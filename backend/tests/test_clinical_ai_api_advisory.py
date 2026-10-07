from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
from dermatology import clinical_ai_api


def test_authenticated_differential_returns_non_decision_advisory_contract(monkeypatch):
    app = FastAPI()
    app.include_router(clinical_ai_api.router)

    monkeypatch.setattr(
        clinical_ai_api,
        "generate_differential",
        lambda _: SimpleNamespace(
            abstained=False,
            disclaimer="Suggestion only; clinician review is required.",
            safety=SimpleNamespace(urgent_review=False, reason="none", matched_flags=()),
            candidates=(),
        ),
    )
    app.dependency_overrides[auth.get_current_user] = lambda: {
        "uid": "doctor-1",
        "roles": {"doctor"},
        "claims": {"organization_id": "org-1", "clinic_id": "clinic-1"},
    }

    response = TestClient(app).post(
        "/api/v1/dermatology/clinical-ai/differential",
        headers={"Authorization": "Bearer synthetic-test-token"},
        json={
            "primary_morphology": "papule",
            "distribution": "localized",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["advisory"] == {
        "role": "suggestion_only",
        "clinician_decision_required": True,
        "can_decide": False,
        "can_sign_diagnosis": False,
        "can_prescribe": False,
    }


def test_production_app_registers_clinical_ai_and_guideline_routes():
    from app import app
    paths: set[str] = set()
    pending = list(app.routes)
    while pending:
        route = pending.pop()
        route_path = getattr(route, "path", None)
        if route_path:
            paths.add(route_path)
        nested = getattr(route, "routes", None)
        if nested:
            pending.extend(nested)
    assert "/api/v1/dermatology/clinical-ai/differential" in paths
    assert "/api/v1/dermatology/guidelines" in paths
    assert "/api/v1/dermatology/guidelines/recommend" in paths
