from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/audit", tags=["audit"])
DB_PATH = os.getenv("AUDIT_DB_PATH", "audit.db")


class AuditEvent(BaseModel):
    actor_id: str = Field(min_length=1, max_length=200)
    actor_role: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=200)
    resource_type: str = Field(min_length=1, max_length=100)
    resource_id: str = Field(min_length=1, max_length=200)
    metadata: Dict[str, Any] = {}
    correlation_id: str | None = None


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, actor_id TEXT NOT NULL, actor_role TEXT NOT NULL, action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, metadata_json TEXT NOT NULL, correlation_id TEXT, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL)")
    return conn


def record_event(event: AuditEvent) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        previous = conn.execute("SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
        previous_hash = previous[0] if previous else "GENESIS"
        canonical = {"timestamp": timestamp, **event.model_dump(), "previous_hash": previous_hash}
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        cursor = conn.execute("INSERT INTO audit_events(timestamp,actor_id,actor_role,action,resource_type,resource_id,metadata_json,correlation_id,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?,?)", (timestamp, event.actor_id, event.actor_role, event.action, event.resource_type, event.resource_id, json.dumps(event.metadata, sort_keys=True), event.correlation_id, previous_hash, digest))
        event_id = cursor.lastrowid
    return {"id": f"AUD-{event_id:09d}", **canonical, "event_hash": digest}


@router.post("/events")
def create_audit_event(event: AuditEvent):
    return record_event(event)


@router.get("/events")
def list_audit_events(limit: int = 100):
    with db() as conn:
        rows = conn.execute("SELECT id,timestamp,actor_id,actor_role,action,resource_type,resource_id,metadata_json,correlation_id,previous_hash,event_hash FROM audit_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
    return [{"id": f"AUD-{row[0]:09d}", "timestamp": row[1], "actor_id": row[2], "actor_role": row[3], "action": row[4], "resource_type": row[5], "resource_id": row[6], "metadata": json.loads(row[7]), "correlation_id": row[8], "previous_hash": row[9], "event_hash": row[10]} for row in rows]
