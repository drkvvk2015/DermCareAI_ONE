import asyncio

from app import MAX_REQUEST_BODY_BYTES, request_context_middleware


def test_oversized_content_length_uses_common_response_finalization():
    async def exercise():
        called = False

        async def call_next(_request):
            nonlocal called
            called = True
            raise AssertionError("next handler must not run")

        request = type(
            "RequestStub",
            (),
            {
                "headers": {
                    "content-length": str(MAX_REQUEST_BODY_BYTES + 1),
                }
            },
        )()

        response = await request_context_middleware(request, call_next)

        assert called is False
        assert response.status_code == 413
        assert response.headers["X-Request-ID"]
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Permissions-Policy"] == "camera=(self), microphone=(), geolocation=()"

    asyncio.run(exercise())


def test_invalid_content_length_uses_common_response_finalization():
    async def exercise():
        async def call_next(_request):
            raise AssertionError("next handler must not run")

        request = type(
            "RequestStub",
            (),
            {"headers": {"content-length": "invalid"}},
        )()

        response = await request_context_middleware(request, call_next)

        assert response.status_code == 400
        assert response.headers["X-Request-ID"]
        assert response.headers["X-Response-Time-ms"]

    asyncio.run(exercise())
