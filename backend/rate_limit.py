"""Distributed-capable rate limiting.

Redis is required for production deployments so limits are shared across workers.
A bounded in-process fallback remains available for development and tests.
"""
from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None


_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_LOCK = Lock()
_REDIS_CLIENT = None


def _redis_client():
    global _REDIS_CLIENT
    url = os.getenv("REDIS_URL")
    if not url or redis is None:
        return None
    if _REDIS_CLIENT is None:
        _REDIS_CLIENT = redis.Redis.from_url(url, decode_responses=True)
    return _REDIS_CLIENT


def redis_configured() -> bool:
    return bool(os.getenv("REDIS_URL"))


def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    client = _redis_client()
    if client is not None:
        bucket_key = "dermcareai:ratelimit:" + hashlib.sha256(key.encode("utf-8")).hexdigest()
        try:
            count = int(client.incr(bucket_key))
            if count == 1:
                client.expire(bucket_key, window_seconds)
            if count > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please retry later.",
                    headers={"Retry-After": str(window_seconds)},
                )
            return
        except HTTPException:
            raise
        except Exception as exc:
            if os.getenv("APP_ENV", "development").lower() == "production":
                raise HTTPException(status_code=503, detail="Distributed rate limiter unavailable") from exc

    if os.getenv("APP_ENV", "development").lower() == "production":
        raise HTTPException(status_code=503, detail="REDIS_URL is required for production rate limiting")

    now = time.monotonic()
    cutoff = now - window_seconds
    with _LOCK:
        bucket = _BUCKETS[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please retry later.",
                headers={"Retry-After": str(window_seconds)},
            )
        bucket.append(now)


def client_key(request: Request, identity: str | None = None) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    return f"{identity or 'anonymous'}:{ip}"
