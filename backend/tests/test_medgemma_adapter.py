from __future__ import annotations

import io

from PIL import Image

from ai_adapters.medgemma import MedGemmaAdapter


def _image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (120, 80, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


class _Inputs(dict):
    def to(self, _device):
        return self


class _Processor:
    def __init__(self):
        self.messages = None

    def apply_chat_template(self, messages, **_kwargs):
        self.messages = messages
        return _Inputs(input_ids=[[1, 2]])

    def decode(self, _generated, **_kwargs):
        return "conservative visible-feature description"


class _Model:
    device = "cpu"

    def generate(self, **_kwargs):
        return [[1, 2, 3]]


def test_review_delivers_decoded_image_to_multimodal_processor(monkeypatch):
    monkeypatch.setenv("ENABLE_MEDGEMMA", "true")
    monkeypatch.setenv("MEDGEMMA_REVISION", "0123456789abcdef0123456789abcdef01234567")
    adapter = MedGemmaAdapter()
    processor = _Processor()
    adapter._processor = processor
    adapter._model = _Model()

    result = adapter.review(_image_bytes(), "plaque on extensor surface")

    image_part = processor.messages[0]["content"][0]
    assert image_part["type"] == "image"
    assert isinstance(image_part["image"], Image.Image)
    assert result["clinical_use"] == "suggestion_only"
    assert result["decision_authority"] == "treating_physician"


def test_production_adapter_rejects_mutable_revision(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_MEDGEMMA", "true")
    monkeypatch.setenv("MEDGEMMA_REVISION", "main")
    adapter = MedGemmaAdapter()
    assert adapter.config.enabled is False
    assert adapter.config.revision is None


def test_medgemma_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_MEDGEMMA", raising=False)
    adapter = MedGemmaAdapter()
    assert adapter.config.enabled is False
    assert adapter.available is False
    assert adapter.status()["error"] == "disabled_by_configuration"


def test_medgemma_status_exposes_governance_boundary(monkeypatch):
    monkeypatch.setenv("ENABLE_MEDGEMMA", "false")
    adapter = MedGemmaAdapter()
    status = adapter.status()
    assert status["model_id"] == "google/medgemma-1.5-4b-it"
    assert status["loaded"] is False
