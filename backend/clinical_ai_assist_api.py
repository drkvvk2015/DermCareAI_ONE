from __future__ import annotations

import io
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from PIL import Image
from PIL.Image import DecompressionBombError, UnidentifiedImageError

from ai_adapters.medgemma import MedGemmaAdapter
from audit import AuditEvent, record_event
from auth import require_roles
from clinical_ai_policy import capabilities, require_clinical_assist_enabled
from clinical_store import get_encounter, has_active_consent
from dermatology.clinical_ai import ClinicalFeatures, generate_differential
from dermatology.vision_analysis import analyze_image
from inference_runtime import run_inference
from upload_limits import MAX_IMAGE_BYTES, read_upload_limited

router = APIRouter(prefix="/api/v1/clinical-ai", tags=["clinical-ai-assist"])


_ALLOWED_IMAGE_FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


async def _read_validated_clinical_image(file: UploadFile) -> bytes:
    expected_format = _ALLOWED_IMAGE_FORMATS.get((file.content_type or "").lower())
    if expected_format is None:
        raise HTTPException(status_code=400, detail="Unsupported image MIME type")

    content = await read_upload_limited(file, MAX_IMAGE_BYTES)
    if not content:
        raise HTTPException(status_code=400, detail="Empty image upload")

    try:
        with Image.open(io.BytesIO(content)) as uploaded:
            decoded_format = str(uploaded.format or "").upper()
            uploaded.verify()
            if decoded_format != expected_format:
                raise HTTPException(status_code=400, detail="Image MIME type does not match decoded format")
    except HTTPException:
        raise
    except DecompressionBombError as exc:
        raise HTTPException(status_code=413, detail="Image dimensions exceed configured safety limit") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Unable to decode image upload") from exc

    return content


class DifferentialAssistRequest(BaseModel):
    encounter_id: str = Field(min_length=1, max_length=120)
    primary_morphology: str = Field(min_length=1, max_length=120)
    secondary_changes: list[str] = Field(default_factory=list, max_length=20)
    color: str = Field(default="", max_length=120)
    border: str = Field(default="", max_length=120)
    surface: str = Field(default="", max_length=120)
    distribution: str = Field(default="", max_length=240)
    symptoms: list[str] = Field(default_factory=list, max_length=20)
    duration_days: int | None = Field(default=None, ge=0)
    fever: bool = False
    pain: bool = False
    pruritus: bool = False
    systemic_red_flags: list[str] = Field(default_factory=list, max_length=20)


@router.get("/capabilities")
def get_capabilities(_: dict[str, Any] = Depends(require_roles("doctor", "admin", "auditor"))):
    state = capabilities()
    return {
        "clinical_assist_enabled": state.clinical_assist_enabled,
        "generative_assist_enabled": state.generative_assist_enabled,
        "diagnostic_mode": state.diagnostic_mode.value,
        "production_boundary": {
            "clinical_assist": "assistive_only",
            "diagnostic_inference": state.diagnostic_mode.value,
            "autonomous_diagnosis": False,
            "autonomous_prescribing": False,
        },
    }


@router.post("/differential")
def differential_assist(
    req: DifferentialAssistRequest,
    user: dict[str, Any] = Depends(require_roles("doctor", "admin")),
):
    try:
        require_clinical_assist_enabled()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    claims = user.get("claims", {})
    organization_id = claims.get("organization_id") or claims.get("organizationId")
    clinic_id = claims.get("clinic_id") or claims.get("clinicId")
    if not organization_id or not clinic_id:
        raise HTTPException(status_code=403, detail="Clinical tenant context is missing")

    encounter = get_encounter(req.encounter_id, str(organization_id), str(clinic_id))
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    result = generate_differential(
        ClinicalFeatures(
            primary_morphology=req.primary_morphology,
            secondary_changes=tuple(req.secondary_changes),
            color=req.color,
            border=req.border,
            surface=req.surface,
            distribution=req.distribution,
            symptoms=tuple(req.symptoms),
            duration_days=req.duration_days,
            fever=req.fever,
            pain=req.pain,
            pruritus=req.pruritus,
            systemic_red_flags=tuple(req.systemic_red_flags),
        )
    )

    payload = {
        "capability": "differential_support",
        "clinical_use": "preliminary_assistive_only",
        "diagnostic_status": "not_a_diagnosis",
        "model_name": "DermCareAI deterministic clinical-support rules v1",
        "research_model": False,
        "requires_clinician_verification": True,
        "can_sign_diagnosis": False,
        "can_prescribe": False,
        "abstained": result.abstained,
        "safety": {
            "urgent_review": result.safety.urgent_review,
            "reason": result.safety.reason,
            "matched_flags": list(result.safety.matched_flags),
        },
        "candidates": [
            {
                "label": item.label,
                "support_score": item.score,
                "support_score_is_probability": False,
                "evidence": [
                    {"feature": ev.feature, "contribution": ev.contribution, "rationale": ev.rationale}
                    for ev in item.evidence
                ],
                "missing_information": list(item.missing_information),
            }
            for item in result.candidates
        ],
        "disclaimer": result.disclaimer,
    }
    record_event(
        AuditEvent(
            action="clinical_ai_assist_differential",
            resource_type="clinical_encounter",
            resource_id=req.encounter_id,
            metadata={
                "patient_id": encounter["patient_id"],
                "capability": "differential_support",
                "model_name": payload["model_name"],
                "abstained": result.abstained,
                "urgent_review": result.safety.urgent_review,
                "candidate_labels": [item.label for item in result.candidates],
            },
        ),
        user,
    )
    return payload


