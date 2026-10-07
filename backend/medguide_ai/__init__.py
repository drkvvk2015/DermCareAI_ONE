"""Guideline lookup adapted from drkvvk2015/AI_mEDICal_guidelines (MIT).

Only deterministic, read-only retrieval of clinician-approved guideline entries is
retained. The upstream LLM, autonomous-update, feedback-learning, federated-sync and
simulation paths are intentionally not vendored.
"""
from medguide_ai.core import (
    EvidenceItem,
    EvidenceStrength,
    GuidelineSource,
    GuidelineStore,
    PatientContext,
    Recommendation,
    SUPPORTED_SOURCES,
    TrustedSource,
    EvidenceVersion,
    load_guideline_dir,
)

__all__ = [
    "EvidenceItem",
    "EvidenceStrength",
    "EvidenceVersion",
    "GuidelineSource",
    "GuidelineStore",
    "PatientContext",
    "Recommendation",
    "SUPPORTED_SOURCES",
    "TrustedSource",
    "load_guideline_dir",
]
