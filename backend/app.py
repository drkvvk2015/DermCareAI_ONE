from __future__ import annotations

import base64
import io
import logging
import os
from pathlib import Path
from typing import Any, Dict

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageStat
from pydantic import BaseModel, Field

from ImagePreprocessing import ImagePreprocessor
from MelanomaClassifier import MobileNetPredictor
from SkinLesionClassifier import SkinLesionClassifier
from evaluation import ABSTAIN_LABEL, safety_gate, validate_prediction_payload
from resilience import file_sha256

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.70"))
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(12 * 1024 * 1024)))


class PredictionResponse(BaseModel):
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    model_used: str
    visualization: str
    accepted: bool
    safety_reason: str
    image_quality: Dict[str, Any]
    app_version: str


app = FastAPI(title="DermCareAI API", version=APP_VERSION)

# Restrict CORS in production. DEVELOPMENT may override this explicitly.
configured_origins = os.getenv("CORS_ORIGINS", "*")
origins = [item.strip() for item in configured_origins.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False if origins == ["*"] else True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ModelService:
    def __init__(self) -> None:
        self.preprocessor = ImagePreprocessor(target_size=(224, 224))
        self.mobilenet: MobileNetPredictor | None = None
        self.nasnet: SkinLesionClassifier | None = None
        self.reload_count = 0
        self.last_error: str | None = None
        self.nasnet_classes = {
            0: "Actinic Keratosis",
            1: "Basal Cell Carcinoma",
            2: "Benign Keratosis",
            3: "Dermatofibroma",
            4: "Melanoma",
            5: "Melanocytic Nevus",
            6: "Vascular Lesion",
        }

    @property
    def model_paths(self) -> Dict[str, str]:
        return {
            "mobilenet": str(MODEL_DIR / "melanoma_classifier.pth"),
            "nasnet": str(MODEL_DIR / "FinetunedNasNetMobile.keras"),
        }

    def load(self) -> bool:
        """Load both models. Failure leaves the API alive in a degraded state."""
        try:
            paths = self.model_paths
            self.mobilenet = MobileNetPredictor(paths["mobilenet"])
            self.nasnet = SkinLesionClassifier(paths["nasnet"])
            self.last_error = None
            logger.info("Model service loaded")
            return True
        except Exception as exc:
            self.mobilenet = None
            self.nasnet = None
            self.last_error = str(exc)
            logger.exception("Model load failed")
            return False

    def recover(self) -> bool:
        self.reload_count += 1
        return self.load()

    def status(self) -> Dict[str, Any]:
        paths = self.model_paths
        return {
            "loaded": self.mobilenet is not None and self.nasnet is not None,
            "reload_count": self.reload_count,
            "last_error": self.last_error,
            "models": {
                name: {
                    "path": path,
                    "exists": Path(path).is_file(),
                    "sha256": file_sha256(path),
                }
                for name, path in paths.items()
            },
        }

    def process_image(self, image_bytes: bytes) -> Dict[str, Any]:
        if self.mobilenet is None or self.nasnet is None:
            raise RuntimeError("AI model service is unavailable")

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        quality = assess_image_quality(image)
        if not quality["usable"]:
            return {
                "class_name": ABSTAIN_LABEL,
                "confidence": 0.0,
                "model_used": "quality-gate",
                "visualization": "",
                "accepted": False,
                "safety_reason": quality["reason"],
                "image_quality": quality,
                "app_version": APP_VERSION,
            }

        image_array = np.array(image)
        processed_image = self.preprocessor.preprocess(image_array)
        if processed_image is None:
            raise ValueError("Image preprocessing failed")

        mobilenet_result = self.mobilenet.predict(processed_image)
        mobilenet_predicted_class = mobilenet_result["class_index"]
        mobilenet_confidence = float(mobilenet_result["probabilities"][mobilenet_predicted_class])

        if mobilenet_predicted_class == 0:
            import tensorflow as tf

            nasnet_image = tf.cast(processed_image, tf.float32) / 255.0
            nasnet_result = self.nasnet.predict_with_gradcam(nasnet_image)
            final_class = self.nasnet_classes[nasnet_result["class_index"]]
            final_confidence = float(nasnet_result["probabilities"][nasnet_result["class_index"]])
            model_used = "NASNetMobile"
            visualization = nasnet_result["gradcam_visualization"]
        else:
            # The binary model is a screening branch, not proof of melanoma.
            final_class = "Melanoma Risk Signal"
            final_confidence = mobilenet_confidence
            model_used = "MobileNetV2"
            visualization = self.mobilenet.gradcam_visualization(
                processed_image, mobilenet_predicted_class
            )

        decision = safety_gate(
            class_name=final_class,
            confidence=final_confidence,
            image_quality_ok=bool(quality["usable"]),
            minimum_confidence=MIN_CONFIDENCE,
        )
        if not decision.accepted:
            final_class = ABSTAIN_LABEL

        visualization_str = ""
        if visualization is not None:
            visualization_img = Image.fromarray(
                np.clip(visualization * 255, 0, 255).astype(np.uint8)
            )
            buffered = io.BytesIO()
            visualization_img.save(buffered, format="JPEG", quality=88)
            visualization_str = base64.b64encode(buffered.getvalue()).decode()

        result = {
            "class_name": final_class,
            "confidence": final_confidence,
            "model_used": model_used,
            "visualization": visualization_str,
            "accepted": decision.accepted,
            "safety_reason": decision.reason,
            "image_quality": quality,
            "app_version": APP_VERSION,
        }
        validation_errors = validate_prediction_payload(result)
        if validation_errors:
            raise ValueError(f"Invalid prediction payload: {validation_errors}")
        return result


model_service = ModelService()


@app.on_event("startup")
async def startup_event() -> None:
    model_service.load()


def assess_image_quality(image: Image.Image) -> Dict[str, Any]:
    width, height = image.size
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    mean = float(stat.mean[0])
    variance = float(stat.var[0])
    megapixels = (width * height) / 1_000_000

    issues: list[str] = []
    if width < 256 or height < 256:
        issues.append("resolution_too_low")
    if megapixels > 40:
        issues.append("resolution_too_high")
    if mean < 18:
        issues.append("image_too_dark")
    if mean > 242:
        issues.append("image_too_bright")
    if variance < 40:
        issues.append("low_contrast_or_blur")

    return {
        "usable": not issues,
        "reason": "Image passed the basic quality gate." if not issues else ", ".join(issues),
        "width": width,
        "height": height,
        "mean_luminance": round(mean, 2),
        "luminance_variance": round(variance, 2),
        "issues": issues,
    }


@app.get("/")
def read_root() -> Dict[str, str]:
    return {"service": "DermCareAI", "version": APP_VERSION, "status": "ok"}


@app.get("/health")
def health_check() -> Dict[str, Any]:
    status = model_service.status()
    overall = "healthy" if status["loaded"] else "degraded"
    return {"status": overall, "version": APP_VERSION, "service": status}


@app.post("/self-heal")
def self_heal() -> Dict[str, Any]:
    """Controlled recovery endpoint; it only reloads the configured local models."""
    recovered = model_service.recover()
    return {"recovered": recovered, "status": model_service.status()}


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty image upload")
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds configured size limit")

    try:
        return model_service.process_image(contents)
    except RuntimeError as exc:
        # One controlled recovery attempt for transient model/runtime faults.
        logger.warning("Inference unavailable: %s", exc)
        if model_service.recover():
            try:
                return model_service.process_image(contents)
            except Exception as retry_exc:
                logger.exception("Inference retry failed")
                raise HTTPException(status_code=503, detail="AI service temporarily unavailable") from retry_exc
        raise HTTPException(status_code=503, detail="AI service unavailable") from exc
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail="Unable to process image") from exc
