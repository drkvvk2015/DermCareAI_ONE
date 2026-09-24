"""Distributed-capable rate limiting with Redis fail-closed support in production."""
from __future__ import annotations

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
_REDIS = None


def _redis_client():
    global _REDIS
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    if redis is None:
        return None
    if _REDIS is None:
        _REDIS = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
    return _REDIS


def _local_limit(key: str, *, limit: int, window_seconds: int) -> None:
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


def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    client = _redis_client()
    if client is not None:
        try:
            bucket_key = f"dermcareai:ratelimit:{key}"
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
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Distributed rate limiting is unavailable",
                ) from exc
    elif os.getenv("APP_ENV", "development").lower() == "production" and os.getenv("REQUIRE_DISTRIBUTED_RATE_LIMIT", "true").lower() == "true":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed rate limiting is not configured",
        )

    _local_limit(key, limit=limit, window_seconds=window_seconds)


def client_key(request: Request, identity: str | None = None) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    return f"{identity or 'anonymous'}:{ip}"
