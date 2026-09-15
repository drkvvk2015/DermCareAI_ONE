import pytest
from fastapi import HTTPException

import auth


def test_extract_bearer_rejects_missing_token() -> None:
    with pytest.raises(HTTPException) as exc:
        auth._extract_bearer(None)
    assert exc.value.status_code == 401


def test_extract_bearer_rejects_empty_token() -> None:
    with pytest.raises(HTTPException) as exc:
        auth._extract_bearer("Bearer   ")
    assert exc.value.status_code == 401


def test_extract_bearer_accepts_token() -> None:
    assert auth._extract_bearer("Bearer abc123") == "abc123"


def test_require_roles_rejects_wrong_role() -> None:
    dependency = auth.require_roles("doctor")
    with pytest.raises(HTTPException) as exc:
        dependency({"uid": "u1", "roles": {"receptionist"}})
    assert exc.value.status_code == 403


def test_require_roles_allows_admin() -> None:
    dependency = auth.require_roles("doctor")
    user = {"uid": "u1", "roles": {"admin"}}
    assert dependency(user) == user
