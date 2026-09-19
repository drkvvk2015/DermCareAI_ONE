from __future__ import annotations

import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from ai_registry import init_store as init_ai_store
from audit import db as audit_db
from clinical_store import init_store as init_clinical_store
from commerce_store import init_store as init_commerce_store


def main() -> None:
    if os.getenv("APP_ENV", "").lower() == "production" and not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required for production migrations.")
    init_commerce_store()
    init_clinical_store()
    init_ai_store()
    with audit_db():
        pass
    print("DermCareAI database schemas initialized.")


if __name__ == "__main__":
    main()
