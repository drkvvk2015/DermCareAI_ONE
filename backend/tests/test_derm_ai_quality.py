from io import BytesIO
from PIL import Image
from dermatology.image_quality import assess_image_quality

def _jpeg(size=(512, 512), value=128):
    image = Image.new("RGB", size, (value, value, value))
    buf = BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()

def test_small_image_is_rejected():
    result = assess_image_quality(_jpeg((128, 128)))
    assert not result.usable
    assert "resolution_too_low" in result.issues

def test_decodable_image_reports_dimensions():
    result = assess_image_quality(_jpeg())
    assert (result.width, result.height) == (512, 512)
