import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.requests import Request

from rate_limit import client_key
from upload_limits import read_upload_limited


def test_upload_reader_rejects_oversize_without_unbounded_buffer():
    async def exercise():
        upload = UploadFile(filename="large.jpg", file=BytesIO(b"x" * 100))
        with pytest.raises(HTTPException) as exc:
            await read_upload_limited(upload, 64)
        assert exc.value.status_code == 413

    asyncio.run(exercise())


def _request(peer: str, forwarded: str = "") -> Request:
    headers = []
    if forwarded:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "client": (peer, 1234),
            "scheme": "http",
        }
    )


def test_authenticated_rate_limit_key_ignores_forwarded_for(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    request = _request("10.0.0.9", "203.0.113.10")
    assert client_key(request, "doctor-1") == "user:doctor-1"


def test_anonymous_rate_limit_ignores_untrusted_forwarded_for(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    request = _request("10.0.0.9", "203.0.113.10")
    assert client_key(request) == "anonymous:10.0.0.9"


def test_anonymous_rate_limit_honors_forwarded_for_from_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.9")
    request = _request("10.0.0.9", "203.0.113.10")
    assert client_key(request) == "anonymous:203.0.113.10"
