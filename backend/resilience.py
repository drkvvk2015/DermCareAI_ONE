"""Reliability helpers for DermCareAI inference.

The module deliberately separates *recovery* from *model promotion*.
A failed inference may trigger a controlled model-service reload, but no
new model is promoted automatically from live traffic.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelStatus:
    name: str
    path: str
    exists: bool
    sha256: Optional[str]
    loaded: bool
    last_error: Optional[str]
    reload_count: int


def file_sha256(path: str) -> Optional[str]:
    """Return a deterministic SHA-256 digest, or None when the file is absent."""
    file_path = Path(path)
    if not file_path.is_file():
        return None
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SelfHealingModelService:
    """Thread-safe lazy loader with bounded retry/reload behaviour."""

    def __init__(self, loader: Callable[[], object], *, name: str, max_reloads: int = 2):
        self._loader = loader
        self._name = name
        self._max_reloads = max_reloads
        self._lock = Lock()
        self._instance: Optional[object] = None
        self._last_error: Optional[str] = None
        self._reload_count = 0
        self._last_load_monotonic = 0.0

    def get(self) -> object:
        if self._instance is not None:
            return self._instance
        with self._lock:
            if self._instance is None:
                self._load_locked()
        return self._instance

    def recover(self) -> bool:
        """Reload once after a runtime failure, subject to a bounded retry budget."""
        with self._lock:
            if self._reload_count >= self._max_reloads:
                return False
            self._instance = None
            self._reload_count += 1
            self._load_locked()
            return self._instance is not None

    def reset_retry_budget(self) -> None:
        with self._lock:
            self._reload_count = 0

    def status(self, path: str) -> ModelStatus:
        return ModelStatus(
            name=self._name,
            path=path,
            exists=Path(path).is_file(),
            sha256=file_sha256(path),
            loaded=self._instance is not None,
            last_error=self._last_error,
            reload_count=self._reload_count,
        )

    def _load_locked(self) -> None:
        started = time.monotonic()
        try:
            instance = self._loader()
            self._instance = instance
            self._last_error = None
            self._last_load_monotonic = started
            logger.info("Loaded model service %s", self._name)
        except Exception as exc:  # pragma: no cover - exercised through integration tests
            self._instance = None
            self._last_error = str(exc)
            logger.exception("Failed to load model service %s", self._name)
            raise


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
