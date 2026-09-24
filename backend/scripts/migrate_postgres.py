from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from ai_registry import init_store as init_ai_store
from audit import db as audit_db
from clinical_store import init_store as init_clinical_store
from commerce_store import init_store as init_commerce_store

MIGRATION_VERSION = "2026-09-24-hardening-1"


def main() -> None:
    if os.getenv("APP_ENV", "").lower() == "production" and not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required for production migrations.")

    init_commerce_store()
    init_clinical_store()
    init_ai_store()
    with audit_db():
        pass

    database_url = os.getenv("CLINICAL_DATABASE_URL") or os.getenv("DATABASE_URL")
    if database_url:
        engine = create_engine(database_url)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "INSERT INTO schema_migrations(version, applied_at) "
                    "VALUES (:version, :applied_at) "
                    "ON CONFLICT(version) DO NOTHING"
                ),
                {
                    "version": MIGRATION_VERSION,
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        engine.dispose()

    print(f"DermCareAI database schemas initialized ({MIGRATION_VERSION}).")


if __name__ == "__main__":
    main()
