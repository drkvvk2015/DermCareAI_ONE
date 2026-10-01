from __future__ import annotations

import os

from fastapi import HTTPException, UploadFile


MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(12 * 1024 * 1024)))
MAX_REQUEST_BODY_BYTES = int(
    os.getenv("MAX_REQUEST_BODY_BYTES", str(MAX_IMAGE_BYTES + 1024 * 1024))
)
_UPLOAD_CHUNK_BYTES = 1024 * 1024


async def read_upload_limited(file: UploadFile, max_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    """Read an upload in bounded chunks and reject as soon as the limit is crossed."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(min(_UPLOAD_CHUNK_BYTES, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail="Image exceeds configured size limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)
