from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class MedGemmaConfig:
    model_id: str
    revision: str | None
    enabled: bool
    max_new_tokens: int
    temperature: float


class MedGemmaAdapter:
    """Opt-in adapter for MedGemma 1.5 4B.

    This adapter is deliberately disabled unless explicitly enabled. It produces
    preliminary assistive output only; it never marks an assessment as a
    diagnosis, treatment recommendation, or clinician-approved result.
    """

    def __init__(self) -> None:
        self.config = MedGemmaConfig(
            model_id=os.getenv("MEDGEMMA_MODEL_ID", "google/medgemma-1.5-4b-it"),
            revision=os.getenv("MEDGEMMA_REVISION") or None,
            enabled=os.getenv("ENABLE_MEDGEMMA", "false").lower() == "true",
            max_new_tokens=max(64, min(int(os.getenv("MEDGEMMA_MAX_NEW_TOKENS", "256")), 1024)),
            temperature=max(0.0, min(float(os.getenv("MEDGEMMA_TEMPERATURE", "0.0")), 1.0)),
        )
        self._processor: Any | None = None
        self._model: Any | None = None
        self._error: str | None = None

    @property
    def available(self) -> bool:
        return self.config.enabled and self._model is not None and self._processor is not None

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "loaded": self.available,
            "model_id": self.config.model_id,
            "revision": self.config.revision,
            "error": self._error,
        }

    def load(self) -> bool:
        if not self.config.enabled:
            self._error = "disabled_by_configuration"
            return False
        try:
            from transformers import AutoProcessor, Gemma3ForConditionalGeneration

            kwargs: dict[str, Any] = {}
            if self.config.revision:
                kwargs["revision"] = self.config.revision
            self._processor = AutoProcessor.from_pretrained(self.config.model_id, **kwargs)
            self._model = Gemma3ForConditionalGeneration.from_pretrained(self.config.model_id, **kwargs)
            self._error = None
            return True
        except Exception as exc:
            self._processor = None
            self._model = None
            self._error = str(exc)
            return False

    def review(self, image_bytes: bytes, clinical_context: str) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("MedGemma adapter is not loaded")
        if not image_bytes:
            raise ValueError("image_bytes is required")

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_sha256 = hashlib.sha256(image_bytes).hexdigest()
        prompt = (
            "You are a clinical decision-support research assistant. "
            "Describe visible dermatologic features conservatively. "
            "Do not diagnose, prescribe, or recommend treatment. "
            "State uncertainty and recommend clinician correlation. "
            f"Clinical context: {clinical_context.strip()[:4000]}"
        )
        messages = [{"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": prompt},
        ]}]
        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        outputs = self._model.generate(
            **inputs,
            max_new_tokens=self.config.max_new_tokens,
            do_sample=self.config.temperature > 0,
            temperature=self.config.temperature if self.config.temperature > 0 else None,
        )
        generated = outputs[0][inputs["input_ids"].shape[-1]:]
        text = self._processor.decode(generated, skip_special_tokens=True).strip()
        return {
            "model_name": "MedGemma",
            "model_id": self.config.model_id,
            "revision": self.config.revision,
            "artifact_sha256": None,
            "image_sha256": image_sha256,
            "output": text,
            "clinical_use": "preliminary_assistive_only",
            "requires_clinician_verification": True,
            "can_sign_diagnosis": False,
            "can_prescribe": False,
        }
