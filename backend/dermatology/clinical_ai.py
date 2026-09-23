from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Mapping


@dataclass(frozen=True)
class ClinicalFeatures:
    """Normalized findings used by deterministic clinical decision support.

    Scores are heuristic evidence scores, not probabilities.
    """

    primary_morphology: str
    secondary_changes: tuple[str, ...] = ()
    color: str = ""
    border: str = ""
    surface: str = ""
    distribution: str = ""
    symptoms: tuple[str, ...] = ()
    duration_days: int | None = None
    fever: bool = False
    pain: bool = False
    pruritus: bool = False
    systemic_red_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceItem:
    feature: str
    contribution: int
    rationale: str


@dataclass(frozen=True)
class DifferentialCandidate:
    label: str
    score: int
    evidence: tuple[EvidenceItem, ...]
    missing_information: tuple[str, ...]

    @property
    def normalized_score(self) -> float:
        return min(self.score / 10.0, 1.0)


@dataclass(frozen=True)
class SafetyAssessment:
    urgent_review: bool
    reason: str | None
    matched_flags: tuple[str, ...]


@dataclass(frozen=True)
class DifferentialResponse:
    candidates: tuple[DifferentialCandidate, ...]
    safety: SafetyAssessment
    abstained: bool
    disclaimer: str = (
        "Clinical decision support only; this is not a diagnosis or calibrated "
        "probability. A qualified clinician must review the findings."
    )


_MIN_SCORE_FOR_OUTPUT: Final[int] = 3
_MAX_CANDIDATES: Final[int] = 5

_RED_FLAG_RULES: Final[Mapping[str, tuple[str, ...]]] = {
    "possible severe cutaneous adverse reaction": (
        "mucosal erosion",
        "mucosal erosions",
        "skin pain",
        "targetoid lesions",
        "target lesions",
        "blistering",
        "rapidly progressive",
        "epidermal detachment",
    ),
    "possible necrotizing soft tissue infection": (
        "pain out of proportion",
        "rapidly progressive",
        "necrosis",
        "dusky skin",
        "crepitus",
        "systemic toxicity",
    ),
}


def _normalized_text(*values: str) -> str:
    return " ".join(value.strip().lower() for value in values if value.strip())


def assess_safety(features: ClinicalFeatures) -> SafetyAssessment:
    text = _normalized_text(
        features.color,
        features.border,
        features.surface,
        features.distribution,
        *features.systemic_red_flags,
        *features.symptoms,
    )

    matched: list[str] = []
    reasons: list[str] = []

    for syndrome, flags in _RED_FLAG_RULES.items():
        hits = [flag for flag in flags if flag in text]
        if hits:
            matched.extend(hits)
            reasons.append(syndrome)

    if features.fever and features.pain and "rapidly progressive" in text:
        matched.extend(["fever", "pain", "rapidly progressive"])
        reasons.append("possible serious skin/soft-tissue infection")

    if not matched:
        return SafetyAssessment(False, None, ())

    unique_hits = tuple(dict.fromkeys(matched))
    unique_reasons = tuple(dict.fromkeys(reasons))
    return SafetyAssessment(
        urgent_review=True,
        reason=(
            "Urgent clinical assessment is recommended because the documented "
            f"features include patterns compatible with {', '.join(unique_reasons)}."
        ),
        matched_flags=unique_hits,
    )


def _candidate(
    label: str,
    score: int,
    evidence: list[EvidenceItem],
    missing_information: list[str],
) -> DifferentialCandidate:
    return DifferentialCandidate(
        label=label,
        score=max(score, 0),
        evidence=tuple(evidence),
        missing_information=tuple(missing_information),
    )


