# ruff: noqa: B008
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from auth import require_roles
from dermatology.scoring import (
    pasi_component,
    salt_component,
    scorable_percentage,
    vasi_component,
)


router = APIRouter(
    prefix="/api/v1/dermatology/scoring",
    tags=["dermatology-scoring"],
)


class PASIComponentRequest(BaseModel):
    erythema: float = Field(ge=0, le=4)
    induration: float = Field(ge=0, le=4)
    desquamation: float = Field(ge=0, le=4)
    area: float = Field(ge=0, le=6)


class PercentageRequest(BaseModel):
    numerator: float = Field(ge=0)
    denominator: float = Field(gt=0)


class VASIRequest(BaseModel):
    depigmented_area_percent: float = Field(ge=0, le=100)


class SALTRequest(BaseModel):
    hair_loss_percent: float = Field(ge=0, le=100)


@router.post("/pasi-component")
def calculate_pasi_component(
    req: PASIComponentRequest,
    _: dict = Depends(require_roles("doctor", "admin")),
):
    return {"value": pasi_component(**req.model_dump())}


@router.post("/percentage")
def calculate_percentage(
    req: PercentageRequest,
    _: dict = Depends(require_roles("doctor", "admin")),
):
    return {"value": scorable_percentage(req.numerator, req.denominator)}


@router.post("/vasi")
def calculate_vasi(
    req: VASIRequest,
    _: dict = Depends(require_roles("doctor", "admin")),
):
    return {"value": vasi_component(req.depigmented_area_percent)}


@router.post("/salt")
def calculate_salt(
    req: SALTRequest,
    _: dict = Depends(require_roles("doctor", "admin")),
):
    return {"value": salt_component(req.hair_loss_percent)}
