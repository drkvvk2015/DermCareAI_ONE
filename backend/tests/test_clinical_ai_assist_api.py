from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from PIL import Image

import clinical_ai_assist_api as module
import clinical_ai_policy
from auth import get_current_user


def _user():
    return {
        "uid": "doctor-1",
        "roles": {"doctor"},
        "claims": {"organization_id": "org-1", "clinic_id": "clinic-1"},
    }


IMAGE_QUALITY_PATH = "/api/v1/clinical-ai/image-quality/enc-1"
GENERATIVE_REVIEW_PATH = "/api/v1/clinical-ai/generative-image-review/enc-1"
IMAGE_ENDPOINTS = (
    (IMAGE_QUALITY_PATH, False),
    (GENERATIVE_REVIEW_PATH, True),
)


def _http_client() -> TestClient:
    app = FastAPI()
    app.include_router(module.router)
    app.dependency_overrides[get_current_user] = _user
    return TestClient(app)


def _image_bytes(image_format: str = "JPEG") -> bytes:
    output = BytesIO()
    Image.new("RGB", (16, 16), (120, 80, 40)).save(output, format=image_format)
    return output.getvalue()


def _post_image(
    client: TestClient,
    path: str,
    content: bytes | None = None,
    content_type: str = "image/jpeg",
    clinical_context: str | None = None,
):
    data = {"clinical_context": clinical_context} if clinical_context is not None else {}
    return client.post(
        path,
        data=data,
        files={"file": ("synthetic-image.jpg", content or _image_bytes(), content_type)},
    )


def _enable_assist(monkeypatch: pytest.MonkeyPatch, *, generative: bool = False) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "true")
    monkeypatch.setenv("ENABLE_GENERATIVE_CLINICAL_ASSIST", str(generative).lower())
    monkeypatch.setenv("ENABLE_MEDGEMMA", str(generative).lower())


def _install_encounter_and_consent(monkeypatch: pytest.MonkeyPatch, *, consent: bool = True) -> None:
    monkeypatch.setattr(
        module,
        "get_encounter",
        lambda encounter_id, organization_id, clinic_id: {
            "id": encounter_id,
            "patient_id": "patient-1",
        },
    )
    monkeypatch.setattr(module, "has_active_consent", lambda **kwargs: consent)


def _install_quality_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    quality = SimpleNamespace(
        usable=True,
        reason="synthetic quality result",
        width=16,
        height=16,
        mean_luminance=90.0,
        luminance_variance=25.0,
        issues=(),
    )
    result = SimpleNamespace(
        quality=quality,
        region_detected=False,
        region=None,
        safety_note="Clinician confirmation is required.",
    )
    monkeypatch.setattr(module, "analyze_image", lambda _: result)

    async def run_inline(function, *args):
        return function(*args)

    monkeypatch.setattr(module, "run_inference", run_inline)


def test_differential_assist_is_explicitly_non_diagnostic(monkeypatch):
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "true")
    monkeypatch.setattr(module, "get_encounter", lambda encounter_id, organization_id, clinic_id: {"id": encounter_id, "patient_id": "patient-1"})
    monkeypatch.setattr(module, "record_event", lambda *args, **kwargs: None)
    result = module.differential_assist(module.DifferentialAssistRequest(encounter_id="enc-1", primary_morphology="plaque", secondary_changes=["scale"], distribution="extensor surfaces", pruritus=True), _user())
    assert result["clinical_use"] == "suggestion_only"
    assert result["diagnostic_status"] == "not_a_diagnosis"
    assert result["decision_authority"] == "treating_physician"
    assert result["requires_clinician_verification"] is True
    assert result["can_sign_diagnosis"] is False
    assert result["can_prescribe"] is False
    assert result["can_order"] is False
    assert result["can_modify_signed_record"] is False
    assert result["candidates"]
    assert all(item["support_score_is_probability"] is False for item in result["candidates"])


