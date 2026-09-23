from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from sqlalchemy import Engine

from storage import compat_connection, create_store_engine, require_postgres_in_production
from dermatology.media_integrity import validate_media_metadata
from typing import Any, Iterator

ENGINE: Engine = create_store_engine("CLINICAL_DATABASE_URL", "CLINICAL_DB_PATH", "clinical.db")
require_postgres_in_production(ENGINE, "Clinical store")


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
            CREATE TABLE IF NOT EXISTS encounters (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                appointment_id TEXT,
                status TEXT NOT NULL,
                complaints_json TEXT NOT NULL,
                examination_json TEXT NOT NULL,
                assessment_json TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_encounters_clinic_patient
              ON encounters(clinic_id, patient_id, opened_at DESC);

            CREATE TABLE IF NOT EXISTS lesions (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                encounter_id TEXT NOT NULL,
                lesion_code TEXT NOT NULL,
                body_site TEXT NOT NULL,
                laterality TEXT,
                morphology_json TEXT NOT NULL,
                size_mm REAL,
                duration_days INTEGER,
                evolution TEXT,
                symptoms_json TEXT NOT NULL,
                clinical_impression TEXT,
                differential_json TEXT NOT NULL,
                confirmed_diagnosis TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(clinic_id, patient_id, lesion_code)
            );
            CREATE INDEX IF NOT EXISTS idx_lesions_patient
              ON lesions(clinic_id, patient_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS lesion_observations (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                lesion_id TEXT NOT NULL,
                encounter_id TEXT NOT NULL,
                lesion_code TEXT NOT NULL,
                body_site TEXT NOT NULL,
                laterality TEXT,
                morphology_json TEXT NOT NULL,
                size_mm REAL,
                duration_days INTEGER,
                evolution TEXT,
                symptoms_json TEXT NOT NULL,
                clinical_impression TEXT,
                differential_json TEXT NOT NULL,
                confirmed_diagnosis TEXT,
                observed_at TEXT NOT NULL,
                observed_by TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_lesion_observations_timeline
              ON lesion_observations(clinic_id, patient_id, lesion_code, observed_at ASC);

            CREATE TABLE IF NOT EXISTS consents (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                document_version TEXT NOT NULL,
                status TEXT NOT NULL,
                granted_at TEXT,
                withdrawn_at TEXT,
                expires_at TEXT,
                recorded_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_consents_active
              ON consents(clinic_id, patient_id, purpose, status);

            CREATE TABLE IF NOT EXISTS clinical_media (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                encounter_id TEXT,
                lesion_id TEXT,
                consent_id TEXT,
                object_url TEXT NOT NULL,
                kind TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                captured_at TEXT NOT NULL,
                captured_by TEXT NOT NULL,
                retention_until TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_media_patient
              ON clinical_media(clinic_id, patient_id, captured_at DESC);

            CREATE TABLE IF NOT EXISTS encounter_signoffs (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                encounter_id TEXT NOT NULL,
                signed_by TEXT NOT NULL,
                signed_at TEXT NOT NULL,
                attestation TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_encounter_signoff
              ON encounter_signoffs(clinic_id, encounter_id);

            CREATE TABLE IF NOT EXISTS encounter_followups (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                encounter_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                due_at TEXT NOT NULL,
                instructions TEXT NOT NULL,
                status TEXT NOT NULL,
                created_by TEXT NOT NULL,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_followups_clinic_due
              ON encounter_followups(clinic_id, due_at, status);

            CREATE TABLE IF NOT EXISTS encounter_ai_reviews (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                encounter_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                media_id TEXT,
                lesion_id TEXT,
                model_name TEXT NOT NULL,
                model_provenance TEXT,
                predicted_label TEXT NOT NULL,
                confidence REAL NOT NULL,
                accepted INTEGER NOT NULL,
                clinician_decision TEXT,
                clinician_override_label TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ai_reviews_encounter
              ON encounter_ai_reviews(clinic_id, encounter_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_ai_reviews_media
              ON encounter_ai_reviews(clinic_id, media_id, created_at DESC);
            """
        )


@contextmanager
def transaction():
    init_store()
    with compat_connection(ENGINE) as conn:
        yield conn


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    for field in (
        "complaints_json", "examination_json", "assessment_json",
        "plan_json", "morphology_json", "symptoms_json", "differential_json",
    ):
        if field in item:
            item[field.removesuffix("_json")] = json.loads(item.pop(field))
    return item


def create_encounter(
    *,
    organization_id: str,
    clinic_id: str,
    patient_id: str,
    doctor_id: str,
    appointment_id: str | None,
    complaints: dict[str, Any],
    examination: dict[str, Any],
    assessment: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    encounter_id = f"ENC-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO encounters
            (id, organization_id, clinic_id, patient_id, doctor_id, appointment_id,
             status, complaints_json, examination_json, assessment_json, plan_json,
             opened_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                encounter_id, organization_id, clinic_id, patient_id, doctor_id,
                appointment_id, json.dumps(complaints, sort_keys=True),
                json.dumps(examination, sort_keys=True),
                json.dumps(assessment, sort_keys=True),
                json.dumps(plan, sort_keys=True),
                now, now, now,
            ),
        )
        row = conn.execute("SELECT * FROM encounters WHERE id = ?", (encounter_id,)).fetchone()
    return _decode(row)


def get_encounter(encounter_id: str, clinic_id: str) -> dict[str, Any] | None:
    init_store()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM encounters WHERE id = ? AND clinic_id = ?",
            (encounter_id, clinic_id),
        ).fetchone()
    return _decode(row) if row else None


def update_encounter(
    encounter_id: str,
    clinic_id: str,
    expected_version: int,
    patch: dict[str, Any],
) -> dict[str, Any]:
    allowed = {"status", "complaints", "examination", "assessment", "plan", "closed_at"}
    unknown = set(patch) - allowed
    if unknown:
        raise ValueError(f"Unsupported encounter fields: {sorted(unknown)}")
    sets: list[str] = []
    values: list[Any] = []
    for key, value in patch.items():
        column = {
            "complaints": "complaints_json",
            "examination": "examination_json",
            "assessment": "assessment_json",
            "plan": "plan_json",
        }.get(key, key)
        sets.append(f"{column} = ?")
        values.append(
            json.dumps(value, sort_keys=True)
            if key in {"complaints", "examination", "assessment", "plan"}
            else value
        )
    if not sets:
        raise ValueError("No changes supplied")
    now = _now()
    sets.extend(["version = version + 1", "updated_at = ?"])
    values.extend([now, encounter_id, clinic_id, expected_version])
    with transaction() as conn:
        cursor = conn.execute(
            f"UPDATE encounters SET {', '.join(sets)} WHERE id = ? AND clinic_id = ? AND version = ?",
            values,
        )
        if cursor.rowcount != 1:
            raise ValueError("Encounter version conflict or record not found")
        row = conn.execute("SELECT * FROM encounters WHERE id = ?", (encounter_id,)).fetchone()
    return _decode(row)


def upsert_lesion(**payload: Any) -> dict[str, Any]:
    init_store()
    lesion_id = payload.get("id") or f"LES-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    v = {
        "id": lesion_id,
        "organization_id": payload["organization_id"],
        "clinic_id": payload["clinic_id"],
        "patient_id": payload["patient_id"],
        "encounter_id": payload["encounter_id"],
        "lesion_code": payload["lesion_code"],
        "body_site": payload["body_site"],
        "laterality": payload.get("laterality"),
        "morphology": payload.get("morphology", {}),
        "size_mm": payload.get("size_mm"),
        "duration_days": payload.get("duration_days"),
        "evolution": payload.get("evolution"),
        "symptoms": payload.get("symptoms", {}),
        "clinical_impression": payload.get("clinical_impression"),
        "differential": payload.get("differential", []),
        "confirmed_diagnosis": payload.get("confirmed_diagnosis"),
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO lesions (
              id, organization_id, clinic_id, patient_id, encounter_id, lesion_code,
              body_site, laterality, morphology_json, size_mm, duration_days,
              evolution, symptoms_json, clinical_impression, differential_json,
              confirmed_diagnosis, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(clinic_id, patient_id, lesion_code) DO UPDATE SET
              encounter_id=excluded.encounter_id,
              body_site=excluded.body_site,
              laterality=excluded.laterality,
              morphology_json=excluded.morphology_json,
              size_mm=excluded.size_mm,
              duration_days=excluded.duration_days,
              evolution=excluded.evolution,
              symptoms_json=excluded.symptoms_json,
              clinical_impression=excluded.clinical_impression,
              differential_json=excluded.differential_json,
              confirmed_diagnosis=excluded.confirmed_diagnosis,
              updated_at=excluded.updated_at
            """,
            (
                v["id"], v["organization_id"], v["clinic_id"], v["patient_id"],
                v["encounter_id"], v["lesion_code"], v["body_site"], v["laterality"],
                json.dumps(v["morphology"], sort_keys=True), v["size_mm"], v["duration_days"],
                v["evolution"], json.dumps(v["symptoms"], sort_keys=True),
                v["clinical_impression"], json.dumps(v["differential"], sort_keys=True),
                v["confirmed_diagnosis"], now, now,
            ),
        )
        row = conn.execute(
            "SELECT * FROM lesions WHERE clinic_id = ? AND patient_id = ? AND lesion_code = ?",
            (v["clinic_id"], v["patient_id"], v["lesion_code"]),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO lesion_observations (
              id, organization_id, clinic_id, patient_id, lesion_id, encounter_id,
              lesion_code, body_site, laterality, morphology_json, size_mm,
              duration_days, evolution, symptoms_json, clinical_impression,
              differential_json, confirmed_diagnosis, observed_at, observed_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"OBS-{uuid.uuid4().hex[:12].upper()}",
                v["organization_id"], v["clinic_id"], v["patient_id"], lesion_id,
                v["encounter_id"], v["lesion_code"], v["body_site"], v["laterality"],
                json.dumps(v["morphology"], sort_keys=True), v["size_mm"],
                v["duration_days"], v["evolution"], json.dumps(v["symptoms"], sort_keys=True),
                v["clinical_impression"], json.dumps(v["differential"], sort_keys=True),
                v["confirmed_diagnosis"], now, str(payload.get("observed_by") or "system"),
            ),
        )
    return _decode(row)


def list_lesion_timeline(*, clinic_id: str, patient_id: str, lesion_code: str) -> list[dict[str, Any]]:
    init_store()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM lesion_observations
            WHERE clinic_id = ? AND patient_id = ? AND lesion_code = ?
            ORDER BY observed_at ASC
            """,
            (clinic_id, patient_id, lesion_code),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        for field in ("morphology_json", "symptoms_json", "differential_json"):
            item[field.removesuffix("_json")] = json.loads(item.pop(field))
        result.append(item)
    return result

def create_consent(**payload: Any) -> dict[str, Any]:
    consent_id = f"CNS-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    with transaction() as conn:
        if payload["status"] == "withdrawn":
            conn.execute(
                """
                UPDATE consents
                SET status = 'withdrawn', withdrawn_at = COALESCE(withdrawn_at, ?)
                WHERE clinic_id = ? AND patient_id = ? AND purpose = ? AND status = 'granted'
                """,
                (payload.get("withdrawn_at") or now, payload["clinic_id"], payload["patient_id"], payload["purpose"]),
            )
        conn.execute(
            """
            INSERT INTO consents (
              id, organization_id, clinic_id, patient_id, purpose, document_version,
              status, granted_at, withdrawn_at, expires_at, recorded_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                consent_id, payload["organization_id"], payload["clinic_id"], payload["patient_id"],
                payload["purpose"], payload["document_version"], payload["status"],
                payload.get("granted_at"), payload.get("withdrawn_at"), payload.get("expires_at"),
                payload["recorded_by"], now,
            ),
        )
        row = conn.execute("SELECT * FROM consents WHERE id = ?", (consent_id,)).fetchone()
    return dict(row)


def has_active_consent(*, clinic_id: str, patient_id: str, purpose: str) -> bool:
    init_store()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM consents
            WHERE clinic_id = ? AND patient_id = ? AND purpose = ?
              AND status = 'granted'
              AND (expires_at IS NULL OR expires_at > ?)
              AND withdrawn_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (clinic_id, patient_id, purpose, _now()),
        ).fetchone()
    return row is not None


def create_media(**payload: Any) -> dict[str, Any]:
    if not has_active_consent(
        clinic_id=payload["clinic_id"],
        patient_id=payload["patient_id"],
        purpose=payload["consent_purpose"],
    ):
        raise PermissionError("Active consent is required before persisting clinical media metadata")

    validate_media_metadata(
        sha256=payload["sha256"],
        mime_type=payload["mime_type"],
        byte_size=int(payload["byte_size"]),
        captured_at=payload["captured_at"],
        retention_until=payload.get("retention_until"),
    )

    media_id = f"IMG-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO clinical_media (
              id, organization_id, clinic_id, patient_id, encounter_id, lesion_id,
              consent_id, object_url, kind, sha256, mime_type, byte_size,
              captured_at, captured_by, retention_until, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                media_id, payload["organization_id"], payload["clinic_id"], payload["patient_id"],
                payload.get("encounter_id"), payload.get("lesion_id"), payload.get("consent_id"),
                payload["object_url"], payload["kind"], payload["sha256"], payload["mime_type"],
                int(payload["byte_size"]), payload["captured_at"], payload["captured_by"],
                payload.get("retention_until"), now,
            ),
        )
        row = conn.execute("SELECT * FROM clinical_media WHERE id = ?", (media_id,)).fetchone()
    return dict(row)



def create_signoff(
    *, organization_id: str, clinic_id: str, encounter_id: str,
    signed_by: str, attestation: str,
) -> dict[str, Any]:
    signoff_id = f"SIG-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    with transaction() as conn:
        existing = conn.execute(
            "SELECT * FROM encounter_signoffs WHERE clinic_id = ? AND encounter_id = ?",
            (clinic_id, encounter_id),
        ).fetchone()
        if existing:
            return dict(existing)
        conn.execute(
            """
            INSERT INTO encounter_signoffs
            (id, organization_id, clinic_id, encounter_id, signed_by, signed_at, attestation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (signoff_id, organization_id, clinic_id, encounter_id, signed_by, now, attestation, now),
        )
        conn.execute(
            """
            UPDATE encounters
            SET status = 'signed', closed_at = COALESCE(closed_at, ?),
                version = version + 1, updated_at = ?
            WHERE id = ? AND clinic_id = ?
            """,
            (now, now, encounter_id, clinic_id),
        )
        row = conn.execute("SELECT * FROM encounter_signoffs WHERE id = ?", (signoff_id,)).fetchone()
    return dict(row)


def get_signoff(*, clinic_id: str, encounter_id: str) -> dict[str, Any] | None:
    init_store()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM encounter_signoffs WHERE clinic_id = ? AND encounter_id = ?",
            (clinic_id, encounter_id),
        ).fetchone()
    return dict(row) if row else None


def create_followup(
    *, organization_id: str, clinic_id: str, encounter_id: str, patient_id: str,
    due_at: str, instructions: str, created_by: str,
) -> dict[str, Any]:
    followup_id = f"FUP-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO encounter_followups
            (id, organization_id, clinic_id, encounter_id, patient_id, due_at,
             instructions, status, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?, ?)
            """,
            (
                followup_id, organization_id, clinic_id, encounter_id, patient_id,
                due_at, instructions, created_by, now, now,
            ),
        )
        row = conn.execute(
            "SELECT * FROM encounter_followups WHERE id = ?", (followup_id,)
        ).fetchone()
    return dict(row)


def list_followups(*, clinic_id: str, patient_id: str | None = None) -> list[dict[str, Any]]:
    init_store()
    with _connect() as conn:
        if patient_id:
            rows = conn.execute(
                """
                SELECT * FROM encounter_followups
                WHERE clinic_id = ? AND patient_id = ?
                ORDER BY due_at ASC
                """,
                (clinic_id, patient_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM encounter_followups
                WHERE clinic_id = ?
                ORDER BY due_at ASC
                """,
                (clinic_id,),
            ).fetchall()
    return [dict(row) for row in rows]


def record_ai_review(
    *, organization_id: str, clinic_id: str, encounter_id: str,
    request_id: str, media_id: str | None, lesion_id: str | None,
    model_name: str, model_provenance: str | None,
    predicted_label: str, confidence: float, accepted: bool,
) -> dict[str, Any]:
    review_id = f"AIR-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO encounter_ai_reviews
            (id, organization_id, clinic_id, encounter_id, request_id, media_id, lesion_id, model_name,
             model_provenance, predicted_label, confidence, accepted, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id, organization_id, clinic_id, encounter_id, request_id,
                media_id, lesion_id, model_name, model_provenance, predicted_label,
                float(confidence), int(accepted), now,
            ),
        )
        row = conn.execute(
            "SELECT * FROM encounter_ai_reviews WHERE id = ?", (review_id,)
        ).fetchone()
    return dict(row)


def review_ai_assessment(
    *, clinic_id: str, encounter_id: str, review_id: str, clinician_decision: str,
    clinician_override_label: str | None, reviewed_by: str,
) -> dict[str, Any]:
    if clinician_decision not in {"accepted", "overridden", "rejected"}:
        raise ValueError("Unsupported clinician decision")
    now = _now()
    with transaction() as conn:
        cursor = conn.execute(
            """
            UPDATE encounter_ai_reviews
            SET clinician_decision = ?, clinician_override_label = ?,
                reviewed_by = ?, reviewed_at = ?
            WHERE id = ? AND clinic_id = ? AND encounter_id = ?
            """,
            (
                clinician_decision,
                clinician_override_label,
                reviewed_by,
                now,
                review_id,
                clinic_id,
                encounter_id,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError("AI review not found")
        row = conn.execute(
            "SELECT * FROM encounter_ai_reviews WHERE id = ?", (review_id,)
        ).fetchone()
    return dict(row)


def has_pending_ai_reviews(*, clinic_id: str, encounter_id: str) -> bool:
    init_store()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM encounter_ai_reviews
            WHERE clinic_id = ? AND encounter_id = ?
              AND clinician_decision IS NULL
            LIMIT 1
            """,
            (clinic_id, encounter_id),
        ).fetchone()
    return row is not None


def list_ai_reviews(*, clinic_id: str, encounter_id: str) -> list[dict[str, Any]]:
    init_store()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM encounter_ai_reviews
            WHERE clinic_id = ? AND encounter_id = ?
            ORDER BY created_at DESC
            """,
            (clinic_id, encounter_id),
        ).fetchall()
    return [dict(row) for row in rows]



def get_patient_clinical_summary(*, clinic_id: str, patient_id: str) -> dict[str, Any]:
    init_store()
    with _connect() as conn:
        encounters = conn.execute(
            """
            SELECT * FROM encounters
            WHERE clinic_id = ? AND patient_id = ?
            ORDER BY opened_at DESC
            """,
            (clinic_id, patient_id),
        ).fetchall()
        lesions = conn.execute(
            """
            SELECT * FROM lesions
            WHERE clinic_id = ? AND patient_id = ?
            ORDER BY updated_at DESC
            """,
            (clinic_id, patient_id),
        ).fetchall()
        followups = conn.execute(
            """
            SELECT * FROM encounter_followups
            WHERE clinic_id = ? AND patient_id = ?
            ORDER BY due_at ASC
            """,
            (clinic_id, patient_id),
        ).fetchall()
        signoffs = conn.execute(
            """
            SELECT s.*
            FROM encounter_signoffs s
            JOIN encounters e ON e.id = s.encounter_id
            WHERE s.clinic_id = ? AND e.patient_id = ?
            ORDER BY s.signed_at DESC
            """,
            (clinic_id, patient_id),
        ).fetchall()
    return {
        "patient_id": patient_id,
        "encounters": [_decode(row) for row in encounters],
        "lesions": [_decode(row) for row in lesions],
        "followups": [dict(row) for row in followups],
        "signoffs": [dict(row) for row in signoffs],
    }
