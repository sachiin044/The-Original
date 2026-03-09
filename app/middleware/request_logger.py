# middleware/request_logger.py
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.core.db import get_supabase

supabase = get_supabase()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())

        response = None
        error_message = None

        try:
            response = await call_next(request)
            return response
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)

            # api_key_id is injected by verify_api_key dependency
            api_key_id = getattr(request.state, "api_key_id", None)

            try:
                supabase.table("api_usage_logs").insert({
                    "request_id": request_id,
                    "api_key_id": api_key_id,
                    "endpoint": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code if response else 500,
                    "duration_ms": duration_ms,
                    "error_message": error_message,
                }).execute()
            except Exception:
                # IMPORTANT: logging must never break the app
                pass


