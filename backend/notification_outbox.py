from __future__ import annotations

import json
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from idempotency import IdempotencyConflict, request_hash
from sqlalchemy import inspect
from storage import compat_connection, create_store_engine, require_postgres_in_production


_ENGINE = create_store_engine(
    "CLINICAL_DATABASE_URL",
    "CLINICAL_DB_PATH",
    "clinical.db",
)
require_postgres_in_production(_ENGINE, "Notification outbox")
_LOCK = Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def init_outbox() -> None:
    with compat_connection(_ENGINE) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS notification_outbox (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                event_key TEXT NOT NULL,
                channel TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                available_at TEXT NOT NULL,
                locked_until TEXT,
                provider_message_id TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sent_at TEXT,
                UNIQUE(organization_id, clinic_id, event_key, channel)
            );
            CREATE INDEX IF NOT EXISTS idx_notification_outbox_ready
              ON notification_outbox(status, available_at, created_at);
            """
        )
        columns = {column["name"] for column in inspect(conn._conn).get_columns("notification_outbox")}
        if "payload_hash" not in columns:
            conn.execute("ALTER TABLE notification_outbox ADD COLUMN payload_hash TEXT")


def enqueue_registration(
    *,
    organization_id: str,
    clinic_id: str,
    event_key: str,
    payload: dict[str, Any],
    channels: list[str],
) -> list[dict[str, Any]]:
    init_outbox()
    now = _iso(_now())
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload_digest = request_hash(payload)
    rows: list[dict[str, Any]] = []
    with compat_connection(_ENGINE) as conn:
        existing = conn.execute(
            """
            SELECT payload_hash, payload_json
            FROM notification_outbox
            WHERE organization_id = ? AND clinic_id = ? AND event_key = ?
            LIMIT 1
            """,
            (organization_id, clinic_id, event_key),
        ).fetchone()
        if existing:
            existing_hash = existing["payload_hash"] or hashlib.sha256(
                str(existing["payload_json"]).encode("utf-8")
            ).hexdigest()
            if existing_hash != payload_digest:
                raise IdempotencyConflict(
                    "Idempotency-Key was already used with different notification data"
                )
            conn.execute(
                """
                UPDATE notification_outbox
                SET payload_hash = ?
                WHERE organization_id = ? AND clinic_id = ? AND event_key = ?
                  AND payload_hash IS NULL
                """,
                (payload_digest, organization_id, clinic_id, event_key),
            )

        for channel in channels:
            row_id = f"NTF-{uuid.uuid4().hex[:12].upper()}"
            conn.execute(
                """
                INSERT INTO notification_outbox (
                    id, organization_id, clinic_id, event_key, channel, payload_json,
                    payload_hash, status, attempts, available_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?)
                ON CONFLICT(organization_id, clinic_id, event_key, channel) DO NOTHING
                """,
                (
                    row_id,
                    organization_id,
                    clinic_id,
                    event_key,
                    channel,
                    payload_json,
                    payload_digest,
                    now,
                    now,
                    now,
                ),
            )
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, channel, status, attempts, provider_message_id, last_error
                FROM notification_outbox
                WHERE organization_id = ? AND clinic_id = ? AND event_key = ?
                ORDER BY channel ASC
                """,
                (organization_id, clinic_id, event_key),
            ).fetchall()
        ]
    return rows


def claim_batch(*, limit: int = 8, lease_seconds: int = 120) -> list[dict[str, Any]]:
    init_outbox()
    now = _now()
    now_iso = _iso(now)
    lease_iso = _iso(now + timedelta(seconds=lease_seconds))
    candidates: list[dict[str, Any]]
    with _LOCK, compat_connection(_ENGINE) as conn:
        candidates = [
            dict(row)
            for row in conn.execute(
                """
                SELECT * FROM notification_outbox
                WHERE available_at <= ?
                  AND (
                    status = 'pending'
                    OR (status = 'processing' AND locked_until IS NOT NULL AND locked_until <= ?)
                  )
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (now_iso, now_iso, limit),
            ).fetchall()
        ]
        claimed: list[dict[str, Any]] = []
        for row in candidates:
            updated = conn.execute(
                """
                UPDATE notification_outbox
                SET status = 'processing',
                    attempts = attempts + 1,
                    locked_until = ?,
                    updated_at = ?
                WHERE id = ?
                  AND (
                    status = 'pending'
                    OR (status = 'processing' AND locked_until IS NOT NULL AND locked_until <= ?)
                  )
                """,
                (lease_iso, now_iso, row["id"], now_iso),
            )
            if updated.rowcount == 1:
                row["attempts"] = int(row["attempts"]) + 1
                row["status"] = "processing"
                claimed.append(row)
        return claimed


def mark_sent(*, row_id: str, provider_message_id: str | None = None) -> None:
    now = _iso(_now())
    with compat_connection(_ENGINE) as conn:
        conn.execute(
            """
            UPDATE notification_outbox
            SET status = 'sent',
                provider_message_id = ?,
                last_error = NULL,
                locked_until = NULL,
                sent_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (provider_message_id, now, now, row_id),
        )


def mark_failed(*, row_id: str, error: str, max_attempts: int = 5) -> None:
    now = _now()
    with compat_connection(_ENGINE) as conn:
        row = conn.execute(
            "SELECT attempts FROM notification_outbox WHERE id = ?",
            (row_id,),
        ).fetchone()
        attempts = int(row["attempts"]) if row else max_attempts
        if attempts >= max_attempts:
            status = "failed"
            available_at = now
        else:
            status = "pending"
            available_at = now + timedelta(seconds=min(300, 2 ** attempts * 5))
        conn.execute(
            """
            UPDATE notification_outbox
            SET status = ?,
                available_at = ?,
                locked_until = NULL,
                last_error = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (status, _iso(available_at), error[:1000], _iso(now), row_id),
        )
