from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from auth import require_roles
from dermatology.clinical_ai import ClinicalFeatures, generate_differential


router = APIRouter(
    prefix="/api/v1/dermatology/clinical-ai",
    tags=["dermatology-clinical-ai"],
)


class ClinicalDifferentialRequest(BaseModel):
    primary_morphology: str
    secondary_changes: list[str] = Field(default_factory=list)
    color: str = ""
    border: str = ""
    surface: str = ""
    distribution: str
    symptoms: list[str] = Field(default_factory=list)
    duration_days: int | None = Field(default=None, ge=0)
    fever: bool = False
    pain: bool = False
    pruritus: bool = False
    systemic_red_flags: list[str] = Field(default_factory=list)


@router.post("/differential")
def clinical_differential(
    request: ClinicalDifferentialRequest,
    _: dict = Depends(require_roles("doctor", "admin")),
) -> dict[str, object]:
    result = generate_differential(
        ClinicalFeatures(
            primary_morphology=request.primary_morphology,
            secondary_changes=tuple(request.secondary_changes),
            color=request.color,
            border=request.border,
            surface=request.surface,
            distribution=request.distribution,
            symptoms=tuple(request.symptoms),
            duration_days=request.duration_days,
            fever=request.fever,
            pain=request.pain,
            pruritus=request.pruritus,
            systemic_red_flags=tuple(request.systemic_red_flags),
        )
    )

    return {
        "abstained": result.abstained,
        "disclaimer": result.disclaimer,
        "safety": {
            "urgent_review": result.safety.urgent_review,
            "reason": result.safety.reason,
            "matched_flags": list(result.safety.matched_flags),
        },
        "candidates": [
            {
                "label": candidate.label,
                "score": candidate.score,
                "heuristic_score": candidate.normalized_score,
                "evidence": [
                    {
                        "feature": item.feature,
                        "contribution": item.contribution,
                        "rationale": item.rationale,
                    }
                    for item in candidate.evidence
                ],
                "missing_information": list(candidate.missing_information),
            }
            for candidate in result.candidates
        ],
    }
