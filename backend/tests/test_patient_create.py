import os
from uuid import uuid4

os.environ.setdefault("CLINICAL_DB_PATH", f"/tmp/dermcareai-patient-create-{uuid4().hex}.db")
os.environ.setdefault("AUDIT_DB_PATH", f"/tmp/dermcareai-patient-audit-{uuid4().hex}.db")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import clinical  # noqa: E402
import patient_store  # noqa: E402
from auth import get_current_user  # noqa: E402

URL = "/api/v1/clinical/patients"
EXPECTED_FIELDS = {
    "name", "age", "gender", "phone", "email", "address", "medicalHistory", "allergies",
    "currentMedications", "organizationId", "clinicId", "doctorId", "createdAt", "upcomingVisit",
}


class _AlreadyExists(Exception):
    pass


class _Snapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data


class _Doc:
    def __init__(self, store, name):
        self._store, self._name = store, name

    def get(self):
        return _Snapshot(self._store.get(self._name))

    def create(self, data):
        if self._name in self._store:
            raise _AlreadyExists()
        self._store[self._name] = data


class _Collection:
    def __init__(self, store):
        self._store = store

    def document(self, name):
        return _Doc(self._store, name)


class _FakeFirestore:
    def __init__(self):
        self.collections = {"patients": {}, "doctors": {"doctor-1": {"status": "active"}}}

    def collection(self, name):
        return _Collection(self.collections.setdefault(name, {}))


def _body(**overrides):
    body = {
        "name": "Synthetic Patient",
        "age": 42,
        "gender": "female",
        "phone": "0000000000",
        "email": "synthetic@example.invalid",
        "address": "1 Test Lane",
        "medicalHistory": "none",
        "allergies": "none",
        "currentMedications": "none",
    }
    body.update(overrides)
    return body


def _headers():
    return {"Idempotency-Key": f"key-{uuid4().hex}"}


@pytest.fixture
def env(monkeypatch):
    fake = _FakeFirestore()
    events = []
    monkeypatch.setattr(patient_store, "_client", lambda: fake)
    monkeypatch.setattr(patient_store, "_gexc", type("G", (), {"AlreadyExists": _AlreadyExists}))
    monkeypatch.setattr(clinical, "record_event", lambda event, user: events.append(event))
    current = {
        "uid": "doctor-1",
        "roles": {"doctor"},
        "claims": {"organization_id": "org-1", "clinic_id": "clinic-1"},
    }
    app = FastAPI()
    app.include_router(clinical.router)
    app.dependency_overrides[get_current_user] = lambda: current
    return TestClient(app), fake, events, current


def test_create_patient_derives_tenant_and_doctor(env):
    client, fake, events, _ = env
    response = client.post(URL, json=_body(), headers=_headers())
    assert response.status_code == 201
    patient_id = response.json()["id"]
    stored = fake.collections["patients"][patient_id]
    assert set(stored) == EXPECTED_FIELDS
    assert stored["organizationId"] == "org-1"
    assert stored["clinicId"] == "clinic-1"
    assert stored["doctorId"] == "doctor-1"
    assert stored["upcomingVisit"] is None
    assert isinstance(stored["createdAt"], str)
    assert stored["age"] == 42
    assert len(events) == 1
    assert events[0].action == "patient_created"
    assert events[0].resource_id == patient_id
    assert events[0].metadata == {"organization_id": "org-1", "clinic_id": "clinic-1"}


@pytest.mark.parametrize("field", ["organizationId", "clinicId", "doctorId", "organization_id", "clinic_id", "doctor_id"])
def test_client_tenant_and_doctor_fields_are_rejected(env, field):
    client, fake, _, _ = env
    response = client.post(URL, json=_body(**{field: "attacker"}), headers=_headers())
    assert response.status_code == 422
    assert fake.collections["patients"] == {}


@pytest.mark.parametrize("override", [{"age": -1}, {"age": 131}, {"age": "42"}, {"age": 4.5}, {"gender": "unknown"}, {"name": "   "}])
def test_invalid_fields_rejected(env, override):
    client, fake, _, _ = env
    response = client.post(URL, json=_body(**override), headers=_headers())
    assert response.status_code == 422
    assert fake.collections["patients"] == {}


def test_missing_idempotency_key_rejected(env):
    client, fake, _, _ = env
    assert client.post(URL, json=_body()).status_code == 400
    assert fake.collections["patients"] == {}


def test_unauthenticated_request_rejected():
    app = FastAPI()
    app.include_router(clinical.router)
    response = TestClient(app).post(URL, json=_body(), headers=_headers())
    assert response.status_code == 401


def test_missing_tenant_claims_rejected(env):
    client, fake, _, current = env
    current["claims"] = {}
    response = client.post(URL, json=_body(), headers=_headers())
    assert response.status_code == 403
    assert fake.collections["patients"] == {}


def test_insufficient_role_rejected(env):
    client, fake, _, current = env
    current["roles"] = {"receptionist"}
    response = client.post(URL, json=_body(), headers=_headers())
    assert response.status_code == 403
    assert fake.collections["patients"] == {}


@pytest.mark.parametrize("doctor_record", [None, {"status": "pending"}])
def test_doctor_must_be_active(env, doctor_record):
    client, fake, events, _ = env
    if doctor_record is None:
        fake.collections["doctors"].clear()
    else:
        fake.collections["doctors"]["doctor-1"] = doctor_record
    response = client.post(URL, json=_body(), headers=_headers())
    assert response.status_code == 403
    assert fake.collections["patients"] == {}
    assert events == []


def test_admin_can_create_without_doctor_record(env):
    client, fake, _, current = env
    current.update(uid="admin-1", roles={"admin"})
    fake.collections["doctors"].clear()
    response = client.post(URL, json=_body(), headers=_headers())
    assert response.status_code == 201
    assert fake.collections["patients"][response.json()["id"]]["doctorId"] == "admin-1"


def test_idempotent_replay_returns_same_id_without_duplicate(env):
    client, fake, events, _ = env
    headers = _headers()
    first = client.post(URL, json=_body(), headers=headers)
    second = client.post(URL, json=_body(), headers=headers)
    assert first.status_code == 201
    assert second.json() == first.json()
    assert len(fake.collections["patients"]) == 1
    assert len(events) == 1


def test_idempotency_key_reuse_with_different_body_conflicts(env):
    client, fake, _, _ = env
    headers = _headers()
    assert client.post(URL, json=_body(), headers=headers).status_code == 201
    assert client.post(URL, json=_body(name="Other Synthetic"), headers=headers).status_code == 409
    assert len(fake.collections["patients"]) == 1


def test_firebase_unavailable_maps_to_503(env, monkeypatch):
    client, _, events, _ = env

    def unavailable():
        raise patient_store.PatientStoreUnavailable("not configured")

    monkeypatch.setattr(patient_store, "_client", unavailable)
    response = client.post(URL, json=_body(), headers=_headers())
    assert response.status_code == 503
    assert "Synthetic" not in response.text
    assert events == []


def test_missing_firebase_admin_sdk_maps_to_503(env, monkeypatch):
    client, _, _, _ = env
    monkeypatch.undo()
    monkeypatch.setattr(patient_store, "firebase_admin", None)
    app = FastAPI()
    app.include_router(clinical.router)
    app.dependency_overrides[get_current_user] = lambda: {
        "uid": "doctor-1", "roles": {"doctor"}, "claims": {"organization_id": "org-1", "clinic_id": "clinic-1"},
    }
    monkeypatch.setattr(clinical, "record_event", lambda event, user: None)
    response = TestClient(app).post(URL, json=_body(), headers=_headers())
    assert response.status_code == 503
