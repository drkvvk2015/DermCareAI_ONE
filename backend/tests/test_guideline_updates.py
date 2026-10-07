import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import get_current_user
from dermatology import guidelines_api
from medguide_ai import updates
from medguide_ai.updates import MonitoredDocument, acknowledge, check_for_updates, list_pending

URL = "https://www.nice.org.uk/guidance/synthetic-doc"


def _configure(tmp_path, entries=None):
    entries = entries or [{"source": "NICE", "url": URL, "label": "Synthetic NICE doc"}]
    (tmp_path / "sources.json").write_text(json.dumps(entries), encoding="utf-8")


def test_untrusted_urls_are_rejected() -> None:
    with pytest.raises(ValueError):
        MonitoredDocument(source="NICE", url="http://www.nice.org.uk/x", label="x")
    with pytest.raises(ValueError):
        MonitoredDocument(source="NICE", url="https://evil.example.com/x", label="x")
    with pytest.raises(ValueError):
        MonitoredDocument(source="AAD", url="https://www.nice.org.uk/x", label="x")


def test_baseline_then_change_creates_pending_notice_only(tmp_path) -> None:
    _configure(tmp_path)
    first = check_for_updates(tmp_path, fetch=lambda url: b"v1")
    assert first["baselined"] == [URL] and first["changed"] == []
    same = check_for_updates(tmp_path, fetch=lambda url: b"v1")
    assert same["unchanged"] == [URL]
    changed = check_for_updates(tmp_path, fetch=lambda url: b"v2")
    assert len(changed["changed"]) == 1
    pending = list_pending(tmp_path)
    assert pending[0]["status"] == "pending_review"
    assert [p.name for p in tmp_path.glob("*.json")] == ["sources.json"]


def test_fetch_errors_are_reported_without_notice(tmp_path) -> None:
    _configure(tmp_path)

    def boom(url: str) -> bytes:
        raise TimeoutError

    result = check_for_updates(tmp_path, fetch=boom)
    assert result["errors"] == [{"url": URL, "error": "TimeoutError"}]
    assert list_pending(tmp_path) == []


def test_acknowledge_requires_valid_id_and_outcome(tmp_path) -> None:
    _configure(tmp_path)
    check_for_updates(tmp_path, fetch=lambda url: b"v1")
    check_for_updates(tmp_path, fetch=lambda url: b"v2")
    notice_id = list_pending(tmp_path)[0]["id"]
    with pytest.raises(ValueError):
        acknowledge(tmp_path, "../state", "dr", "entry_updated")
    with pytest.raises(ValueError):
        acknowledge(tmp_path, notice_id, "dr", "auto_approved")
    notice = acknowledge(tmp_path, notice_id, "doctor-1", "entry_updated")
    assert notice["reviewed_by"] == "doctor-1"
    assert list_pending(tmp_path) == []


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("GUIDELINES_DIR", str(tmp_path))
    guidelines_api.reset_store()
    monkeypatch.setattr(guidelines_api, "record_event", lambda event, user: None)
    monkeypatch.setattr(guidelines_api, "check_for_updates", lambda directory: updates.check_for_updates(directory, fetch=lambda u: b"x"))
    current = {"uid": "doctor-1", "roles": {"doctor"}, "claims": {"organization_id": "o", "clinic_id": "c"}}
    app = FastAPI()
    app.include_router(guidelines_api.router)
    app.dependency_overrides[get_current_user] = lambda: current
    _configure(tmp_path)
    yield TestClient(app), current, tmp_path
    guidelines_api.reset_store()


def test_only_admin_can_trigger_check_and_doctor_can_review(client) -> None:
    http, current, tmp_path = client
    assert http.post("/api/v1/dermatology/guidelines/updates/check").status_code in {401, 403}
    current["roles"] = {"admin"}
    assert http.post("/api/v1/dermatology/guidelines/updates/check").status_code == 200
    check_for_updates(tmp_path, fetch=lambda u: b"changed")
    current["roles"] = {"doctor"}
    pending = http.get("/api/v1/dermatology/guidelines/updates").json()["pending"]
    assert len(pending) == 1
    bad = http.post(f"/api/v1/dermatology/guidelines/updates/{pending[0]['id']}/review", json={"outcome": "auto"})
    assert bad.status_code == 422
    ok = http.post(f"/api/v1/dermatology/guidelines/updates/{pending[0]['id']}/review", json={"outcome": "no_clinical_change"})
    assert ok.status_code == 200 and ok.json()["reviewed_by"] == "doctor-1"
    missing = http.post("/api/v1/dermatology/guidelines/updates/NOPE-1/review", json={"outcome": "no_clinical_change"})
    assert missing.status_code == 404


def test_guideline_files_are_reloaded_automatically_on_change(tmp_path, monkeypatch) -> None:
    import json as _json
    import os

    from tests.test_guidelines import _ENTRY

    monkeypatch.setenv("GUIDELINES_DIR", str(tmp_path))
    guidelines_api.reset_store()
    assert guidelines_api._store().list_guidelines() == []

    path = tmp_path / "g.json"
    path.write_text(_json.dumps([_ENTRY]), encoding="utf-8")
    assert [g["guideline_id"] for g in guidelines_api._store().list_guidelines()] == ["TEST-001"]

    updated = {**_ENTRY, "recommendation": "Synthetic updated"}
    path.write_text(_json.dumps([updated]), encoding="utf-8")
    os.utime(path, ns=(1, 2_000_000_000))
    assert guidelines_api._store()._items["TEST-001"].recommendation == "Synthetic updated"

    path.write_text("{ not valid json", encoding="utf-8")
    os.utime(path, ns=(1, 3_000_000_000))
    assert guidelines_api._store()._items["TEST-001"].recommendation == "Synthetic updated"
    assert guidelines_api._loaded.load_error is True

    unapproved = {k: v for k, v in _ENTRY.items() if k != "approved_by"}
    path.write_text(_json.dumps([unapproved]), encoding="utf-8")
    os.utime(path, ns=(1, 4_000_000_000))
    assert guidelines_api._store()._items["TEST-001"].recommendation == "Synthetic updated"
    assert guidelines_api._loaded.load_error is True
    guidelines_api.reset_store()
