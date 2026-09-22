from __future__ import annotations

import re
from datetime import datetime

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

def validate_media_metadata(
    *,
    sha256: str,
    mime_type: str,
    byte_size: int,
    captured_at: str,
    retention_until: str | None = None,
) -> None:
    if not HEX_SHA256.fullmatch(sha256.lower()):
        raise ValueError("sha256 must be a 64-character hexadecimal digest")
    if mime_type.lower() not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValueError(f"Unsupported clinical media MIME type: {mime_type}")
    if byte_size <= 0:
        raise ValueError("byte_size must be greater than zero")
    try:
        captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("captured_at must be a valid ISO-8601 timestamp") from exc
    if retention_until is not None:
        try:
            retention = datetime.fromisoformat(retention_until.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("retention_until must be a valid ISO-8601 timestamp") from exc
        if retention <= captured:
            raise ValueError("retention_until must be later than captured_at")
