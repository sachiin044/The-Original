from datetime import datetime
from app.core.db import get_supabase

supabase = get_supabase()


def log_api_usage(api_key_id: str, endpoint: str):
    try:
        supabase.table("api_usage_logs").insert({
            "api_key_id": api_key_id,
            "endpoint": endpoint,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass  # logging must never block API
