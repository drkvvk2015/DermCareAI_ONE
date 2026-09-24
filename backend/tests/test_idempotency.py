import os
from uuid import uuid4

os.environ.setdefault("CLINICAL_DB_PATH", f"/tmp/dermcareai-idempotency-{uuid4().hex}.db")

from idempotency import begin_operation, complete_operation


def test_idempotency_returns_cached_response_for_same_request():
    kwargs = dict(
        scope="clinical",
        organization_id="org-a",
        clinic_id="clinic-a",
        actor_id="doctor-a",
        operation_key="sync-test-001",
        payload={"method": "POST", "body": {"value": 1}},
    )
    assert begin_operation(**kwargs) is None
    complete_operation(scope=kwargs["scope"], organization_id=kwargs["organization_id"], clinic_id=kwargs["clinic_id"], actor_id=kwargs["actor_id"], operation_key=kwargs["operation_key"], response={"id": "LES-1"})
    assert begin_operation(**kwargs) == {"id": "LES-1"}


def test_idempotency_rejects_key_reuse_with_different_payload():
    kwargs = dict(
        scope="clinical",
        organization_id="org-a",
        clinic_id="clinic-a",
        actor_id="doctor-a",
        operation_key="sync-test-002",
        payload={"method": "POST", "body": {"value": 1}},
    )
    assert begin_operation(**kwargs) is None
    complete_operation(scope=kwargs["scope"], organization_id=kwargs["organization_id"], clinic_id=kwargs["clinic_id"], actor_id=kwargs["actor_id"], operation_key=kwargs["operation_key"], response={"id": "LES-2"})
    try:
        begin_operation(
            **{**kwargs, "payload": {"method": "POST", "body": {"value": 2}}}
        )
    except ValueError as exc:
        assert "different request" in str(exc)
    else:
        raise AssertionError("reusing an idempotency key with different input must fail")
