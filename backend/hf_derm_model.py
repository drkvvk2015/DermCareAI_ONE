from __future__ import annotations

import os
from typing import Any, Dict

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

MODEL_ID = os.getenv("DERM_MODEL_ID", "PREMAADC/vit-base-ham10000")


class EmbeddedDermModel:
    """Locally cached 7-class HAM10000 model.

    This is an embedded research model, not a clinically validated diagnostic device.
    """

    def __init__(self, model_id: str = MODEL_ID) -> None:
        self.model_id = model_id
        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = AutoModelForImageClassification.from_pretrained(model_id)
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    @torch.no_grad()
    def predict(self, image: Image.Image) -> Dict[str, Any]:
        inputs = self.processor(images=image.convert("RGB"), return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        index = int(torch.argmax(probs).item())
        label = self.model.config.id2label.get(index, str(index))
        return {
            "class_name": label,
            "confidence": float(probs[index].item()),
            "model_used": f"Embedded:{self.model_id}",
            "probabilities": probs.detach().cpu().numpy().tolist(),
            "device": str(self.device),
            "research_only": True,
        }
