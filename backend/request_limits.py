from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.types import Message, Receive, Scope, Send


class RequestBodyLimitExceeded(Exception):
    """Raised when an HTTP request body exceeds the configured ingress limit."""


class RequestBodyLimitMiddleware:
    """Enforce a request-body ceiling even when the client uses chunked transfer."""

    def __init__(self, app: Callable[..., Awaitable[None]], max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                received += len(body)
                if received > self.max_body_bytes:
                    raise RequestBodyLimitExceeded
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyLimitExceeded:
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"detail":"Request body exceeds configured size limit"}',
                }
            )
