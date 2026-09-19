"""Minimal in-process observability with no PHI or payload persistence."""
from __future__ import annotations

from collections import Counter
from threading import Lock
from time import monotonic
from typing import Any


_lock = Lock()
_requests = Counter()
_ai_models = Counter()
_ai_decisions = Counter()
_total_request_ms = 0.0
_started_at = monotonic()


def record_request(status_code: int, elapsed_ms: float) -> None:
    global _total_request_ms
    bucket = f"{status_code // 100}xx"
    with _lock:
        _requests[bucket] += 1
        _total_request_ms += max(0.0, elapsed_ms)


def record_prediction(*, model: str, accepted: bool) -> None:
    with _lock:
        _ai_models[model] += 1
        _ai_decisions["accepted" if accepted else "abstained"] += 1


def snapshot() -> dict[str, Any]:
    with _lock:
        request_count = sum(_requests.values())
        average_ms = _total_request_ms / request_count if request_count else 0.0
        return {
            "uptime_seconds": round(monotonic() - _started_at, 2),
            "http_requests": dict(_requests),
            "http_request_average_ms": round(average_ms, 2),
            "ai_predictions_by_model": dict(_ai_models),
            "ai_decisions": dict(_ai_decisions),
        }
