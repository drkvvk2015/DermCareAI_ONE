from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from dermatology.image_quality import ImageQualityResult, assess_image_quality


@dataclass(frozen=True)
class RegionMeasurement:
    area_pixels: int
    perimeter_pixels: float
    circularity: float
    bounding_box: tuple[int, int, int, int]


@dataclass(frozen=True)
class VisionAnalysisResult:
    quality: ImageQualityResult
    region_detected: bool
    region: RegionMeasurement | None
    measurement_unit: str
    safety_note: str


def _decode(image_bytes: bytes) -> np.ndarray:
    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode clinical image")
    return image


def _largest_candidate_region(image: np.ndarray) -> RegionMeasurement | None:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    minimum_area = 0.01 * image.shape[0] * image.shape[1]
    candidates = [c for c in contours if cv2.contourArea(c) >= minimum_area]
    if not candidates:
        return None

    contour = max(candidates, key=cv2.contourArea)
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    if perimeter <= 0:
        return None

    x, y, width, height = cv2.boundingRect(contour)
    circularity = float(min((4.0 * np.pi * area) / (perimeter * perimeter), 1.0))
    return RegionMeasurement(
        area_pixels=int(round(area)),
        perimeter_pixels=round(perimeter, 2),
        circularity=round(circularity, 4),
        bounding_box=(x, y, width, height),
    )


def analyze_image(image_bytes: bytes) -> VisionAnalysisResult:
    quality = assess_image_quality(image_bytes)
    if not quality.usable:
        return VisionAnalysisResult(
            quality=quality,
            region_detected=False,
            region=None,
            measurement_unit="pixels",
            safety_note=(
                "Image failed the quality gate. Capture a better image before "
                "using any measurement for clinical interpretation."
            ),
        )

    image = _decode(image_bytes)
    region = _largest_candidate_region(image)
    return VisionAnalysisResult(
        quality=quality,
        region_detected=region is not None,
        region=region,
        measurement_unit="pixels",
        safety_note=(
            "This is an image-processing candidate region, not clinically validated "
            "lesion segmentation. Clinician confirmation is required."
        ),
    )
