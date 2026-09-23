from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Engine

from storage import create_store_engine, execute, require_postgres_in_production, transaction

ENGINE: Engine = create_store_engine("CLINICAL_DATABASE_URL", "CLINICAL_DB_PATH", "clinical.db")
require_postgres_in_production(ENGINE, "Prescription store")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_store() -> None:
    with ENGINE.begin() as conn:
        execute(conn, """
            CREATE TABLE IF NOT EXISTS prescriptions (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                encounter_id TEXT NOT NULL,
                status TEXT NOT NULL,
                instructions TEXT NOT NULL,
                items_json TEXT NOT NULL,
                prescribed_by TEXT NOT NULL,
                signed_at TEXT,
                cancelled_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        try:
            execute(conn, "ALTER TABLE prescriptions ADD COLUMN dispense_status TEXT NOT NULL DEFAULT 'not_dispensed'")
        except Exception:
            pass
        execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_prescriptions_patient
            ON prescriptions(clinic_id, patient_id, created_at DESC)
        """)
        execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_prescriptions_encounter
            ON prescriptions(clinic_id, encounter_id, created_at DESC)
        """)


def create_prescription(
    *,
    organization_id: str,
    clinic_id: str,
    patient_id: str,
    encounter_id: str,
    instructions: str,
    items: list[dict[str, Any]],
    prescribed_by: str,
) -> dict[str, Any]:
    init_store()
    if not items:
        raise ValueError("At least one medication item is required")
    prescription_id = f"RX-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    with transaction(ENGINE) as conn:
        execute(
            conn,
            """
            INSERT INTO prescriptions (
                id, organization_id, clinic_id, patient_id, encounter_id,
                status, instructions, items_json, prescribed_by,
                created_at, updated_at
            ) VALUES (
                :id, :organization_id, :clinic_id, :patient_id, :encounter_id,
                'active', :instructions, :items_json, :prescribed_by,
                :created_at, :updated_at
            )
            """,
            {
                "id": prescription_id,
                "organization_id": organization_id,
                "clinic_id": clinic_id,
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "instructions": instructions,
                "items_json": json.dumps(items, sort_keys=True),
                "prescribed_by": prescribed_by,
                "created_at": now,
                "updated_at": now,
            },
        )
        row = execute(
            conn,
            "SELECT * FROM prescriptions WHERE id = :id",
            {"id": prescription_id},
        ).mappings().first()
    return _decode(row)


def _decode(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    item = dict(row)
    item["items"] = json.loads(item.pop("items_json"))
    return item


def get_prescription(
    prescription_id: str,
    *,
    organization_id: str,
    clinic_id: str,
) -> dict[str, Any] | None:
    init_store()
    with ENGINE.connect() as conn:
        row = execute(
            conn,
            """
            SELECT * FROM prescriptions
            WHERE id = :id AND organization_id = :organization_id AND clinic_id = :clinic_id
            """,
            {"id": prescription_id, "organization_id": organization_id, "clinic_id": clinic_id},
        ).mappings().first()
    return _decode(row) if row else None


def list_prescriptions(
    patient_id: str,
    *,
    organization_id: str,
    clinic_id: str,
) -> list[dict[str, Any]]:
    init_store()
    with ENGINE.connect() as conn:
        rows = execute(
            conn,
            """
            SELECT * FROM prescriptions
            WHERE patient_id = :patient_id
              AND organization_id = :organization_id
              AND clinic_id = :clinic_id
            ORDER BY created_at DESC
            """,
            {"patient_id": patient_id, "organization_id": organization_id, "clinic_id": clinic_id},
        ).mappings().all()
    return [_decode(row) for row in rows]


def cancel_prescription(
    prescription_id: str,
    *,
    organization_id: str,
    clinic_id: str,
) -> dict[str, Any]:
    init_store()
    now = _now()
    with transaction(ENGINE) as conn:
        row = execute(
            conn,
            """
            SELECT * FROM prescriptions
            WHERE id = :id AND organization_id = :organization_id AND clinic_id = :clinic_id
            """,
            {"id": prescription_id, "organization_id": organization_id, "clinic_id": clinic_id},
        ).mappings().first()
        if row is None:
            raise KeyError(prescription_id)
        if row["status"] != "active":
            raise ValueError("Only active prescriptions can be cancelled")
        execute(
            conn,
            """
            UPDATE prescriptions
            SET status = 'cancelled', cancelled_at = :cancelled_at, updated_at = :updated_at
            WHERE id = :id AND organization_id = :organization_id AND clinic_id = :clinic_id AND status = 'active'
            """,
            {
                "id": prescription_id,
                "organization_id": organization_id,
                "clinic_id": clinic_id,
                "cancelled_at": now,
                "updated_at": now,
            },
        )
        updated = execute(
            conn,
            "SELECT * FROM prescriptions WHERE id = :id",
            {"id": prescription_id},
        ).mappings().first()
    return _decode(updated)
