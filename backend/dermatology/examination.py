from __future__ import annotations

from dataclasses import dataclass
from typing import Final

PRIMARY_MORPHOLOGIES: Final[tuple[str, ...]] = (
    "macule", "patch", "papule", "plaque", "nodule", "vesicle",
    "bulla", "pustule", "wheal", "tumor", "ulcer",
)

SECONDARY_CHANGES: Final[tuple[str, ...]] = (
    "scale", "crust", "erosion", "fissure", "excoriation",
    "atrophy", "scar", "lichenification",
)

@dataclass(frozen=True)
class DermatologyExamination:
    primary_morphology: str
    secondary_changes: tuple[str, ...] = ()
    color: str = ""
    border: str = ""
    surface: str = ""
    distribution: str = ""
    dermoscopy: str = ""
    systemic_red_flags: tuple[str, ...] = ()

def validate_examination(exam: DermatologyExamination) -> None:
    if exam.primary_morphology not in PRIMARY_MORPHOLOGIES:
        raise ValueError(f"Unsupported primary morphology: {exam.primary_morphology}")
    invalid_secondary = [item for item in exam.secondary_changes if item not in SECONDARY_CHANGES]
    if invalid_secondary:
        raise ValueError(f"Unsupported secondary changes: {', '.join(invalid_secondary)}")
    if not exam.distribution.strip():
        raise ValueError("distribution is required")

def as_dict(exam: DermatologyExamination) -> dict[str, object]:
    validate_examination(exam)
    return {
        "primary_morphology": exam.primary_morphology,
        "secondary_changes": list(exam.secondary_changes),
        "color": exam.color.strip(),
        "border": exam.border.strip(),
        "surface": exam.surface.strip(),
        "distribution": exam.distribution.strip(),
        "dermoscopy": exam.dermoscopy.strip(),
        "systemic_red_flags": list(exam.systemic_red_flags),
    }
