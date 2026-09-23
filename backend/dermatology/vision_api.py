from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import require_roles
from dermatology.vision_analysis import analyze_image

router = APIRouter(
    prefix="/api/v1/dermatology/vision",
    tags=["dermatology-vision"],
)


@router.post("/analyze")
async def analyze_dermatology_image(
    file: UploadFile = File(...),
    _: dict = Depends(require_roles("doctor", "admin")),
) -> dict[str, object]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty image upload")

    try:
        result = analyze_image(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload: dict[str, object] = {
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
        "measurement_unit": result.measurement_unit,
        "safety_note": result.safety_note,
    }
    if result.region is not None:
        payload["region"] = {
            "area_pixels": result.region.area_pixels,
            "perimeter_pixels": result.region.perimeter_pixels,
            "circularity": result.region.circularity,
            "bounding_box": list(result.region.bounding_box),
        }
    return payload
