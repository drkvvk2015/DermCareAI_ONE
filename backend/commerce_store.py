from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator

DB_PATH = Path(os.getenv("COMMERCE_DB_PATH", "commerce.db"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_store() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                invoice_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pharmacy_stock (
                medicine_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                quantity REAL NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS payment_events (
                event_id TEXT PRIMARY KEY,
                received_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_invoice(invoice: Dict[str, Any]) -> None:
    init_store()
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO invoices
            (id, patient_id, invoice_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                invoice["id"],
                invoice["patient_id"],
                json.dumps(invoice, sort_keys=True),
                invoice["status"],
                invoice["created_at"],
                now,
            ),
        )


def get_invoice(invoice_id: str) -> Dict[str, Any] | None:
    init_store()
    with _connect() as conn:
        row = conn.execute(
            "SELECT invoice_json FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
    return json.loads(row["invoice_json"]) if row else None


def update_invoice(invoice: Dict[str, Any]) -> None:
    save_invoice(invoice)


def upsert_stock(item: Dict[str, Any]) -> Dict[str, Any]:
    init_store()
    payload = dict(item)
    medicine_id = str(payload["medicine_id"])
    quantity = float(payload.get("quantity", 0))
    updated_at = datetime.now(timezone.utc).isoformat()
    payload["updated_at"] = updated_at
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO pharmacy_stock(medicine_id, payload_json, quantity, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(medicine_id) DO UPDATE SET
              payload_json=excluded.payload_json,
              quantity=excluded.quantity,
              updated_at=excluded.updated_at
            """,
            (medicine_id, json.dumps(payload, sort_keys=True), quantity, updated_at),
        )
    return payload


def list_stock() -> list[Dict[str, Any]]:
    init_store()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT payload_json FROM pharmacy_stock ORDER BY medicine_id"
        ).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def atomic_dispense(required: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    init_store()
    now = datetime.now(timezone.utc).isoformat()
    with transaction() as conn:
        rows: Dict[str, sqlite3.Row] = {}
        for medicine_id in required:
            row = conn.execute(
                "SELECT medicine_id, payload_json, quantity FROM pharmacy_stock WHERE medicine_id = ?",
                (medicine_id,),
            ).fetchone()
            if row is None:
                raise KeyError(medicine_id)
            rows[medicine_id] = row

        for medicine_id, requested_qty in required.items():
            if float(rows[medicine_id]["quantity"]) < float(requested_qty):
                raise ValueError(medicine_id)

        updated: Dict[str, Dict[str, Any]] = {}
        for medicine_id, requested_qty in required.items():
            new_qty = float(rows[medicine_id]["quantity"]) - float(requested_qty)
            payload = json.loads(rows[medicine_id]["payload_json"])
            payload["quantity"] = new_qty
            payload["updated_at"] = now
            conn.execute(
                "UPDATE pharmacy_stock SET payload_json = ?, quantity = ?, updated_at = ? WHERE medicine_id = ?",
                (json.dumps(payload, sort_keys=True), new_qty, now, medicine_id),
            )
            updated[medicine_id] = payload

        return updated


def record_payment_event(event_id: str, payload: Dict[str, Any]) -> bool:
    init_store()
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO payment_events(event_id, received_at, payload_json) VALUES (?, ?, ?)",
                (event_id, now, json.dumps(payload, sort_keys=True)),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def reset_store() -> None:
    init_store()
    with _connect() as conn:
        conn.execute("DELETE FROM invoices")
        conn.execute("DELETE FROM pharmacy_stock")
        conn.execute("DELETE FROM payment_events")
