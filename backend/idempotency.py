from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from sqlalchemy import Engine

from storage import create_store_engine, execute, transaction


_ENGINE_CONFIG = {
    "clinical": ("CLINICAL_DATABASE_URL", "CLINICAL_DB_PATH", "clinical-idempotency.db"),
    "commerce": ("COMMERCE_DATABASE_URL", "COMMERCE_DB_PATH", "commerce-idempotency.db"),
}
_ENGINES: dict[str, Engine] = {}
_LOCK = Lock()


class IdempotencyConflict(ValueError):
    pass


class IdempotencyInProgress(ValueError):
    pass


def _engine(scope: str) -> Engine:
    if scope not in _ENGINE_CONFIG:
        raise ValueError(f"Unsupported idempotency scope: {scope}")
    with _LOCK:
        engine = _ENGINES.get(scope)
        if engine is None:
            url_env, path_env, default_path = _ENGINE_CONFIG[scope]
            engine = create_store_engine(url_env, path_env, default_path)
            _ENGINES[scope] = engine
        return engine


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _init(scope: str) -> None:
    with _engine(scope).begin() as conn:
        execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS idempotency_operations (
                scope TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                clinic_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                operation_key TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                response_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(scope, organization_id, clinic_id, actor_id, operation_key)
            )
            """,
        )
        execute(
            conn,
            """CREATE INDEX IF NOT EXISTS idx_idempotency_updated
               ON idempotency_operations(scope, updated_at)""",
        )


def request_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def begin_operation(
    *,
    scope: str,
    organization_id: str,
    clinic_id: str,
    actor_id: str,
    operation_key: str,
    payload: Any,
    lease_seconds: int = 300,
) -> dict[str, Any] | None:
    """Return a cached response, or claim a new operation.

    None means this caller owns first execution. A completed operation returns its
    stored response. A conflicting key or active concurrent execution raises 409-worthy
    exceptions.
    """
    operation_key = operation_key.strip()
    if len(operation_key) < 8 or len(operation_key) > 200:
        raise ValueError("Idempotency-Key must be between 8 and 200 characters")
    _init(scope)
    digest = request_hash(payload)
    now = datetime.now(timezone.utc)

    with transaction(_engine(scope)) as conn:
        row = execute(
            conn,
            """SELECT * FROM idempotency_operations
               WHERE scope = :scope
                 AND organization_id = :organization_id
                 AND clinic_id = :clinic_id
                 AND actor_id = :actor_id
                 AND operation_key = :operation_key""",
            {
                "scope": scope,
                "organization_id": organization_id,
                "clinic_id": clinic_id,
                "actor_id": actor_id,
                "operation_key": operation_key,
            },
        ).mappings().first()

        if row:
            if row["request_hash"] != digest:
                raise IdempotencyConflict("Idempotency-Key was already used with a different request")
            if row["status"] == "completed":
                return json.loads(row["response_json"] or "null")
            try:
                updated_at = datetime.fromisoformat(str(row["updated_at"]))
                age = (now - updated_at).total_seconds()
            except ValueError:
                age = lease_seconds + 1
            if age < lease_seconds:
                raise IdempotencyInProgress("The same idempotent operation is already processing")
            updated = execute(
                conn,
                """UPDATE idempotency_operations
                   SET status = 'processing', updated_at = :updated_at
                   WHERE scope = :scope
                     AND organization_id = :organization_id
                     AND clinic_id = :clinic_id
                     AND actor_id = :actor_id
                     AND operation_key = :operation_key
                     AND status = 'processing'""",
                {
                    "updated_at": now.isoformat(),
                    "scope": scope,
                    "organization_id": organization_id,
                    "clinic_id": clinic_id,
                    "actor_id": actor_id,
                    "operation_key": operation_key,
                },
            )
            if updated.rowcount != 1:
                raise IdempotencyInProgress("The same idempotent operation is already processing")
            return None

        try:
            execute(
                conn,
                """INSERT INTO idempotency_operations(
                 scope, organization_id, clinic_id, actor_id, operation_key,
                 request_hash, status, created_at, updated_at
               )
               VALUES(
                 :scope, :organization_id, :clinic_id, :actor_id, :operation_key,
                 :request_hash, 'processing', :created_at, :updated_at
               )""",
            {
                "scope": scope,
                "organization_id": organization_id,
                "clinic_id": clinic_id,
                "actor_id": actor_id,
                "operation_key": operation_key,
                "request_hash": digest,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                },
            )
        except Exception as exc:
            message = str(exc).lower()
            if "unique" in message or "duplicate" in message:
                raise IdempotencyInProgress("The same idempotent operation is already processing") from exc
            raise
    return None


def complete_operation(
    *,
    scope: str,
    organization_id: str,
    clinic_id: str,
    actor_id: str,
    operation_key: str,
    response: Any,
) -> None:
    _init(scope)
    now = _now()
    with transaction(_engine(scope)) as conn:
        updated = execute(
            conn,
            """UPDATE idempotency_operations
               SET status = 'completed',
                   response_json = :response_json,
                   updated_at = :updated_at
               WHERE scope = :scope
                 AND organization_id = :organization_id
                 AND clinic_id = :clinic_id
                 AND actor_id = :actor_id
                 AND operation_key = :operation_key
                 AND status = 'processing'""",
            {
                "response_json": json.dumps(response, sort_keys=True, default=str),
                "updated_at": now,
                "scope": scope,
                "organization_id": organization_id,
                "clinic_id": clinic_id,
                "actor_id": actor_id,
                "operation_key": operation_key,
            },
        )
        if updated.rowcount != 1:
            raise ValueError("Idempotency operation was not claimed by this actor")