def generate_differential(features: ClinicalFeatures) -> DifferentialResponse:
    """Generate a small, deterministic differential from structured findings."""
    morphology = features.primary_morphology.strip().lower()
    secondary = {item.strip().lower() for item in features.secondary_changes}
    distribution = features.distribution.strip().lower()
    symptoms = {item.strip().lower() for item in features.symptoms}
    color = features.color.strip().lower()
    border = features.border.strip().lower()
    surface = features.surface.strip().lower()

    candidates: list[DifferentialCandidate] = []

    psoriasis_evidence: list[EvidenceItem] = []
    psoriasis_score = 0
    if morphology == "plaque":
        psoriasis_score += 3
        psoriasis_evidence.append(EvidenceItem("plaque", 3, "Plaque morphology is compatible with psoriasis."))
    if "scale" in secondary or "scaly" in surface:
        psoriasis_score += 3
        psoriasis_evidence.append(EvidenceItem("scale", 3, "Scale is a supportive feature."))
    if "extensor" in distribution:
        psoriasis_score += 3
        psoriasis_evidence.append(EvidenceItem("extensor distribution", 3, "Extensor distribution is supportive."))
    if "silvery" in color or "silvery" in surface:
        psoriasis_score += 2
        psoriasis_evidence.append(EvidenceItem("silvery scale", 2, "Silvery scale is supportive."))
    if features.pruritus or {"itch", "pruritus"} & symptoms:
        psoriasis_score += 1
        psoriasis_evidence.append(EvidenceItem("pruritus", 1, "Pruritus can occur in psoriasis."))
    candidates.append(
        _candidate(
            "Possible psoriasis",
            psoriasis_score,
            psoriasis_evidence,
            ["nail examination", "scalp involvement", "family history"],
        )
    )

    eczema_evidence: list[EvidenceItem] = []
    eczema_score = 0
    if morphology in {"patch", "plaque"}:
        eczema_score += 2
        eczema_evidence.append(EvidenceItem("patch/plaque", 2, "Patch or plaque morphology is compatible."))
    if "flexural" in distribution:
        eczema_score += 3
        eczema_evidence.append(EvidenceItem("flexural distribution", 3, "Flexural involvement supports an eczematous pattern."))
    if features.pruritus or {"itch", "pruritus"} & symptoms:
        eczema_score += 3
        eczema_evidence.append(EvidenceItem("pruritus", 3, "Pruritus is a common supportive feature."))
    if "lichenification" in secondary or "xerosis" in surface:
        eczema_score += 2
        eczema_evidence.append(EvidenceItem("chronic eczematous change", 2, "Lichenification/xerosis supports eczema."))
    candidates.append(
        _candidate(
            "Possible eczematous dermatitis",
            eczema_score,
            eczema_evidence,
            ["atopic history", "contact exposures", "secondary infection assessment"],
        )
    )

    tinea_evidence: list[EvidenceItem] = []
    tinea_score = 0
    if morphology in {"patch", "plaque"}:
        tinea_score += 2
        tinea_evidence.append(EvidenceItem("patch/plaque", 2, "Patch/plaque morphology can be seen in tinea corporis."))
    if "annular" in border or "ring" in border:
        tinea_score += 4
        tinea_evidence.append(EvidenceItem("annular border", 4, "Annular expansion is supportive of tinea corporis."))
    if "scale" in secondary or "scaly" in surface:
        tinea_score += 2
        tinea_evidence.append(EvidenceItem("scale", 2, "Scale is supportive."))
    if features.pruritus or {"itch", "pruritus"} & symptoms:
        tinea_score += 1
        tinea_evidence.append(EvidenceItem("pruritus", 1, "Pruritus may accompany tinea."))
    candidates.append(
        _candidate(
            "Possible tinea corporis",
            tinea_score,
            tinea_evidence,
            ["exposure history", "KOH microscopy when clinically indicated"],
        )
    )

    urticaria_evidence: list[EvidenceItem] = []
    urticaria_score = 0
    if morphology == "wheal":
        urticaria_score += 6
        urticaria_evidence.append(EvidenceItem("wheal", 6, "Wheal morphology is strongly supportive."))
    if features.pruritus or {"itch", "pruritus"} & symptoms:
        urticaria_score += 2
        urticaria_evidence.append(EvidenceItem("pruritus", 2, "Pruritus is common in urticaria."))
    if features.duration_days is not None and features.duration_days <= 1:
        urticaria_score += 2
        urticaria_evidence.append(EvidenceItem("very short duration", 2, "Transient episodes support an urticarial pattern."))
    candidates.append(
        _candidate(
            "Possible urticaria",
            urticaria_score,
            urticaria_evidence,
            ["individual lesion duration", "angioedema symptoms", "trigger review"],
        )
    )

    cellulitis_evidence: list[EvidenceItem] = []
    cellulitis_score = 0
    if morphology in {"patch", "plaque"}:
        cellulitis_score += 2
        cellulitis_evidence.append(EvidenceItem("patch/plaque", 2, "Diffuse plaque/patch can occur in cellulitis."))
    if features.pain:
        cellulitis_score += 2
        cellulitis_evidence.append(EvidenceItem("pain", 2, "Pain supports an infectious/inflammatory process."))
    if features.fever:
        cellulitis_score += 3
        cellulitis_evidence.append(EvidenceItem("fever", 3, "Fever supports systemic infection."))
    if "lower limb" in distribution or "leg" in distribution:
        cellulitis_score += 1
        cellulitis_evidence.append(EvidenceItem("lower-limb distribution", 1, "Lower-limb involvement is common in cellulitis."))
    candidates.append(
        _candidate(
            "Possible cellulitis",
            cellulitis_score,
            cellulitis_evidence,
            ["warmth", "portal of entry", "systemic observations"],
        )
    )

    ranked = tuple(
        candidate
        for candidate in sorted(
            candidates,
            key=lambda item: (item.score, len(item.evidence), item.label),
            reverse=True,
        )
        if candidate.score >= _MIN_SCORE_FOR_OUTPUT
    )[:_MAX_CANDIDATES]

    safety = assess_safety(features)
    return DifferentialResponse(
        candidates=() if safety.urgent_review else ranked,
        safety=safety,
        abstained=safety.urgent_review or not ranked,
    )