@router.post("/image-quality/{encounter_id}")
async def image_quality_assist(
    encounter_id: str,
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(require_roles("doctor", "admin")),
):
    try:
        require_clinical_assist_enabled()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    claims = user.get("claims", {})
    organization_id = claims.get("organization_id") or claims.get("organizationId")
    clinic_id = claims.get("clinic_id") or claims.get("clinicId")
    if not organization_id or not clinic_id:
        raise HTTPException(status_code=403, detail="Clinical tenant context is missing")

    encounter = get_encounter(encounter_id, str(organization_id), str(clinic_id))
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if not has_active_consent(
        organization_id=str(organization_id),
        clinic_id=str(clinic_id),
        patient_id=encounter["patient_id"],
        purpose="clinical-image",
    ):
        raise HTTPException(status_code=409, detail="Active clinical-image consent is required")

    content = await _read_validated_clinical_image(file)
    try:
        result = await run_inference(analyze_image, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = {
        "capability": "clinical_image_quality",
        "clinical_use": "assistive_only",
        "diagnostic_status": "not_a_diagnosis",
        "requires_clinician_verification": True,
        "quality": {
            "usable": result.quality.usable,
            "reason": result.quality.reason,
            "width": result.quality.width,
            "height": result.quality.height,
            "mean_luminance": result.quality.mean_luminance,
            "luminance_variance": result.quality.luminance_variance,
            "issues": list(result.quality.issues),
        },
        "region_detected": result.region_detected,
        "region": (
            {
                "area_pixels": result.region.area_pixels,
                "perimeter_pixels": result.region.perimeter_pixels,
                "circularity": result.region.circularity,
                "bounding_box": list(result.region.bounding_box),
            }
            if result.region is not None
            else None
        ),
        "safety_note": result.safety_note,
    }
    record_event(
        AuditEvent(
            action="clinical_ai_assist_image_quality",
            resource_type="clinical_encounter",
            resource_id=encounter_id,
            metadata={
                "patient_id": encounter["patient_id"],
                "capability": "clinical_image_quality",
                "quality_usable": result.quality.usable,
                "region_detected": result.region_detected,
            },
        ),
        user,
    )
    return response


@router.post("/generative-image-review/{encounter_id}")
async def generative_image_review(
    encounter_id: str,
    clinical_context: str = "",
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(require_roles("doctor", "admin")),
):
    state = capabilities()
    if not state.clinical_assist_enabled or not state.generative_assist_enabled:
        raise HTTPException(status_code=409, detail="Generative clinical assist is disabled by production configuration")

    claims = user.get("claims", {})
    organization_id = claims.get("organization_id") or claims.get("organizationId")
    clinic_id = claims.get("clinic_id") or claims.get("clinicId")
    if not organization_id or not clinic_id:
        raise HTTPException(status_code=403, detail="Clinical tenant context is missing")

    encounter = get_encounter(encounter_id, str(organization_id), str(clinic_id))
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if not has_active_consent(
        organization_id=str(organization_id),
        clinic_id=str(clinic_id),
        patient_id=encounter["patient_id"],
        purpose="clinical-image",
    ):
        raise HTTPException(status_code=409, detail="Active clinical-image consent is required")

    content = await _read_validated_clinical_image(file)

    adapter = MedGemmaAdapter()
    if not adapter.load():
        raise HTTPException(status_code=503, detail="Generative clinical assist model is unavailable")
    try:
        result = await run_inference(adapter.review, content, clinical_context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result.update(
        {
            "capability": "generative_image_review",
            "clinical_use": "preliminary_assistive_only",
            "diagnostic_status": "not_a_diagnosis",
            "requires_clinician_verification": True,
            "can_sign_diagnosis": False,
            "can_prescribe": False,
        }
    )
    record_event(
        AuditEvent(
            action="clinical_ai_assist_generative_image_review",
            resource_type="clinical_encounter",
            resource_id=encounter_id,
            metadata={
                "patient_id": encounter["patient_id"],
                "capability": "generative_image_review",
                "model_name": result.get("model_name"),
                "model_id": result.get("model_id"),
                "revision": result.get("revision"),
                "image_sha256": result.get("image_sha256"),
            },
        ),
        user,
    )
    return result
