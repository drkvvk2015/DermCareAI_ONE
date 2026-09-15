from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Callable

from fastapi import Depends, Header, HTTPException, status

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    from firebase_admin import credentials
except ImportError as exc:  # pragma: no cover
    firebase_admin = None
    firebase_auth = None
    credentials = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def _firebase_app():
    if _IMPORT_ERROR is not None:
        raise HTTPException(status_code=503, detail="Firebase Admin SDK is not installed")
    try:
        return firebase_admin.get_app()
    except ValueError:
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            try:
                service_account = json.loads(service_account_json)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=500, detail="Invalid FIREBASE_SERVICE_ACCOUNT_JSON") from exc
            return firebase_admin.initialize_app(credentials.Certificate(service_account))
        return firebase_admin.initialize_app()


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    return token


@lru_cache(maxsize=1)
def _firebase_enabled() -> bool:
    value = os.getenv("FIREBASE_AUTH_REQUIRED", "true").lower()
    return value == "true"


def get_current_user(authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    if not _firebase_enabled():
        raise HTTPException(status_code=503, detail="FIREBASE_AUTH_REQUIRED must remain enabled for clinic APIs")
    token = _extract_bearer(authorization)
    try:
        _firebase_app()
        decoded = firebase_auth.verify_id_token(token, check_revoked=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked Firebase ID token") from exc

    role = decoded.get("role")
    roles_claim = decoded.get("roles")
    roles = {str(role)} if role else set()
    if isinstance(roles_claim, list):
        roles.update(str(item) for item in roles_claim)
    if not roles:
        roles.add("staff")

    return {
        "uid": str(decoded.get("uid") or decoded.get("user_id") or decoded.get("sub")),
        "email": decoded.get("email"),
        "roles": roles,
        "claims": decoded,
    }


def require_roles(*allowed_roles: str) -> Callable[..., dict[str, Any]]:
    allowed = {role.lower() for role in allowed_roles}

    def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        user_roles = {str(role).lower() for role in user.get("roles", set())}
        if not user_roles.intersection(allowed) and "admin" not in user_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency
