import pytest
from fastapi import HTTPException
from fastapi import Request

from rate_limit import enforce_rate_limit


def test_rate_limit_blocks_after_threshold() -> None:
    key = "test-rate-limit"
    enforce_rate_limit(key, limit=1, window_seconds=60)
    with pytest.raises(HTTPException) as exc:
        enforce_rate_limit(key, limit=1, window_seconds=60)
    assert exc.value.status_code == 429