def test_differential_assist_stays_disabled_when_feature_flag_is_off(monkeypatch):
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "false")
    try:
        module.differential_assist(module.DifferentialAssistRequest(encounter_id="enc-1", primary_morphology="plaque"), _user())
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Clinical assist must be fail-closed when disabled")


def test_differential_assist_requires_tenant_context(monkeypatch):
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "true")
    with_tenant_missing = dict(_user())
    with_tenant_missing["claims"] = {}
    try:
        module.differential_assist(module.DifferentialAssistRequest(encounter_id="enc-1", primary_morphology="plaque"), with_tenant_missing)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Clinical assist must require tenant context")


def test_diagnostic_execution_is_permanently_disabled_in_application_policy(monkeypatch):
    monkeypatch.setenv("AI_DIAGNOSTIC_MODE", "clinical")
    state = clinical_ai_policy.capabilities()
    assert state.diagnostic_mode.value == "disabled"
    assert clinical_ai_policy.diagnostic_clinical_activation_allowed() is False


def test_capability_contract_exposes_the_public_production_boundary(monkeypatch):
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "true")
    result = module.get_capabilities(_user())
    assert result["diagnostic_mode"] == "disabled"
    assert result["production_boundary"] == {
        "clinical_assist": "suggestion_only",
        "diagnostic_inference": "disabled",
        "autonomous_diagnosis": False,
        "autonomous_prescribing": False,
        "autonomous_orders": False,
        "automatic_signed_record_changes": False,
        "decision_authority": "treating_physician",
    }


@pytest.mark.parametrize(("path", "generative"), IMAGE_ENDPOINTS)
def test_image_endpoints_reject_disabled_assist_flags(monkeypatch, path, generative):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "false" if not generative else "true")
    monkeypatch.setenv("ENABLE_GENERATIVE_CLINICAL_ASSIST", "false")
    monkeypatch.setenv("ENABLE_MEDGEMMA", "true")

    response = _post_image(_http_client(), path)

    assert response.status_code == 409


@pytest.mark.parametrize(("path", "generative"), IMAGE_ENDPOINTS)
def test_image_endpoints_scope_encounter_lookup_to_tenant(monkeypatch, path, generative):
    _enable_assist(monkeypatch, generative=generative)
    lookups = []

    def no_encounter(encounter_id, organization_id, clinic_id):
        lookups.append((encounter_id, organization_id, clinic_id))
        return None

    monkeypatch.setattr(module, "get_encounter", no_encounter)
    client = _http_client()

    response = _post_image(client, path)

    assert response.status_code == 404
    assert lookups == [("enc-1", "org-1", "clinic-1")]


@pytest.mark.parametrize(("path", "generative"), IMAGE_ENDPOINTS)
def test_image_endpoints_require_active_image_consent(monkeypatch, path, generative):
    _enable_assist(monkeypatch, generative=generative)
    _install_encounter_and_consent(monkeypatch, consent=False)

    response = _post_image(_http_client(), path)

    assert response.status_code == 409
    assert response.json()["detail"] == "Active clinical-image consent is required"


@pytest.mark.parametrize(("path", "generative"), IMAGE_ENDPOINTS)
@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b"not-an-image", "image/jpeg"),
        (_image_bytes("PNG"), "image/jpeg"),
    ],
)
def test_image_endpoints_reject_malformed_and_mime_mismatched_uploads(
    monkeypatch, path, generative, content, content_type
):
    _enable_assist(monkeypatch, generative=generative)
    _install_encounter_and_consent(monkeypatch)

    response = _post_image(
        _http_client(),
        path,
        content=content,
        content_type=content_type,
    )

    assert response.status_code == 400


