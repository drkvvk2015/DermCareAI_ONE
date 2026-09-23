from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import Engine, inspect

from storage import create_store_engine, execute, require_postgres_in_production, transaction

ENGINE: Engine = create_store_engine("COMMERCE_DATABASE_URL", "COMMERCE_DB_PATH", "commerce.db")
require_postgres_in_production(ENGINE, "Commerce store")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_store() -> None:
    with ENGINE.begin() as conn:
        execute(conn, """
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                invoice_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        execute(conn, """
            CREATE TABLE IF NOT EXISTS pharmacy_stock (
                medicine_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                quantity DOUBLE PRECISION NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        execute(conn, """
            CREATE TABLE IF NOT EXISTS pharmacy_batches (
                batch_id TEXT PRIMARY KEY,
                medicine_id TEXT NOT NULL,
                expiry TEXT NOT NULL,
                quantity DOUBLE PRECISION NOT NULL,
                blocked BOOLEAN NOT NULL DEFAULT FALSE,
                organization_id TEXT,
                clinic_id TEXT,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        columns = {column["name"] for column in inspect(ENGINE).get_columns("pharmacy_batches")}
        if "organization_id" not in columns:
            execute(conn, "ALTER TABLE pharmacy_batches ADD COLUMN organization_id TEXT")
        if "clinic_id" not in columns:
            execute(conn, "ALTER TABLE pharmacy_batches ADD COLUMN clinic_id TEXT")
        execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_pharmacy_batches_tenant_fefo
            ON pharmacy_batches(organization_id, clinic_id, medicine_id, expiry, batch_id)
        """)
        execute(conn, """
            CREATE TABLE IF NOT EXISTS payment_events (
                event_id TEXT PRIMARY KEY,
                received_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
        """)


def save_invoice(invoice: Dict[str, Any]) -> None:
    init_store()
    now = _now()
    with transaction(ENGINE) as conn:
        execute(
            conn,
            """
            INSERT INTO invoices(id, patient_id, invoice_json, status, created_at, updated_at)
            VALUES (:id, :patient_id, :invoice_json, :status, :created_at, :updated_at)
            ON CONFLICT (id) DO UPDATE SET
              invoice_json = EXCLUDED.invoice_json,
              status = EXCLUDED.status,
              updated_at = EXCLUDED.updated_at
            """,
            {
                "id": invoice["id"],
                "patient_id": invoice["patient_id"],
                "invoice_json": json.dumps(invoice, sort_keys=True),
                "status": invoice["status"],
                "created_at": invoice["created_at"],
                "updated_at": now,
            },
        )


def get_invoice(invoice_id: str) -> Dict[str, Any] | None:
    init_store()
    with ENGINE.connect() as conn:
        row = execute(
            conn,
            "SELECT invoice_json FROM invoices WHERE id = :invoice_id",
            {"invoice_id": invoice_id},
        ).mappings().first()
    return json.loads(row["invoice_json"]) if row else None


def update_invoice(invoice: Dict[str, Any]) -> None:
    save_invoice(invoice)


def upsert_stock(item: Dict[str, Any]) -> Dict[str, Any]:
    init_store()
    payload = dict(item)
    medicine_id = str(payload["medicine_id"])
    quantity = float(payload.get("quantity", 0))
    updated_at = _now()
    payload["updated_at"] = updated_at
    with transaction(ENGINE) as conn:
        execute(
            conn,
            """
            INSERT INTO pharmacy_stock(medicine_id, payload_json, quantity, updated_at)
            VALUES (:medicine_id, :payload_json, :quantity, :updated_at)
            ON CONFLICT(medicine_id) DO UPDATE SET
              payload_json = EXCLUDED.payload_json,
              quantity = EXCLUDED.quantity,
              updated_at = EXCLUDED.updated_at
            """,
            {
                "medicine_id": medicine_id,
                "payload_json": json.dumps(payload, sort_keys=True),
                "quantity": quantity,
                "updated_at": updated_at,
            },
        )
    return payload


def upsert_batch(batch: Dict[str, Any], *, organization_id: str, clinic_id: str) -> Dict[str, Any]:
    """Persist a pharmacy batch for deterministic FEFO allocation."""
    init_store()
    payload = dict(batch)
    batch_id = str(payload.get("batch_id", "")).strip()
    medicine_id = str(payload.get("medicine_id", "")).strip()
    expiry = str(payload.get("expiry", "")).strip()
    quantity = float(payload.get("quantity", 0))
    blocked = bool(payload.get("blocked", False))
    if not batch_id or not medicine_id or not expiry:
        raise ValueError("batch_id, medicine_id and expiry are required")
    if quantity < 0:
        raise ValueError("batch quantity cannot be negative")
    payload.update({"batch_id": batch_id, "medicine_id": medicine_id, "expiry": expiry, "quantity": quantity, "blocked": blocked, "organization_id": organization_id, "clinic_id": clinic_id})
    now = _now()
    payload["updated_at"] = now
    with transaction(ENGINE) as conn:
        execute(conn, """
            INSERT INTO pharmacy_batches(batch_id, medicine_id, expiry, quantity, blocked, organization_id, clinic_id, payload_json, updated_at)
            VALUES (:batch_id, :medicine_id, :expiry, :quantity, :blocked, :organization_id, :clinic_id, :payload_json, :updated_at)
            ON CONFLICT(batch_id) DO UPDATE SET
              medicine_id = EXCLUDED.medicine_id,
              expiry = EXCLUDED.expiry,
              organization_id = EXCLUDED.organization_id,
              clinic_id = EXCLUDED.clinic_id,
              quantity = EXCLUDED.quantity,
              blocked = EXCLUDED.blocked,
              payload_json = EXCLUDED.payload_json,
              updated_at = EXCLUDED.updated_at
        """, {
            "batch_id": batch_id, "medicine_id": medicine_id, "expiry": expiry,
            "quantity": quantity, "blocked": blocked, "organization_id": organization_id, "clinic_id": clinic_id,
            "payload_json": json.dumps(payload, sort_keys=True), "updated_at": now,
        })
    return payload


def list_batches(medicine_id: str | None = None, *, organization_id: str, clinic_id: str) -> list[Dict[str, Any]]:
    init_store()
    with ENGINE.connect() as conn:
        if medicine_id:
            rows = execute(conn, "SELECT payload_json FROM pharmacy_batches WHERE organization_id = :organization_id AND clinic_id = :clinic_id AND medicine_id = :medicine_id ORDER BY expiry, batch_id", {"organization_id": organization_id, "clinic_id": clinic_id, "medicine_id": medicine_id}).mappings().all()
        else:
            rows = execute(conn, "SELECT payload_json FROM pharmacy_batches WHERE organization_id = :organization_id AND clinic_id = :clinic_id ORDER BY medicine_id, expiry, batch_id", {"organization_id": organization_id, "clinic_id": clinic_id}).mappings().all()
    return [json.loads(row["payload_json"]) for row in rows]


def atomic_fefo_dispense(required: Dict[str, float], *, on: str, organization_id: str, clinic_id: str) -> Dict[str, list[tuple[str, float]]]:
    """Allocate and decrement non-expired, unblocked batches inside one transaction."""
    init_store()
    with transaction(ENGINE) as conn:
        result: Dict[str, list[tuple[str, float]]] = {}
        for medicine_id, requested in required.items():
            requested = float(requested)
            if requested <= 0:
                raise ValueError(medicine_id)
            rows = execute(conn, """
                SELECT batch_id, expiry, quantity, blocked
                FROM pharmacy_batches
                WHERE organization_id = :organization_id AND clinic_id = :clinic_id AND medicine_id = :medicine_id AND quantity > 0
                  AND blocked = FALSE AND expiry >= :on
                ORDER BY expiry, batch_id
            """, {"organization_id": organization_id, "clinic_id": clinic_id, "medicine_id": medicine_id, "on": on}).mappings().all()
            remaining = requested
            allocations: list[tuple[str, float]] = []
            for row in rows:
                take = min(remaining, float(row["quantity"]))
                if take <= 0:
                    continue
                new_quantity = float(row["quantity"]) - take
                execute(conn, "UPDATE pharmacy_batches SET quantity = :quantity, updated_at = :updated_at WHERE batch_id = :batch_id AND organization_id = :organization_id AND clinic_id = :clinic_id", {"quantity": new_quantity, "updated_at": _now(), "batch_id": row["batch_id"], "organization_id": organization_id, "clinic_id": clinic_id})
                allocations.append((str(row["batch_id"]), take))
                remaining -= take
                if remaining <= 0:
                    break
            if remaining > 0:
                raise ValueError(medicine_id)
            result[medicine_id] = allocations
        return result


def list_stock() -> list[Dict[str, Any]]:
    init_store()
    with ENGINE.connect() as conn:
        rows = execute(
            conn,
            "SELECT payload_json FROM pharmacy_stock ORDER BY medicine_id",
        ).mappings().all()
    return [json.loads(row["payload_json"]) for row in rows]


def atomic_dispense(required: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    init_store()
    now = _now()
    with transaction(ENGINE) as conn:
        rows: Dict[str, Dict[str, Any]] = {}
        for medicine_id in required:
            row = execute(
                conn,
                "SELECT medicine_id, payload_json, quantity FROM pharmacy_stock WHERE medicine_id = :medicine_id",
                {"medicine_id": medicine_id},
            ).mappings().first()
            if row is None:
                raise KeyError(medicine_id)
            rows[medicine_id] = dict(row)

        for medicine_id, requested_qty in required.items():
            if float(rows[medicine_id]["quantity"]) < float(requested_qty):
                raise ValueError(medicine_id)

        updated: Dict[str, Dict[str, Any]] = {}
        for medicine_id, requested_qty in required.items():
            new_qty = float(rows[medicine_id]["quantity"]) - float(requested_qty)
            payload = json.loads(rows[medicine_id]["payload_json"])
            payload["quantity"] = new_qty
            payload["updated_at"] = now
            execute(
                conn,
                """
                UPDATE pharmacy_stock
                SET payload_json = :payload_json, quantity = :quantity, updated_at = :updated_at
                WHERE medicine_id = :medicine_id
                """,
                {
                    "payload_json": json.dumps(payload, sort_keys=True),
                    "quantity": new_qty,
                    "updated_at": now,
                    "medicine_id": medicine_id,
                },
            )
            updated[medicine_id] = payload
        return updated


def record_payment_event(event_id: str, payload: Dict[str, Any]) -> bool:
    init_store()
    now = _now()
    try:
        with transaction(ENGINE) as conn:
            execute(
                conn,
                """
                INSERT INTO payment_events(event_id, received_at, payload_json)
                VALUES (:event_id, :received_at, :payload_json)
                """,
                {
                    "event_id": event_id,
                    "received_at": now,
                    "payload_json": json.dumps(payload, sort_keys=True),
                },
            )
        return True
    except Exception as exc:
        message = str(exc).lower()
        if "unique" in message or "duplicate" in message:
            return False
        raise


def reset_store() -> None:
    init_store()
    with transaction(ENGINE) as conn:
        execute(conn, "DELETE FROM invoices")
        execute(conn, "DELETE FROM pharmacy_stock")
        execute(conn, "DELETE FROM payment_events")
