from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import rate_limit


class FakeRedisClient:
    def __init__(self):
        self.count = 0
        self.expirations = []

    def incr(self, key):
        self.count += 1
        return self.count

    def expire(self, key, seconds):
        self.expirations.append((key, seconds))
        return True


class FakeRedis:
    client = FakeRedisClient()
    url = None
    options = None

    @classmethod
    def from_url(cls, url, **options):
        cls.url = url
        cls.options = options
        return cls.client


def test_redis_rate_limit_contract_uses_shared_expiring_counter(monkeypatch):
    FakeRedis.client = FakeRedisClient()
    monkeypatch.setattr(rate_limit, "redis", SimpleNamespace(Redis=FakeRedis))
    monkeypatch.setattr(rate_limit, "_REDIS", None)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("APP_ENV", "staging")

    rate_limit.enforce_rate_limit("doctor:client", limit=2, window_seconds=30)
    rate_limit.enforce_rate_limit("doctor:client", limit=2, window_seconds=30)

    assert FakeRedis.url == "redis://localhost:6379/0"
    assert FakeRedis.options["decode_responses"] is True
    assert FakeRedis.options["socket_connect_timeout"] == 2
    assert FakeRedis.options["socket_timeout"] == 2
    assert FakeRedis.client.expirations == [("dermcareai:ratelimit:doctor:client", 30)]

    with pytest.raises(HTTPException) as error:
        rate_limit.enforce_rate_limit("doctor:client", limit=2, window_seconds=30)
    assert error.value.status_code == 429


def test_redis_failure_fails_closed_in_production(monkeypatch):
    class UnavailableRedisClient(FakeRedisClient):
        def incr(self, key):
            raise OSError("Redis unavailable")

    FakeRedis.client = UnavailableRedisClient()
    monkeypatch.setattr(rate_limit, "redis", SimpleNamespace(Redis=FakeRedis))
    monkeypatch.setattr(rate_limit, "_REDIS", None)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(HTTPException) as error:
        rate_limit.enforce_rate_limit("doctor:client", limit=2, window_seconds=30)
    assert error.value.status_code == 503
