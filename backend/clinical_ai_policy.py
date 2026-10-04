from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class DiagnosticMode(str, Enum):
    DISABLED = "disabled"
    SHADOW = "shadow"
    CLINICAL = "clinical"


@dataclass(frozen=True)
class ClinicalAICapabilities:
    clinical_assist_enabled: bool
    generative_assist_enabled: bool
    diagnostic_mode: DiagnosticMode


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default).lower()).strip().lower() == "true"


def capabilities() -> ClinicalAICapabilities:
    raw_mode = os.getenv("AI_DIAGNOSTIC_MODE", "disabled").strip().lower()
    try:
        mode = DiagnosticMode(raw_mode)
    except ValueError:
        mode = DiagnosticMode.DISABLED

    clinical_assist = _bool("ENABLE_CLINICAL_ASSIST_AI", False)
    generative_requested = _bool("ENABLE_GENERATIVE_CLINICAL_ASSIST", False) and _bool("ENABLE_MEDGEMMA", False)
    revision_pinned = bool(os.getenv("MEDGEMMA_REVISION", "").strip())
    if os.getenv("APP_ENV", "development").lower() == "production":
        generative_assist = clinical_assist and generative_requested and revision_pinned
    else:
        generative_assist = clinical_assist and generative_requested

    return ClinicalAICapabilities(
        clinical_assist_enabled=clinical_assist,
        generative_assist_enabled=generative_assist,
        diagnostic_mode=mode,
    )


def require_clinical_assist_enabled() -> ClinicalAICapabilities:
    state = capabilities()
    if not state.clinical_assist_enabled:
        raise RuntimeError("Clinical assist AI is disabled by production configuration")
    return state


def diagnostic_clinical_activation_allowed() -> bool:
    return capabilities().diagnostic_mode is DiagnosticMode.CLINICAL
