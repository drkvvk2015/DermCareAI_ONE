"""Pytest bootstrap for isolated local SQLite state.

CI jobs that provide DATABASE_URL values keep their explicit database backend.
Local runs without explicit database URLs receive fresh per-session SQLite
paths before test modules import their storage engines, preventing stale local
database files from affecting results.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TEMP_ROOT: tempfile.TemporaryDirectory[str] | None = None


def pytest_configure(config) -> None:
    del config
    global _TEMP_ROOT
    if _TEMP_ROOT is not None:
        return

    database_bindings = (
        ("CLINICAL_DATABASE_URL", "CLINICAL_DB_PATH", "clinical.db"),
        ("AUDIT_DATABASE_URL", "AUDIT_DB_PATH", "audit.db"),
        ("COMMERCE_DATABASE_URL", "COMMERCE_DB_PATH", "commerce.db"),
    )
    if any(os.getenv(url_var) for url_var, _, _ in database_bindings):
        return

    _TEMP_ROOT = tempfile.TemporaryDirectory(prefix="dermcareai-pytest-")
    root = Path(_TEMP_ROOT.name)
    for _, path_var, filename in database_bindings:
        os.environ.setdefault(path_var, str(root / filename))


def pytest_unconfigure(config) -> None:
    del config
    global _TEMP_ROOT
    if _TEMP_ROOT is not None:
        _TEMP_ROOT.cleanup()
        _TEMP_ROOT = None
