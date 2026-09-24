from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Engine

from storage import create_store_engine, execute, require_postgres_in_production, transaction

ENGINE: Engine = create_store_engine("COMMERCE_DATABASE_URL", "COMMERCE_DB_PATH", "commerce.db")
require_postgres_in_production(ENGINE, "Prescription dispense ledger")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_store() -> None:
    with ENGINE.begin() as conn:
        execute(conn, """
            CREATE TABLE IF NOT EXISTS prescription_dispense_ledger (
                prescription_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                status TEXT NOT NULL,
                allocations_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def begin_or_get(*, prescription_id: str, organization_id: str, clinic_id: str, patient_id: str) -> dict[str, Any]:
    """Create an idempotency ledger row or return the existing tenant-scoped row."""
    init_store()
    now = _now()
    with transaction(ENGINE) as conn:
        row = execute(
            conn,
            """SELECT * FROM prescription_dispense_ledger
               WHERE prescription_id = :prescription_id
                 AND organization_id = :organization_id
                 AND clinic_id = :clinic_id""",
            {"prescription_id": prescription_id, "organization_id": organization_id, "clinic_id": clinic_id},
        ).mappings().first()
        if row:
            if row["patient_id"] != patient_id:
                raise PermissionError("Dispense ledger patient mismatch")
            return _decode(row)

        execute(
            conn,
            """INSERT INTO prescription_dispense_ledger
               (prescription_id, organization_id, clinic_id, patient_id, status, allocations_json, created_at, updated_at)
               VALUES (:prescription_id, :organization_id, :clinic_id, :patient_id, 'pending', :allocations_json, :created_at, :updated_at)""",
            {
                "prescription_id": prescription_id,
                "organization_id": organization_id,
                "clinic_id": clinic_id,
                "patient_id": patient_id,
                "allocations_json": "{}",
                "created_at": now,
                "updated_at": now,
            },
        )
        row = execute(
            conn, "SELECT * FROM prescription_dispense_ledger WHERE prescription_id = :prescription_id",
            {"prescription_id": prescription_id},
        ).mappings().first()
    return _decode(row)


def claim_pending(*, prescription_id: str, organization_id: str, clinic_id: str, lease_seconds: int = 900) -> bool:
    """Claim a pending dispense so concurrent requests cannot allocate the same prescription twice.

    A stale processing lease can be reclaimed after the bounded lease interval, allowing
    recovery after a worker crash without silently treating an active request as complete.
    """
    init_store()
    now = datetime.now(timezone.utc)
    with transaction(ENGINE) as conn:
        row = execute(
            conn,
            """SELECT status, updated_at FROM prescription_dispense_ledger
               WHERE prescription_id = :prescription_id
                 AND organization_id = :organization_id
                 AND clinic_id = :clinic_id""",
            {"prescription_id": prescription_id, "organization_id": organization_id, "clinic_id": clinic_id},
        ).mappings().first()
        if row is None:
            raise KeyError(prescription_id)
        if row["status"] == "allocated" or row["status"] == "completed":
            return False
        stale = False
        if row["status"] == "processing":
            try:
                stale = (now - datetime.fromisoformat(str(row["updated_at"]))).total_seconds() >= lease_seconds
            except ValueError:
                stale = True
        if row["status"] not in {"pending", "processing"} and not stale:
            return False
        if row["status"] == "processing" and not stale:
            return False
        updated = execute(
            conn,
            """UPDATE prescription_dispense_ledger
               SET status = 'processing', updated_at = :updated_at
               WHERE prescription_id = :prescription_id
                 AND organization_id = :organization_id
                 AND clinic_id = :clinic_id
                 AND status = :expected_status""",
            {
                "prescription_id": prescription_id,
                "organization_id": organization_id,
                "clinic_id": clinic_id,
                "expected_status": "processing" if stale else "pending",
                "updated_at": now.isoformat(),
            },
        )
        return bool(updated.rowcount)

 
def record_allocated(*, prescription_id: str, organization_id: str, clinic_id: str, allocations: dict[str, Any]) -> dict[str, Any]:
    init_store()
    now = _now()
    with transaction(ENGINE) as conn:
        execute(
            conn,
            """UPDATE prescription_dispense_ledger
               SET status = 'allocated', allocations_json = :allocations_json, updated_at = :updated_at
               WHERE prescription_id = :prescription_id AND organization_id = :organization_id AND clinic_id = :clinic_id""",
            {
                "prescription_id": prescription_id,
                "organization_id": organization_id,
                "clinic_id": clinic_id,
                "allocations_json": json.dumps(allocations, sort_keys=True, default=str),
                "updated_at": now,
            },
        )
        row = execute(
            conn, "SELECT * FROM prescription_dispense_ledger WHERE prescription_id = :prescription_id",
            {"prescription_id": prescription_id},
        ).mappings().first()
    if row is None:
        raise KeyError(prescription_id)
    return _decode(row)


def finalize(*, prescription_id: str, organization_id: str, clinic_id: str) -> dict[str, Any]:
    init_store()
    now = _now()
    with transaction(ENGINE) as conn:
        execute(
            conn,
            """UPDATE prescription_dispense_ledger
               SET status = 'completed', updated_at = :updated_at
               WHERE prescription_id = :prescription_id
                 AND organization_id = :organization_id
                 AND clinic_id = :clinic_id
                 AND status IN ('pending', 'processing', 'allocated')""",
            {"prescription_id": prescription_id, "organization_id": organization_id, "clinic_id": clinic_id, "updated_at": now},
        )
        row = execute(
            conn, "SELECT * FROM prescription_dispense_ledger WHERE prescription_id = :prescription_id",
            {"prescription_id": prescription_id},
        ).mappings().first()
    if row is None:
        raise KeyError(prescription_id)
    return _decode(row)


def _decode(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["allocations"] = json.loads(item.pop("allocations_json"))
    return item
