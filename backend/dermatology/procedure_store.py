from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Engine
from storage import compat_connection, create_store_engine, require_postgres_in_production

ENGINE: Engine = create_store_engine("CLINICAL_DATABASE_URL", "CLINICAL_DB_PATH", "clinical.db")
require_postgres_in_production(ENGINE, "Dermatology procedure store")

@contextmanager
def _connect():
    with compat_connection(ENGINE) as conn:
        yield conn

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def init_store() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS dermatology_procedures (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                encounter_id TEXT NOT NULL,
                procedure_type TEXT NOT NULL,
                body_site TEXT NOT NULL,
                indication TEXT NOT NULL,
                consent_id TEXT NOT NULL,
                performed_by TEXT NOT NULL,
                performed_at TEXT NOT NULL,
                outcome TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_derm_procedures_patient
              ON dermatology_procedures(clinic_id, patient_id, performed_at DESC);
            """
        )

def create_procedure(**payload: Any) -> dict[str, Any]:
    init_store()
    procedure_id = f"PROC-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO dermatology_procedures (
                id, organization_id, clinic_id, patient_id, encounter_id,
                procedure_type, body_site, indication, consent_id,
                performed_by, performed_at, outcome, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                procedure_id, payload["organization_id"], payload["clinic_id"],
                payload["patient_id"], payload["encounter_id"], payload["procedure_type"],
                payload["body_site"], payload["indication"], payload["consent_id"],
                payload["performed_by"], payload["performed_at"], payload.get("outcome"), now,
            ),
        )
        row = conn.execute("SELECT * FROM dermatology_procedures WHERE id = ?", (procedure_id,)).fetchone()
    return dict(row)

def list_procedures(*, clinic_id: str, patient_id: str) -> list[dict[str, Any]]:
    init_store()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM dermatology_procedures
            WHERE clinic_id = ? AND patient_id = ?
            ORDER BY performed_at DESC
            """,
            (clinic_id, patient_id),
        ).fetchall()
    return [dict(row) for row in rows]