@pytest.mark.parametrize(("path", "generative"), IMAGE_ENDPOINTS)
def test_image_endpoints_reject_oversized_uploads(monkeypatch, path, generative):
    _enable_assist(monkeypatch, generative=generative)
    _install_encounter_and_consent(monkeypatch)
    monkeypatch.setattr(module, "MAX_IMAGE_BYTES", 8)

    response = _post_image(_http_client(), path, content=b"x" * 9)

    assert response.status_code == 413


def test_image_quality_endpoint_records_tenant_audit_event(monkeypatch):
    _enable_assist(monkeypatch)
    _install_encounter_and_consent(monkeypatch)
    _install_quality_inference(monkeypatch)
    events: list[Any] = []
    monkeypatch.setattr(module, "record_event", lambda event, user: events.append((event, user)))

    response = _post_image(_http_client(), IMAGE_QUALITY_PATH)

    assert response.status_code == 200
    assert response.json()["capability"] == "clinical_image_quality"
    event, _ = events[0]
    assert event.action == "clinical_ai_assist_image_quality"
    assert event.metadata["organization_id"] == "org-1"
    assert event.metadata["clinic_id"] == "clinic-1"


def test_generative_review_enforces_immutable_revision_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_CLINICAL_ASSIST_AI", "true")
    monkeypatch.setenv("ENABLE_GENERATIVE_CLINICAL_ASSIST", "true")
    monkeypatch.setenv("ENABLE_MEDGEMMA", "true")
    monkeypatch.setenv("MEDGEMMA_REVISION", "main")
    monkeypatch.setattr(
        module,
        "_medgemma_adapter",
        lambda: (_ for _ in ()).throw(AssertionError("adapter must not load")),
    )

    response = _post_image(_http_client(), GENERATIVE_REVIEW_PATH)

    assert response.status_code == 409


@pytest.mark.parametrize("failure", ["load", "review"])
def test_generative_review_handles_model_failures_without_exposing_details(monkeypatch, failure):
    _enable_assist(monkeypatch, generative=True)
    _install_encounter_and_consent(monkeypatch)

    class StubAdapter:
        def load(self):
            return failure != "load"

        def review(self, image_bytes, clinical_context):
            raise RuntimeError("synthetic model failure")

    monkeypatch.setattr(module, "_medgemma_adapter", StubAdapter)

    async def run_inline(function, *args):
        return function(*args)

    monkeypatch.setattr(module, "run_inference", run_inline)

    response = _post_image(_http_client(), GENERATIVE_REVIEW_PATH)

    assert response.status_code == 503
    assert "synthetic model failure" not in response.text


def test_generative_review_receives_multipart_context_image_and_records_audit(monkeypatch):
    _enable_assist(monkeypatch, generative=True)
    _install_encounter_and_consent(monkeypatch)
    events: list[Any] = []
    monkeypatch.setattr(module, "record_event", lambda event, user: events.append((event, user)))
    image_bytes = _image_bytes()
    clinical_context = "Synthetic context for regression testing."
    received: list[tuple[bytes, str]] = []

    class StubAdapter:
        def load(self):
            return True

        def review(self, content, context):
            received.append((content, context))
            return {
                "model_name": "synthetic",
                "model_id": "synthetic/model",
                "revision": "a" * 40,
                "image_sha256": "b" * 64,
                "output": "Conservative synthetic description.",
            }

    monkeypatch.setattr(module, "_medgemma_adapter", StubAdapter)

    async def run_inline(function, *args):
        return function(*args)

    monkeypatch.setattr(module, "run_inference", run_inline)

    response = _post_image(
        _http_client(),
        GENERATIVE_REVIEW_PATH,
        content=image_bytes,
        clinical_context=clinical_context,
    )

    assert response.status_code == 200
    assert received == [(image_bytes, clinical_context)]
    assert response.json()["clinical_use"] == "suggestion_only"
    event, _ = events[0]
    assert event.action == "clinical_ai_assist_generative_image_review"
    assert event.metadata["organization_id"] == "org-1"
    assert event.metadata["clinic_id"] == "clinic-1"
