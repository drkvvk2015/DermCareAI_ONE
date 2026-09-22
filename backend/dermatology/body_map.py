from __future__ import annotations

from dataclasses import dataclass
from typing import Final
BODY_SITES: Final[tuple[str, ...]] = (
    "scalp",
    "face",
    "neck",
    "chest",
    "back",
    "abdomen",
    "upper_limb",
    "lower_limb",
    "hand",
    "foot",
    "genital",
)


@dataclass(frozen=True)
class LesionObservation:
    lesion_code: str
    body_site: str
    laterality: str | None
    size_mm: float | None
    morphology: str
    observation_date: str


def validate_observation(observation: LesionObservation) -> None:
    if observation.body_site not in BODY_SITES:
        raise ValueError(f"Unsupported body site: {observation.body_site}")
    if observation.size_mm is not None and observation.size_mm < 0:
        raise ValueError("size_mm cannot be negative")
    if not observation.lesion_code.strip():
        raise ValueError("lesion_code is required")
    if not observation.morphology.strip():
        raise ValueError("morphology is required")


def compare_size(previous_mm: float | None, current_mm: float | None) -> str:
    if previous_mm is None or current_mm is None:
        return "unknown"
    if current_mm > previous_mm:
        return "increasing"
    if current_mm < previous_mm:
        return "decreasing"
    return "stable"
