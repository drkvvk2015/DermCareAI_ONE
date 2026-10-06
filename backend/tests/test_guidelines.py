import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from auth import get_current_user
from dermatology import guidelines_api
from medguide_ai import EvidenceItem, GuidelineStore, PatientContext, load_guideline_dir

# Synthetic placeholder entries for tests only; not clinical guidance.
_ENTRY = {
    "guideline_id": "TEST-001",
    "title": "Synthetic test entry",
    "disease": "testdisease",
    "recommendation": "Synthetic recommendation A",
    "supporting_evidence": ["synthetic ref"],
    "strength": "high",
    "source": {"name": "NICE", "category": "test"},
    "version": {"guideline_id": "TEST-001", "version": "1.0", "publication_date": "2026-01-01"},
    "medications": ["drugx"],
    "contraindications": ["allergyx"],
    "required_information": ["itching"],
    "approved_by": "Dr Test",
    "approved_on": "2026-02-01",
}


def _store() -> GuidelineStore:
    return GuidelineStore([EvidenceItem.model_validate(_ENTRY)])


def test_unapproved_entry_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem.model_validate({**_ENTRY, "approved_by": "  "})
    bad = {k: v for k, v in _ENTRY.items() if k != "approved_by"}
    with pytest.raises(ValidationError):
        EvidenceItem.model_validate(bad)


def test_recommend_is_advisory_and_flags_gaps() -> None:
    rec = _store().recommend(PatientContext(symptoms=("itching",), conditions=("testdisease",), allergies=("allergyx",)))
    assert rec is not None
    assert rec.human_review_required is True
    assert rec.contraindications_flagged == ("allergyx",)
    assert rec.escalation_required is True
    assert any("not evaluated" in note for note in rec.notes)
    assert rec.approved_by == "Dr Test"


def test_overlapping_medication_is_not_treated_as_unsafe() -> None:
    rec = _store().recommend(PatientContext(conditions=("testdisease",), symptoms=("itching",), medications=("DrugX",)))
    assert rec is not None
    assert rec.contraindications_flagged == ()
    assert rec.escalation_required is False


def test_no_match_returns_none_and_duplicates_rejected() -> None:
    assert _store().recommend(PatientContext(symptoms=("unrelated",))) is None
    with pytest.raises(ValueError):
        GuidelineStore([EvidenceItem.model_validate(_ENTRY), EvidenceItem.model_validate(_ENTRY)])


def test_clinician_can_select_guideline_sources() -> None:
    other = {**_ENTRY, "guideline_id": "TEST-002", "recommendation": "Synthetic B",
             "source": {"name": "BAD", "category": "test"},
             "version": {"guideline_id": "TEST-002", "version": "2.0", "publication_date": "2026-03-01"}}
    store = GuidelineStore([EvidenceItem.model_validate(_ENTRY), EvidenceItem.model_validate(other)])
    base = {"conditions": ("testdisease",), "symptoms": ("itching",)}
    assert store.available_sources() == {"IADVL": 0, "AAD": 0, "BAD": 1, "NICE": 1}
    assert store.recommend(PatientContext(**base, sources=("BAD",))).guideline_id == "TEST-002"
    assert store.recommend(PatientContext(**base, sources=("NICE",))).guideline_id == "TEST-001"
    assert store.recommend(PatientContext(**base, sources=("AAD",))) is None
    assert store.recommend(PatientContext(**base)) is not None


def test_unsupported_source_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PatientContext(symptoms=("x",), sources=("WHO",))
    with pytest.raises(ValidationError):
        EvidenceItem.model_validate({**_ENTRY, "source": {"name": "WHO", "category": "test"}})


def test_missing_directory_yields_empty_store(tmp_path) -> None:
    assert load_guideline_dir(tmp_path / "absent").list_guidelines() == []


def test_load_directory(tmp_path) -> None:
    import json

    (tmp_path / "a.json").write_text(json.dumps([_ENTRY]), encoding="utf-8")
    assert load_guideline_dir(tmp_path).list_guidelines()[0]["guideline_id"] == "TEST-001"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(guidelines_api, "_store", _store)
    events = []
    monkeypatch.setattr(guidelines_api, "record_event", lambda event, user: events.append(event))
    current = {"uid": "doctor-1", "roles": {"doctor"}, "claims": {"organization_id": "o", "clinic_id": "c"}}
    app = FastAPI()
    app.include_router(guidelines_api.router)
    app.dependency_overrides[get_current_user] = lambda: current
    return TestClient(app), events, current


def test_api_returns_suggestion_only_and_audits_without_patient_data(client) -> None:
    http, events, _ = client
    r = http.post("/api/v1/dermatology/guidelines/recommend", json={"conditions": ["testdisease"], "symptoms": ["itching"]})
    assert r.status_code == 200
    body = r.json()
    assert body["advisory"]["can_decide"] is False
    assert body["recommendation"]["guideline_id"] == "TEST-001"
    assert events[0].metadata == {"matched": True}


def test_api_rejects_extra_fields_and_wrong_role(client) -> None:
    http, _, current = client
    url = "/api/v1/dermatology/guidelines/recommend"
    assert http.post(url, json={"symptoms": ["x"], "name": "Jane"}).status_code == 422
    current["roles"] = {"patient"}
    assert http.post(url, json={"symptoms": ["x"]}).status_code in {401, 403}
