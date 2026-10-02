import asyncio

from PIL import Image
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
    assert all(row["delivery_key"] for row in first)
    assert {row["delivery_key"] for row in first} == {row["delivery_key"] for row in second}

    claimed = notification_outbox.claim_batch(limit=5)
    assert len(claimed) == 2
    assert notification_outbox.claim_batch(limit=5) == []

    for row in claimed:
        notification_outbox.mark_sent(row_id=row["id"])
    assert notification_outbox.claim_batch(limit=5) == []


def test_notification_events_with_same_payload_require_distinct_event_keys(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'outbox-events.db'}", future=True)
    monkeypatch.setattr(notification_outbox, "_ENGINE", engine)
    payload = {
        "patient_name": "Synthetic Patient",
        "phone": "9000000000",
        "appointment_text": "Synthetic appointment",
        "template_name": "patient_registration",
        "template_language": "en",
        "channels": ["sms"],
    }

    first = notification_outbox.enqueue_registration(
        organization_id="org-a",
        clinic_id="clinic-1",
        event_key="notify-event-001",
        payload=payload,
        channels=["sms"],
    )
    second = notification_outbox.enqueue_registration(
        organization_id="org-a",
        clinic_id="clinic-1",
        event_key="notify-event-002",
        payload=payload,
        channels=["sms"],
    )

    assert first[0]["id"] != second[0]["id"]
    assert first[0]["delivery_key"] != second[0]["delivery_key"]


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


def test_notification_outbox_minimizes_payload_after_delivery_and_expires_history(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'outbox-retention.db'}", future=True)
    monkeypatch.setattr(notification_outbox, "_ENGINE", engine)
    payload = {
        "patient_name": "Synthetic Patient",
        "phone": "9000000000",
        "appointment_text": "Synthetic appointment",
        "template_name": "patient_registration",
        "template_language": "en",
        "channels": ["sms"],
    }

    rows = notification_outbox.enqueue_registration(
        organization_id="org-a",
        clinic_id="clinic-1",
        event_key="notify-retention-001",
        payload=payload,
        channels=["sms"],
    )
    row_id = rows[0]["id"]

    with engine.begin() as conn:
        before = conn.exec_driver_sql(
            "SELECT retention_until FROM notification_outbox WHERE id = ?",
            (row_id,),
        ).scalar_one()

    notification_outbox.mark_sent(row_id=row_id, provider_message_id="provider-1")

    with engine.begin() as conn:
        stored = conn.exec_driver_sql(
            "SELECT payload_json, retention_until, status FROM notification_outbox WHERE id = ?",
            (row_id,),
        ).one()
    assert stored[0] == "{}"
    assert stored[1] == before
    assert stored[2] == "sent"

    with engine.begin() as conn:
        conn.exec_driver_sql(
            "UPDATE notification_outbox SET retention_until = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", row_id),
        )

    assert notification_outbox.purge_expired() == 1
    with engine.begin() as conn:
        assert conn.exec_driver_sql(
            "SELECT 1 FROM notification_outbox WHERE id = ?",
            (row_id,),
        ).fetchone() is None


def test_model_service_translates_decompression_bomb_to_bounded_upload(monkeypatch):
    from app import ModelService

    service = ModelService()
    service.mode = "test"

    def raise_decompression_bomb(_source):
        raise Image.DecompressionBombError("synthetic oversized image")

    monkeypatch.setattr("app.Image.open", raise_decompression_bomb)

    try:
        service.process_image(b"synthetic")
    except ValueError as exc:
        assert "dimensions exceed configured safety limit" in str(exc)
    else:
        raise AssertionError("Pillow decompression bomb must be translated to ValueError")
