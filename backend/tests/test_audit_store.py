import os
from uuid import uuid4

os.environ["AUDIT_DB_PATH"] = f"/tmp/dermcareai-audit-test-{uuid4().hex}.db"

from audit import AuditEvent, list_audit_events, record_event


USER = {"uid": "doctor-1", "roles": {"doctor"}, "claims": {}}


def test_hash_chain_and_readback() -> None:
    first = record_event(
        AuditEvent(
            action="encounter_created",
            resource_type="encounter",
            resource_id="ENC-1",
            metadata={"patient_id": "P-1"},
        ),
        USER,
    )
    second = record_event(
        AuditEvent(
            action="consent_recorded",
            resource_type="consent",
            resource_id="CNS-1",
            metadata={"patient_id": "P-1"},
        ),
        USER,
    )

    assert first["previous_hash"] == "GENESIS"
    assert second["previous_hash"] == first["event_hash"]

    rows = list_audit_events(100, USER)
    assert rows[0]["event_hash"] == second["event_hash"]
    assert rows[0]["metadata"]["patient_id"] == "P-1"
