from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict

MODEL_REGISTRY_PATH = Path(os.getenv("MODEL_REGISTRY_PATH", "models/registry.json"))

DEFAULT_REGISTRY: Dict[str, Any] = {
    "schema_version": 1,
    "models": {
        "melanoma_binary": {
            "file": "melanoma_classifier.pth",
            "format": "pytorch",
            "purpose": "melanoma risk screening signal",
            "source": "existing DermCareAI research model",
            "validated": False,
            "sha256": "",
        },
        "skin_lesion_7class": {
            "file": "FinetunedNasNetMobile.keras",
            "format": "keras",
            "purpose": "7-class lesion classification research model",
            "source": "existing DermCareAI research model",
            "validated": False,
            "sha256": "",
        },
        "embedded_ham10000": {
            "repository": "PREMAADC/vit-base-ham10000",
            "format": "transformers",
            "purpose": "7-class dermoscopic lesion classification fallback",
            "validated": False,
            "research_only": True,
            "license": "apache-2.0",
        },
    },
}


def load_registry() -> Dict[str, Any]:
    if not MODEL_REGISTRY_PATH.exists():
        return DEFAULT_REGISTRY
    return json.loads(MODEL_REGISTRY_PATH.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_models(model_dir: str = "models") -> Dict[str, Any]:
    registry = load_registry()
    root = Path(model_dir)
    results: Dict[str, Any] = {}
    for key, spec in registry.get("models", {}).items():
        # Repository-backed models are metadata-only entries until their
        # local cache is explicitly materialized and checksum-pinned.
        if not spec.get("file"):
            results[key] = {
                "repository": spec.get("repository"),
                "exists": False,
                "sha256": None,
                "hash_matches": False,
                "validated": bool(spec.get("validated", False)),
                "research_only": bool(spec.get("research_only", False)),
                "purpose": spec.get("purpose"),
                "materialized": False,
            }
            continue

        path = root / spec["file"]
        exists = path.is_file()
        actual = sha256(path) if exists else None
        expected = (spec.get("sha256") or "").lower()
        results[key] = {
            "file": str(path),
            "exists": exists,
            "sha256": actual,
            "hash_matches": bool(exists and expected and actual == expected),
            "validated": bool(spec.get("validated", False)),
            "purpose": spec.get("purpose"),
            "materialized": exists,
        }
    return results
