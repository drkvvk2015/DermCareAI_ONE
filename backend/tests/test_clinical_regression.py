from __future__ import annotations

import clinical


def _user() -> dict:
    return {
        "uid": "doctor-1",
        "claims": {"organization_id": "org-1", "clinic_id": "clinic-1"},
    }


def test_followup_audit_path_has_no_undefined_provenance_names(monkeypatch):
    monkeypatch.setattr(
        clinical,
        "get_encounter",
        lambda encounter_id, clinic_id: {"id": encounter_id, "patient_id": "patient-1", "status": "open"},
    )
    monkeypatch.setattr(
        clinical,
        "create_followup",
        lambda **kwargs: {"id": "FUP-1", **kwargs},
    )
    events = []
    monkeypatch.setattr(clinical, "record_event", lambda event, user: events.append(event))

    result = clinical.post_followup(
        "ENC-1",
        clinical.FollowupCreate(due_at="2026-10-01T10:00:00Z", instructions="Review lesion response."),
        _user(),
    )

    assert result["id"] == "FUP-1"
    assert events[0].metadata["encounter_id"] == "ENC-1"
    assert "media_id" not in events[0].metadata
    assert "lesion_id" not in events[0].metadata


def test_ai_review_audit_preserves_media_and_lesion_provenance(monkeypatch):
    monkeypatch.setattr(
        clinical,
        "get_encounter",
        lambda encounter_id, clinic_id: {"id": encounter_id, "patient_id": "patient-1", "status": "open"},
    )
    monkeypatch.setattr(
        clinical,
        "get_media",
        lambda **kwargs: {"id": "IMG-1", "encounter_id": "ENC-1", "organization_id": "org-1", "lesion_id": "LES-1"},
    )
    monkeypatch.setattr(
        clinical,
        "get_lesion",
        lambda **kwargs: {"id": "LES-1", "encounter_id": "ENC-1", "organization_id": "org-1"},
    )
    monkeypatch.setattr(
        clinical,
        "record_ai_review",
        lambda **kwargs: {"id": "AIR-1", **kwargs},
    )
    events = []
    monkeypatch.setattr(clinical, "record_event", lambda event, user: events.append(event))

    result = clinical.post_ai_review(
        "ENC-1",
        clinical.AIReviewCreate(
            media_id="IMG-1",
            lesion_id="LES-1",
            request_id="REQ-1",
            model_name="research-model",
            predicted_label="uncertain",
            confidence=0.2,
        ),
        _user(),
    )

    assert result["id"] == "AIR-1"
    assert events[0].metadata["media_id"] == "IMG-1"
    assert events[0].metadata["lesion_id"] == "LES-1"
