import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.requests import Request

from rate_limit import client_key
from upload_limits import read_upload_limited
from request_limits import RequestBodyLimitMiddleware


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


def test_anonymous_rate_limit_ignores_spoofed_left_prefix_from_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.9")
    request = _request("10.0.0.9", "198.51.100.77, 203.0.113.10")
    assert client_key(request) == "anonymous:203.0.113.10"


def test_chunked_request_body_is_rejected_at_asgi_boundary():
    async def exercise():
        called = False

        async def endpoint(scope, receive, send):
            nonlocal called
            called = True
            while True:
                message = await receive()
                if message["type"] == "http.request" and not message.get("more_body"):
                    break

        chunks = iter([
            {"type": "http.request", "body": b"x" * 8, "more_body": True},
            {"type": "http.request", "body": b"y" * 8, "more_body": False},
        ])

        async def receive():
            return next(chunks)

        sent = []

        async def send(message):
            sent.append(message)

        middleware = RequestBodyLimitMiddleware(endpoint, max_body_bytes=10)
        await middleware(
            {"type": "http", "method": "POST", "path": "/", "headers": []},
            receive,
            send,
        )

        assert called is True
        assert sent[0]["status"] == 413

    asyncio.run(exercise())
