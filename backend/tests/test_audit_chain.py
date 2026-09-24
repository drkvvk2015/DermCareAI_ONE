import os
from uuid import uuid4

os.environ.setdefault("AUDIT_DB_PATH", f"/tmp/dermcareai-audit-hardening-{uuid4().hex}.db")

from audit import AuditEvent, db, record_event


def test_audit_hash_chain_state_advances():
    user = {"uid": "doctor-a", "roles": {"doctor"}}
    first = record_event(
        AuditEvent(action="one", resource_type="test", resource_id="1"),
        user,
    )
    second = record_event(
        AuditEvent(action="two", resource_type="test", resource_id="2", correlation_id="corr-1"),
        user,
    )
    assert second["previous_hash"] == first["event_hash"]
    with db() as conn:
        state = conn.execute("SELECT last_hash FROM audit_chain_state WHERE id = 1").fetchone()
    assert state["last_hash"] == second["event_hash"]
