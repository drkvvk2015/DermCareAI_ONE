from __future__ import annotations

import json
import os
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    from firebase_admin import firestore
except ImportError:  # pragma: no cover
    firebase_admin = None
    firebase_auth = None
    firestore = None

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _firebase_app():
    if firebase_admin is None or firebase_auth is None or firestore is None:
        raise HTTPException(status_code=503, detail="Firebase Admin SDK is not available")
    try:
        return firebase_admin.get_app()
    except ValueError:
        raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if not raw:
            raise HTTPException(status_code=503, detail="Firebase service credentials are not configured")
        return firebase_admin.initialize_app(
            firebase_admin.credentials.Certificate(json.loads(raw))
        )


class ClinicianActivation(BaseModel):
    organization_id: str = Field(min_length=1, max_length=120)
    clinic_id: str = Field(min_length=1, max_length=120)
    roles: List[str] = Field(min_length=1)
    license_verified: bool = True


@router.post("/clinicians/{uid}/activate")
def activate_clinician(
    uid: str,
    req: ClinicianActivation,
    admin: dict[str, Any] = Depends(require_roles("admin")),
):
    _firebase_app()
    user = firebase_auth.get_user(uid)
    current = dict(user.custom_claims or {})
    roles = sorted(set(req.roles) | {"staff"})
    current.update({
        "organization_id": req.organization_id,
        "clinic_id": req.clinic_id,
        "roles": roles,
        "role": roles[0],
        "license_verified": bool(req.license_verified),
    })
    firebase_auth.set_custom_user_claims(uid, current)
    firestore.client().collection("doctors").document(uid).set(
        {
            "status": "active",
            "organizationId": req.organization_id,
            "clinicId": req.clinic_id,
            "licenseVerified": bool(req.license_verified),
            "activatedBy": admin["uid"],
            "updatedAt": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    return {
        "uid": uid,
        "status": "active",
        "organization_id": req.organization_id,
        "clinic_id": req.clinic_id,
        "roles": roles,
        "license_verified": bool(req.license_verified),
    }
