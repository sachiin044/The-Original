import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from app.schemas.models import (
    CreateApiKeyRequest,
    UpdateApiKeyRequest,
    RevokeKeyRequest,
)
from app.auth.dependency import verify_api_key
from app.auth.rate_limit import rate_limit
from app.core.db import get_supabase
from app.auth.api_key_service import (
    create_api_key_internal,
    list_api_keys_internal,
    update_api_key_internal,
    revoke_api_key_internal,
)

logger = logging.getLogger("explaingithub")
router = APIRouter()
supabase = get_supabase()


@router.post("/api-keys")
def create_api_keys(
    data: CreateApiKeyRequest,
    _: None = Depends(rate_limit("api_keys")),
):
    """
    Create a new API key.
    """

    try:
        result = create_api_key_internal(
            user_email=data.email,
            name=data.name,
            environment=data.environment,
            scopes=data.scopes,
            expires_at=data.expires_at,
            ip_allowlist=data.ip_allowlist,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception:
        logger.exception("API key creation failed")

        raise HTTPException(
            status_code=500,
            detail="Failed to create API key"
        )


    return {
        "key_id": result["key_id"],
        "api_key": result["api_key"],  # shown ONCE
        "created_at": result["created_at"],
    }


@router.get("/api-keys")
def list_api_keys(
    api_key_id: str = Depends(verify_api_key),
):
    """
    Lightweight list of API keys.
    No logs. No usage aggregation.
    """

    # 1️⃣ Resolve caller email
    key_resp = (
        supabase
        .table("api_keys")
        .select("user_email")
        .eq("id", api_key_id)
        .execute()
    )

    if not key_resp.data:
        return {"error": "API key not found"}

    user_email = key_resp.data[0]["user_email"]

    # 2️⃣ Internal fetch (may return more fields)
    keys = list_api_keys_internal(user_email=user_email)

    # 3️⃣ 🔒 Normalize to PDF contract
    return [
        {
            "key_id": k["key_id"],
            "name": k["name"],
            "environment": k.get("environment"),
            "scopes": k.get("scopes", []),
            "last_used_at": k.get("last_used_at"),
        }
        for k in keys
    ]


@router.patch("/api-keys/{key_id}")
def update_api_key(
    key_id: str,
    data: UpdateApiKeyRequest = Body(..., embed=False),
    api_key_id: str = Depends(verify_api_key),
):
    """
    Update API key metadata only.
    """

    key_resp = (
        supabase
        .table("api_keys")
        .select("user_email")
        .eq("id", api_key_id)
        .execute()
    )

    if not key_resp.data:
        return {"error": "API key not found"}

    user_email = key_resp.data[0]["user_email"]

    update_api_key_internal(
        key_id=key_id,
        user_email=user_email,
        name=data.name,
        scopes=data.scopes,
    )

    return {"status": "updated"}


@router.delete("/api-keys/{key_id}")
def delete_api_key(
    key_id: str,
    api_key_id: str = Depends(verify_api_key),
):
    """
    Revoke an API key (alias of /revoke-keys).
    """

    # 1️⃣ Resolve caller email (reuse existing pattern)
    key_resp = (
        supabase
        .table("api_keys")
        .select("user_email")
        .eq("id", api_key_id)
        .execute()
    )

    if not key_resp.data:
        return {"error": "API key not found"}

    caller_email = key_resp.data[0]["user_email"]

    # 2️⃣ Call shared revoke logic
    try:
        result = revoke_api_key_internal(
            target_key_id=key_id,
            caller_email=caller_email,
        )
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to revoke this API key"
        )

    except Exception:
        logger.exception("API key revoke failed")

        raise HTTPException(
            status_code=500,
            detail="Failed to revoke API key"
        )


    # Normalize response
    if result.get("status") == "already_revoked":
        return {
            "status": "ok",
            "message": "API key already revoked",
            "api_key_id": key_id,
        }

    return {
        "status": "success",
        "message": "API key revoked successfully",
        "api_key_id": key_id,
    }


@router.get("/manage-keys")
def manage_keys(
    api_key_id: str = Depends(verify_api_key),
):
    """
    Return all API keys and usage logs
    scoped to the same user_email as the caller.
    JSON output only.
    """

    # 1️⃣ Get caller's user_email
    key_resp = (
        supabase
        .table("api_keys")
        .select("user_email")
        .eq("id", api_key_id)
        .execute()
    )

    if not key_resp.data:
        raise HTTPException(
            status_code=404,
            detail="API key not found"
        )

    user_email = key_resp.data[0]["user_email"]

    # 2️⃣ Get all keys for this user
    keys_resp = (
        supabase
        .table("api_keys")
        .select("id, name, status, created_at, last_used_at")
        .eq("user_email", user_email)
        .execute()
    )

    keys = keys_resp.data or []

    result = []

    # 3️⃣ For each key, get logs
    for key in keys:
        logs_resp = (
            supabase
            .table("api_usage_logs")
            .select(
                "endpoint, method, status_code, duration_ms, created_at, request_id, error_message"
            )
            .eq("api_key_id", key["id"])
            .order("created_at", desc=True)
            .execute()
        )

        logs = logs_resp.data or []

        result.append({
            "api_key_id": key["id"],
            "name": key["name"],
            "status": key["status"],
            "created_at": key["created_at"],
            "last_used_at": key["last_used_at"],
            "usage": {
                "total_requests": len(logs),
                "error_count": sum(
                    1 for l in logs if l.get("status_code", 200) >= 400
                ),
            },
            "logs": logs,
        })

    return {
        "user_email": user_email,
        "keys": result,
    }

@router.post("/revoke-keys")
def revoke_keys(
    data: RevokeKeyRequest,
    caller_api_key_id: str = Depends(verify_api_key),
):
    """
    Revoke an API key owned by the same user_email.
    """

    # 1️⃣ Get caller's user_email
    caller_resp = (
        supabase
        .table("api_keys")
        .select("user_email")
        .eq("id", caller_api_key_id)
        .execute()
    )

    if not caller_resp.data:
        raise HTTPException(
            status_code=404,
            detail="Caller API key not found"
        )

    caller_email = caller_resp.data[0]["user_email"]

    # 2️⃣ Get target key
    target_resp = (
        supabase
        .table("api_keys")
        .select("id, user_email, status")
        .eq("id", data.api_key_id)
        .execute()
    )

    if not target_resp.data:
        raise HTTPException(
            status_code=404,
            detail="Target API key not found"
        )

    target_key = target_resp.data[0]

    # 3️⃣ Ownership check
    if target_key["user_email"] != caller_email:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to revoke this API key"
        )

    # 4️⃣ Already revoked check
    if target_key["status"] == "revoked":
        return {
            "status": "ok",
            "message": "API key already revoked",
            "api_key_id": data.api_key_id,
        }

    # 5️⃣ Revoke key
    supabase.table("api_keys").update({
        "status": "revoked"
    }).eq("id", data.api_key_id).execute()

    return {
        "status": "success",
        "message": "API key revoked successfully",
        "api_key_id": data.api_key_id,
    }
