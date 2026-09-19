import os
from uuid import uuid4

os.environ.setdefault("AI_GOVERNANCE_DB_PATH", f"/tmp/dermcareai-ai-api-{uuid4().hex}.db")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import get_current_user
from ai_registry import router as ai_router

app = FastAPI()
app.include_router(ai_router)

_CURRENT = {
    "uid": "admin-1",
    "roles": {"admin"},
    "claims": {"organization_id": "org-1", "clinic_id": "clinic-1"},
}


def override_user():
    return _CURRENT


app.dependency_overrides[get_current_user] = override_user


def test_research_model_cannot_deploy_to_production() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/ai/registry",
        json={
            "model_name": "research-demo",
            "version": "1.0.0",
            "artifact_sha256": "b" * 64,
            "research_only": True,
            "validated": False,
            "status": "candidate",
        },
    )
    assert response.status_code == 200
    model_id = response.json()["id"]

    blocked = client.post(
        "/api/v1/ai/deployments",
        json={"model_version_id": model_id, "environment": "production"},
    )
    assert blocked.status_code == 409
