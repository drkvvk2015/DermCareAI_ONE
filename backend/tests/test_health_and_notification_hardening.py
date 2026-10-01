import os
from io import BytesIO

from sqlalchemy import create_engine

import clinical_store
import notification_outbox


def test_public_health_does_not_expose_model_metadata():
    from app import health_check

    payload = health_check()
    assert payload["status"] == "ok"
    assert "service" not in payload
    assert "models" not in payload


def test_notification_outbox_is_idempotent_and_claimable(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'outbox.db'}", future=True)
    monkeypatch.setattr(notification_outbox, "_ENGINE", engine)

    payload = {
        "patient_name": "Synthetic Patient",
        "phone": "9000000000",
        "appointment_text": "Synthetic appointment",
        "template_name": "patient_registration",
        "template_language": "en",
        "channels": ["whatsapp", "sms"],
    }

    first = notification_outbox.enqueue_registration(
        organization_id="org-a",
        clinic_id="clinic-1",
        event_key="notify-test-001",
        payload=payload,
        channels=payload["channels"],
    )
    second = notification_outbox.enqueue_registration(
        organization_id="org-a",
        clinic_id="clinic-1",
        event_key="notify-test-001",
        payload=payload,
        channels=payload["channels"],
    )

    assert len(first) == 2
    assert len(second) == 2
    assert {row["id"] for row in first} == {row["id"] for row in second}

    claimed = notification_outbox.claim_batch(limit=5)
    assert len(claimed) == 2
    assert notification_outbox.claim_batch(limit=5) == []

    for row in claimed:
        notification_outbox.mark_sent(row_id=row["id"])
    assert notification_outbox.claim_batch(limit=5) == []
