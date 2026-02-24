# auth/rate_limit.py

import time
from fastapi import Request, HTTPException
from collections import defaultdict
from threading import Lock

# Configurable limits
RATE_LIMITS = {
    "chat": (60, 60),          # 60 requests per 60 seconds
    "index": (5, 60),          # 5 index calls per minute
    "upload": (5, 60),
    "api_keys": (20, 60),
}

# In-memory store
_request_store = defaultdict(list)
_lock = Lock()


def rate_limit(key_prefix: str):
    """
    FastAPI dependency factory.
    key_prefix determines which limit bucket to use.
    """

    async def dependency(request: Request):

        identifier = (
            request.headers.get("x-api-key")
            or request.client.host
        )

        limit, window = RATE_LIMITS.get(key_prefix, (60, 60))
        now = time.time()

        with _lock:
            timestamps = _request_store[identifier]

            # Remove expired timestamps
            _request_store[identifier] = [
                t for t in timestamps if now - t < window
            ]

            if len(_request_store[identifier]) >= limit:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
                )

            _request_store[identifier].append(now)

    return dependency
