from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum


_IMMUTABLE_REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$", re.IGNORECASE)


class DiagnosticMode(str, Enum):
    """Clinical AI diagnostic execution is intentionally unavailable."""

    DISABLED = "disabled"


@dataclass(frozen=True)
class ClinicalAICapabilities:
    clinical_assist_enabled: bool
    generative_assist_enabled: bool
    diagnostic_mode: DiagnosticMode


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default).lower()).strip().lower() == "true"


def is_immutable_model_revision(value: str | None) -> bool:
    return bool(value and _IMMUTABLE_REVISION_RE.fullmatch(value.strip()))


def capabilities() -> ClinicalAICapabilities:
    clinical_assist = _bool("ENABLE_CLINICAL_ASSIST_AI", False)
    generative_requested = _bool("ENABLE_GENERATIVE_CLINICAL_ASSIST", False) and _bool("ENABLE_MEDGEMMA", False)
    revision_pinned = is_immutable_model_revision(os.getenv("MEDGEMMA_REVISION"))
    if os.getenv("APP_ENV", "development").lower() == "production":
        generative_assist = clinical_assist and generative_requested and revision_pinned
    else:
        generative_assist = clinical_assist and generative_requested

    return ClinicalAICapabilities(
        clinical_assist_enabled=clinical_assist,
        generative_assist_enabled=generative_assist,
        diagnostic_mode=DiagnosticMode.DISABLED,
    )


def require_clinical_assist_enabled() -> ClinicalAICapabilities:
    state = capabilities()
    if not state.clinical_assist_enabled:
        raise RuntimeError("Clinical assist AI is disabled by production configuration")
    return state


def diagnostic_clinical_activation_allowed() -> bool:
    return False
