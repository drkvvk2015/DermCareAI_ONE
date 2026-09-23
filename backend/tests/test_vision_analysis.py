from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw

from dermatology.vision_analysis import analyze_image


def _jpeg_with_contrast() -> bytes:
    image = Image.new("RGB", (512, 512), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((120, 120, 392, 392), fill="black")
    stream = BytesIO()
    image.save(stream, format="JPEG", quality=95)
    return stream.getvalue()


def test_vision_analysis_passes_quality_gate_and_returns_relative_measurement():
    result = analyze_image(_jpeg_with_contrast())

    assert result.quality.usable is True
    assert result.region_detected is True
    assert result.region is not None
    assert result.region.area_pixels > 0
    assert result.measurement_unit == "pixels"


def test_low_information_image_does_not_produce_measurement():
    image = Image.fromarray(np.full((128, 128, 3), 128, dtype=np.uint8))
    stream = BytesIO()
    image.save(stream, format="JPEG")
    
    result = analyze_image(stream.getvalue())

    assert result.quality.usable is False
    assert result.region_detected is False
    assert result.region is None
