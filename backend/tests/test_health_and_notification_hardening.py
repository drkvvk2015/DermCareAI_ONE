import asyncio

from sqlalchemy import create_engine

import clinical_store
import notification_outbox
import notifications
from idempotency import IdempotencyConflict


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


def test_notification_outbox_rejects_reuse_with_different_payload(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'outbox-conflict.db'}", future=True)
    monkeypatch.setattr(notification_outbox, "_ENGINE", engine)
    payload = {
        "patient_name": "Synthetic Patient",
        "phone": "9000000000",
        "appointment_text": "Synthetic appointment",
        "template_name": "patient_registration",
        "template_language": "en",
        "channels": ["sms"],
    }
    notification_outbox.enqueue_registration(
        organization_id="org-a",
        clinic_id="clinic-1",
        event_key="notify-conflict-001",
        payload=payload,
        channels=["sms"],
    )
    changed = {**payload, "phone": "9111111111"}
    try:
        notification_outbox.enqueue_registration(
            organization_id="org-a",
            clinic_id="clinic-1",
            event_key="notify-conflict-001",
            payload=changed,
            channels=["sms", "whatsapp"],
        )
    except IdempotencyConflict:
        return
    raise AssertionError("notification idempotency key reuse with different payload must fail")


def test_notification_worker_marks_bad_persisted_payload_failed(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'outbox-malformed.db'}", future=True)
    monkeypatch.setattr(notification_outbox, "_ENGINE", engine)
    notification_outbox.enqueue_registration(
        organization_id="org-a",
        clinic_id="clinic-1",
        event_key="notify-bad-payload-001",
        payload={
            "patient_name": "Synthetic Patient",
            "phone": "9000000000",
            "appointment_text": "Synthetic appointment",
            "channels": ["sms"],
        },
        channels=["sms"],
    )
    with engine.begin() as conn:
        row = conn.exec_driver_sql(
            "SELECT * FROM notification_outbox WHERE event_key = ?",
            ("notify-bad-payload-001",),
        ).mappings().one()
        conn.exec_driver_sql(
            "UPDATE notification_outbox SET payload_json = ? WHERE id = ?",
            ('{"not_a_registration": true}', row["id"]),
        )

    row = dict(row)
    row["payload_json"] = '{"not_a_registration": true}'
    asyncio.run(notifications._deliver(row))

    with engine.begin() as conn:
        stored = conn.exec_driver_sql(
            "SELECT attempts, status, last_error FROM notification_outbox WHERE id = ?",
            (row["id"],),
        ).fetchone()
    assert stored[0] == 0
    assert stored[1] == "pending"
    assert stored[2]
