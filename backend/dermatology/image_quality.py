from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from PIL import Image, ImageStat

@dataclass(frozen=True)
class ImageQualityResult:
    usable: bool
    reason: str
    width: int
    height: int
    mean_luminance: float
    luminance_variance: float
    issues: tuple[str, ...]

def assess_image_quality(image_bytes: bytes, *, min_dimension: int = 256, min_luminance_variance: float = 40.0) -> ImageQualityResult:
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError("Unable to decode clinical image") from exc
    width, height = image.size
    stat = ImageStat.Stat(image.convert("L"))
    mean = float(stat.mean[0])
    variance = float(stat.var[0])
    issues: list[str] = []
    if width < min_dimension or height < min_dimension:
        issues.append("resolution_too_low")
    if mean < 18:
        issues.append("image_too_dark")
    elif mean > 242:
        issues.append("image_too_bright")
    if variance < min_luminance_variance:
        issues.append("low_contrast_or_blur")
    return ImageQualityResult(
        usable=not issues,
        reason="Image passed the quality gate." if not issues else ", ".join(issues),
        width=width, height=height,
        mean_luminance=round(mean, 2),
        luminance_variance=round(variance, 2),
        issues=tuple(issues),
    )
