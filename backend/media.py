from __future__ import annotations

import hashlib
import hmac
import os
import re
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles
from rate_limit import enforce_rate_limit

router = APIRouter(prefix="/media", tags=["media"])


class SignUploadRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=120)
    purpose: str = Field(default="clinical-image", min_length=1, max_length=60)


class SignUploadResponse(BaseModel):
    cloud_name: str
    api_key: str
    timestamp: int
    signature: str
    upload_preset: str
    resource_type: str = "image"
    folder: str


def _safe_segment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())[:80] or "unknown"


def _signature(params: dict[str, Any], secret: str) -> str:
    serialized = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hmac.new(secret.encode("utf-8"), serialized.encode("utf-8"), hashlib.sha256).hexdigest()


@router.post("/sign-upload", response_model=SignUploadResponse)
def sign_upload(
    req: SignUploadRequest,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin")),
) -> SignUploadResponse:
    enforce_rate_limit(f"media-sign:{user['uid']}", limit=30, window_seconds=60)

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    upload_preset = os.getenv("CLOUDINARY_UPLOAD_PRESET", "dermcareai_signed")

    if not cloud_name or not api_key or not api_secret:
        raise HTTPException(status_code=503, detail="Cloudinary signing is not configured")

    timestamp = int(time.time())
    folder = f"dermcareai/patients/{_safe_segment(req.patient_id)}/{_safe_segment(req.purpose)}"
    params = {"folder": folder, "timestamp": timestamp, "upload_preset": upload_preset}
    return SignUploadResponse(
        cloud_name=cloud_name,
        api_key=api_key,
        timestamp=timestamp,
        signature=_signature(params, api_secret),
        upload_preset=upload_preset,
        folder=folder,
    )
