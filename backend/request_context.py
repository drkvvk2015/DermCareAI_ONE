"""Request correlation context without storing patient or request payload data."""
from __future__ import annotations

import re
from contextvars import ContextVar
from uuid import uuid4

_REQUEST_ID: ContextVar[str | None] = ContextVar("dermcareai_request_id", default=None)
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")


def new_request_id(candidate: str | None = None) -> str:
    if candidate and _SAFE_REQUEST_ID.fullmatch(candidate.strip()):
        return candidate.strip()
    return f"req_{uuid4().hex}"


def set_request_id(request_id: str):
    return _REQUEST_ID.set(request_id)


def get_request_id() -> str | None:
    return _REQUEST_ID.get()


def reset_request_id(token) -> None:
    _REQUEST_ID.reset(token)
