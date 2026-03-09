import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.schemas.models import GithubPATRequest
from app.auth.dependency import verify_api_key
from app.core.db import get_supabase
from app.utils.crypto import encrypt_token
from app.utils.github import validate_github_pat

logger = logging.getLogger("explaingithub")
router = APIRouter()
supabase = get_supabase()


@router.post("/credentials/github/pat")
def register_github_pat(
    data: GithubPATRequest,
    api_key_id: str = Depends(verify_api_key),
):
    """
    Registers a GitHub Personal Access Token.
    """

    # 1️⃣ Resolve user_email from API key
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

    # 2️⃣ Validate token with GitHub
    try:
        granted_scopes = validate_github_pat(
            token=data.token,
            scopes_expected=data.scopes_expected,
        )
    except Exception:
        logger.exception("GitHub PAT validation failed")

        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub token"
        )


    # ================================
    # ⬅️ ADD: OVER-SCOPE VALIDATION (NOTION)
    # ================================
    extra_scopes = set(granted_scopes) - set(data.scopes_expected)
    if extra_scopes:
        raise HTTPException(
            status_code=400,
            detail=f"Token has extra scopes: {list(extra_scopes)}"
        )


    # ================================
    # ⬅️ ADD: EXPIRY VALIDATION (NOTION)
    # ================================
    if not data.expires_at:
        raise HTTPException(
        status_code=400,
        detail="Token expiry is required"
    )

    try:
        expires = datetime.fromisoformat(
            data.expires_at.replace("Z", "+00:00")
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid expires_at format"
    )

    if expires <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Token is already expired"
    )


    # 3️⃣ Encrypt token (NO RAW STORAGE)
    encrypted = encrypt_token(data.token)

    credential_id = str(uuid.uuid4())

    # 4️⃣ Store credential
    supabase.table("credentials").insert({
        "id": credential_id,
        "user_email": user_email,
        "provider": "github",
        "label": data.label,
        "encrypted_token": encrypted,
        "scopes": granted_scopes,
        "expires_at": data.expires_at,
    }).execute()

    return {
        "credential_id": credential_id,
        "status": "validated"
    }


@router.delete("/credentials/{credential_id}")
def revoke_credential(
    credential_id: str,
    api_key_id: str = Depends(verify_api_key),
):
    """
    Revokes a stored credential.
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
        raise HTTPException(
            status_code=404,
            detail="API key not found"
        )

    user_email = key_resp.data[0]["user_email"]

    # 2️⃣ Fetch credential
    cred_resp = (
        supabase
        .table("credentials")
        .select("id, user_email")
        .eq("id", credential_id)
        .execute()
    )

    if not cred_resp.data:
        raise HTTPException(
            status_code=404,
            detail="Credential not found"
        )

    # 3️⃣ Ownership check (PDF implied)
    if cred_resp.data[0]["user_email"] != user_email:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to revoke this credential"
        )

    # 4️⃣ Revoke (soft delete = safest)
    supabase.table("credentials").update({
        "status": "revoked"
    }).eq("id", credential_id).execute()

    return {
        "status": "revoked"
    }
