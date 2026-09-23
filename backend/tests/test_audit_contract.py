from audit import AuditEvent


def test_audit_event_uses_independent_metadata_defaults() -> None:
    first = AuditEvent(action="read", resource_type="patient", resource_id="p1")
    second = AuditEvent(action="read", resource_type="patient", resource_id="p2")

    first.metadata["source"] = "test"

    assert second.metadata == {}


def test_audit_event_rejects_unknown_fields() -> None:
    try:
        AuditEvent(
            action="read",
            resource_type="patient",
            resource_id="p1",
            unexpected="value",
        )
    except Exception as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("unknown audit fields must be rejected")
