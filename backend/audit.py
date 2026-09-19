from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends
from contextlib import contextmanager
from sqlalchemy import Engine

from storage import compat_connection, create_store_engine, require_postgres_in_production
from pydantic import BaseModel, Field

from auth import require_roles

router = APIRouter(prefix="/audit", tags=["audit"])
ENGINE: Engine = create_store_engine("AUDIT_DATABASE_URL", "AUDIT_DB_PATH", "audit.db")
require_postgres_in_production(ENGINE, "Audit store")


class AuditEvent(BaseModel):
    action: str = Field(min_length=1, max_length=200)
    resource_type: str = Field(min_length=1, max_length=100)
    resource_id: str = Field(min_length=1, max_length=200)
    metadata: Dict[str, Any] = {}
    correlation_id: str | None = None


@contextmanager
def db():
    with compat_connection(ENGINE) as conn:
        id_type = "BIGSERIAL PRIMARY KEY" if ENGINE.url.get_backend_name() == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS audit_events (id {id_type}, timestamp TEXT NOT NULL, actor_id TEXT NOT NULL, actor_role TEXT NOT NULL, action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, metadata_json TEXT NOT NULL, correlation_id TEXT, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL)"
        )
        yield conn


def record_event(event: AuditEvent, user: dict[str, Any]) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    roles = sorted(str(role) for role in user.get("roles", set()))
    actor_id = str(user["uid"])
    actor_role = roles[0] if roles else "staff"
    with db() as conn:
        previous = conn.execute("SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
        previous_hash = previous["event_hash"] if previous else "GENESIS"
        canonical = {
            "timestamp": timestamp,
            "actor_id": actor_id,
            "actor_role": actor_role,
            **event.model_dump(),
            "previous_hash": previous_hash,
        }
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        result = conn.execute(
            """
            INSERT INTO audit_events(
              timestamp,actor_id,actor_role,action,resource_type,resource_id,
              metadata_json,correlation_id,previous_hash,event_hash
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            RETURNING id
            """,
            (
                timestamp, actor_id, actor_role, event.action, event.resource_type,
                event.resource_id, json.dumps(event.metadata, sort_keys=True),
                event.correlation_id, previous_hash, digest,
            ),
        )
        event_id = result.fetchone()["id"]
    return {"id": f"AUD-{event_id:09d}", **canonical, "event_hash": digest}


@router.post("/events")
def create_audit_event(event: AuditEvent, user: dict[str, Any] = Depends(require_roles("admin", "auditor"))):
    return record_event(event, user)


@router.get("/events")
def list_audit_events(limit: int = 100, user: dict[str, Any] = Depends(require_roles("admin", "auditor"))):
    with db() as conn:
        rows = conn.execute("SELECT id,timestamp,actor_id,actor_role,action,resource_type,resource_id,metadata_json,correlation_id,previous_hash,event_hash FROM audit_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
    return [
        {
            "id": f"AUD-{row['id']:09d}",
            "timestamp": row["timestamp"],
            "actor_id": row["actor_id"],
            "actor_role": row["actor_role"],
            "action": row["action"],
            "resource_type": row["resource_type"],
            "resource_id": row["resource_id"],
            "metadata": json.loads(row["metadata_json"]),
            "correlation_id": row["correlation_id"],
            "previous_hash": row["previous_hash"],
            "event_hash": row["event_hash"],
        }
        for row in rows
    ]
