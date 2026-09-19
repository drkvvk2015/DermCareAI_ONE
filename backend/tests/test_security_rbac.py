import pytest
from fastapi import HTTPException

from auth import require_roles


def test_require_roles_allows_matching_role() -> None:
    dependency = require_roles("pharmacist")
    user = {"uid": "u1", "roles": {"pharmacist"}}
    assert dependency(user) == user


def test_require_roles_rejects_unapproved_role() -> None:
    dependency = require_roles("pharmacist")
    with pytest.raises(HTTPException) as exc:
        dependency({"uid": "u1", "roles": {"receptionist"}})
    assert exc.value.status_code == 403


def test_admin_bypasses_specific_role_restriction() -> None:
    dependency = require_roles("pharmacist")
    user = {"uid": "admin1", "roles": {"admin"}}
    assert dependency(user) == user
