"""Guideline lookup adapted from drkvvk2015/AI_mEDICal_guidelines (MIT).

Only deterministic, read-only retrieval of clinician-approved guideline entries is
retained. The upstream LLM, autonomous-update, feedback-learning, federated-sync and
simulation paths are intentionally not vendored.
"""
from medguide_ai.core import (
    EvidenceItem,
    EvidenceStrength,
    GuidelineStore,
    PatientContext,
    Recommendation,
    TrustedSource,
    EvidenceVersion,
    load_guideline_dir,
)

__all__ = [
    "EvidenceItem",
    "EvidenceStrength",
    "EvidenceVersion",
    "GuidelineStore",
    "PatientContext",
    "Recommendation",
    "TrustedSource",
    "load_guideline_dir",
]
