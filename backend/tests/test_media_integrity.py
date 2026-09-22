import pytest

from dermatology.media_integrity import validate_media_metadata

def test_valid_media_metadata():
    validate_media_metadata(
        sha256="a" * 64,
        mime_type="image/jpeg",
        byte_size=1024,
        captured_at="2026-09-22T12:00:00+00:00",
        retention_until="2027-09-22T12:00:00+00:00",
    )

def test_invalid_digest_is_rejected():
    with pytest.raises(ValueError):
        validate_media_metadata(
            sha256="not-a-digest",
            mime_type="image/jpeg",
            byte_size=10,
            captured_at="2026-09-22T12:00:00+00:00",
        )

def test_invalid_mime_type_is_rejected():
    with pytest.raises(ValueError):
        validate_media_metadata(
            sha256="a" * 64,
            mime_type="application/pdf",
            byte_size=10,
            captured_at="2026-09-22T12:00:00+00:00",
        )

def test_retention_cannot_precede_capture():
    with pytest.raises(ValueError):
        validate_media_metadata(
            sha256="a" * 64,
            mime_type="image/jpeg",
            byte_size=10,
            captured_at="2026-09-22T12:00:00+00:00",
            retention_until="2026-09-21T12:00:00+00:00",
        )
