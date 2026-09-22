import os

os.environ["CLOUDINARY_CLOUD_NAME"] = "demo"
os.environ["CLOUDINARY_API_KEY"] = "key"
os.environ["CLOUDINARY_API_SECRET"] = "secret"

from media import SignUploadRequest, sign_upload


def _user():
    return {"uid": "doctor1", "roles": {"doctor"}, "claims": {"clinic_id": "clinic1"}}


def test_profile_upload_does_not_require_patient_consent() -> None:
    result = sign_upload(SignUploadRequest(subject_id="doctor1", purpose="profile-avatar"), _user())
    assert result.folder.endswith("/profile-avatar")


def test_clinical_upload_requires_consent(monkeypatch) -> None:
    monkeypatch.setattr("media.has_active_consent", lambda **_: False)
    try:
        sign_upload(SignUploadRequest(subject_id="patient1", purpose="clinical-image"), _user())
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
    else:
        raise AssertionError("Clinical media upload must require active consent")
