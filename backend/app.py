from __future__ import annotations

import base64
import io
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel, Field

from dermatology.analytics_api import router as dermatology_analytics_router
from dermatology.decision_support_api import router as dermatology_scoring_router
from dermatology.vision_api import router as dermatology_vision_router
from dermatology.followup_api import router as dermatology_followup_router
from dermatology.procedure_api import router as dermatology_procedure_router
from dermatology.image_quality import assess_image_quality as assess_dermatology_image_quality
from ai_governance import build_governance_card
from audit import router as audit_router
from auth import require_roles
from clinical import router as clinical_router
from ai_registry import router as ai_registry_router
from admin import router as admin_router
from media import router as media_router
from commerce import router as commerce_router
from prescriptions import router as prescriptions_router
from evaluation import ABSTAIN_LABEL, safety_gate, validate_prediction_payload
from model_registry import verify_models
from notifications import router as notifications_router
from observability import record_prediction, record_request, snapshot as observability_snapshot
from platform_contracts import AIGovernanceCard, PlatformInfo, ReadinessComponent, ReadinessResponse, utc_now
from request_context import get_request_id, new_request_id, reset_request_id, set_request_id
from rate_limit import client_key, enforce_rate_limit, redis_configured
from resilience import file_sha256
from production_readiness import evaluate_readiness

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
APP_VERSION = os.getenv("APP_VERSION", "5.1.0")
APP_ENV = os.getenv("APP_ENV", "development")
MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.70"))
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(12 * 1024 * 1024)))
ENABLE_EMBEDDED_DERM_MODEL = os.getenv("ENABLE_EMBEDDED_DERM_MODEL", "true").lower() == "true"


class PredictionResponse(BaseModel):
    request_id: str
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    model_used: str
    visualization: str
    accepted: bool
    safety_reason: str
    image_quality: Dict[str, Any]
    app_version: str
    governance: AIGovernanceCard


app = FastAPI(title="DermCareAI Clinic Platform API", version=APP_VERSION)
configured_origins = os.getenv("CORS_ORIGINS", "http://localhost:8081")
if APP_ENV == "production" and configured_origins.strip() in {"", "*"}:
    raise RuntimeError("Production CORS_ORIGINS must explicitly list approved origins")
origins = [item.strip() for item in configured_origins.split(",") if item.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST", "PUT", "PATCH"], allow_headers=["*"])


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = new_request_id(request.headers.get("X-Request-ID"))
    token = set_request_id(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        record_request(response.status_code, elapsed_ms)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.2f}"
        return response
    finally:
        reset_request_id(token)


app.include_router(commerce_router)
app.include_router(prescriptions_router)
app.include_router(notifications_router)
app.include_router(audit_router)
app.include_router(media_router)
app.include_router(clinical_router)
app.include_router(ai_registry_router)
app.include_router(admin_router)
app.include_router(dermatology_analytics_router)
app.include_router(dermatology_scoring_router)
app.include_router(dermatology_vision_router)
app.include_router(dermatology_followup_router)
app.include_router(dermatology_procedure_router)


class ModelService:
    def __init__(self) -> None:
        self.preprocessor: Any | None = None
        self.mobilenet: Any | None = None
        self.nasnet: Any | None = None
        self.embedded: Any | None = None
        self.mode = "unavailable"
        self.reload_count = 0
        self.last_error: str | None = None
        self.nasnet_classes = {0: "Actinic Keratosis", 1: "Basal Cell Carcinoma", 2: "Benign Keratosis", 3: "Dermatofibroma", 4: "Melanoma", 5: "Melanocytic Nevus", 6: "Vascular Lesion"}

    @property
    def model_paths(self) -> Dict[str, str]:
        return {"mobilenet": str(MODEL_DIR / "melanoma_classifier.pth"), "nasnet": str(MODEL_DIR / "FinetunedNasNetMobile.keras")}

    def load(self) -> bool:
        paths = self.model_paths
        try:
            if Path(paths["mobilenet"]).is_file() and Path(paths["nasnet"]).is_file():
                # Load heavyweight ML dependencies only when real model weights exist.
                from ImagePreprocessing import ImagePreprocessor
                from MelanomaClassifier import MobileNetPredictor
                from SkinLesionClassifier import SkinLesionClassifier

                self.preprocessor = ImagePreprocessor(target_size=(224, 224))
                self.mobilenet = MobileNetPredictor(paths["mobilenet"])
                self.nasnet = SkinLesionClassifier(paths["nasnet"])
                self.embedded = None
                self.mode = "local-research-models"
                self.last_error = None
                return True
            raise FileNotFoundError("Local research model weights are not installed")
        except Exception as exc:
            self.preprocessor = None
            self.mobilenet = None
            self.nasnet = None
            self.last_error = str(exc)
            if ENABLE_EMBEDDED_DERM_MODEL:
                try:
                    from hf_derm_model import EmbeddedDermModel

                    self.embedded = EmbeddedDermModel()
                    self.mode = "embedded-ham10000-research-model"
                    self.last_error = None
                    logger.info("Embedded dermatology model loaded")
                    return True
                except Exception as embedded_exc:
                    self.embedded = None
                    self.last_error = f"Local models: {exc}; embedded model: {embedded_exc}"
            self.mode = "unavailable"
            logger.exception("All model loading paths failed")
            return False

    def recover(self) -> bool:
        self.reload_count += 1
        return self.load()

    def status(self) -> Dict[str, Any]:
        paths = self.model_paths
        return {
            "loaded": self.mode != "unavailable",
            "mode": self.mode,
            "reload_count": self.reload_count,
            "has_error": self.last_error is not None,
            "registry": verify_models(str(MODEL_DIR)),
            "embedded_model_enabled": ENABLE_EMBEDDED_DERM_MODEL,
            "models": {
                name: {"path": path, "exists": Path(path).is_file(), "sha256": file_sha256(path)}
                for name, path in paths.items()
            },
        }

    def process_image(self, image_bytes: bytes) -> Dict[str, Any]:
        if self.mode == "unavailable":
            raise RuntimeError("AI model service is unavailable")
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        quality = assess_image_quality(image)
        if not quality["usable"]:
            model_name = "quality-gate"
            result = {
                "request_id": get_request_id() or new_request_id(),
                "class_name": ABSTAIN_LABEL,
                "confidence": 0.0,
                "model_used": model_name,
                "visualization": "",
                "accepted": False,
                "safety_reason": quality["reason"],
                "image_quality": quality,
                "app_version": APP_VERSION,
                "governance": build_governance_card(
                    model_name=model_name,
                    model_provenance="Pre-inference image-quality safety gate",
                    confidence_threshold=MIN_CONFIDENCE,
                    research_model=False,
                ),
            }
            record_prediction(model=model_name, accepted=False)
            return result

        visualization = None
        model_provenance = "Controlled local DermCareAI research weights"
        research_model = True
        if self.mode == "embedded-ham10000-research-model" and self.embedded is not None:
            embedded_result = self.embedded.predict(image)
            final_class = embedded_result["class_name"]
            final_confidence = float(embedded_result["confidence"])
            model_used = embedded_result["model_used"]
            model_provenance = "PREMAADC/vit-base-ham10000 research fallback"
        else:
            if self.preprocessor is None or self.mobilenet is None:
                raise RuntimeError("Local model dependencies are unavailable")
            image_array = np.array(image)
            processed_image = self.preprocessor.preprocess(image_array)
            if processed_image is None:
                raise ValueError("Image preprocessing failed")
            mobilenet_result = self.mobilenet.predict(processed_image)  # type: ignore[union-attr]
            mobilenet_predicted_class = mobilenet_result["class_index"]
            mobilenet_confidence = float(mobilenet_result["probabilities"][mobilenet_predicted_class])
            if mobilenet_predicted_class == 0:
                import tensorflow as tf

                nasnet_image = tf.cast(processed_image, tf.float32) / 255.0
                nasnet_result = self.nasnet.predict_with_gradcam(nasnet_image)  # type: ignore[union-attr]
                final_class = self.nasnet_classes[nasnet_result["class_index"]]
                final_confidence = float(nasnet_result["probabilities"][nasnet_result["class_index"]])
                model_used = "NASNetMobile"
                visualization = nasnet_result["gradcam_visualization"]
            else:
                final_class = "Melanoma Risk Signal"
                final_confidence = mobilenet_confidence
                model_used = "MobileNetV2"
                visualization = self.mobilenet.gradcam_visualization(processed_image, mobilenet_predicted_class)  # type: ignore[union-attr]

        registry = verify_models(str(MODEL_DIR))
        registry_integrity = all(
            (not item.get("materialized")) or bool(item.get("hash_matches"))
            for item in registry.values()
        )
        decision = safety_gate(
            class_name=final_class,
            confidence=final_confidence,
            image_quality_ok=bool(quality["usable"]),
            minimum_confidence=MIN_CONFIDENCE,
            model_registered=registry_integrity,
            model_enabled=self.mode != "unavailable",
        )
        if not decision.accepted:
            final_class = ABSTAIN_LABEL

        visualization_str = ""
        if visualization is not None:
            visualization_img = Image.fromarray(np.clip(visualization * 255, 0, 255).astype(np.uint8))
            buffered = io.BytesIO()
            visualization_img.save(buffered, format="JPEG", quality=88)
            visualization_str = base64.b64encode(buffered.getvalue()).decode()

        result = {
            "request_id": get_request_id() or new_request_id(),
            "class_name": final_class,
            "confidence": final_confidence,
            "model_used": model_used,
            "visualization": visualization_str,
            "accepted": decision.accepted,
            "safety_reason": decision.reason,
            "image_quality": quality,
            "app_version": APP_VERSION,
            "governance": build_governance_card(
                model_name=model_used,
                model_provenance=model_provenance,
                confidence_threshold=MIN_CONFIDENCE,
                research_model=research_model,
            ),
        }
        record_prediction(model=model_used, accepted=decision.accepted)
        errors = validate_prediction_payload(result)
        if errors:
            raise ValueError(f"Invalid prediction payload: {errors}")
        return result


model_service = ModelService()


@app.on_event("startup")
async def startup_event() -> None:
    model_service.load()


def assess_image_quality(image: Image.Image) -> Dict[str, Any]:
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=92)
    quality = assess_dermatology_image_quality(buffered.getvalue())
    return {
        "usable": quality.usable,
        "reason": quality.reason,
        "width": quality.width,
        "height": quality.height,
        "mean_luminance": quality.mean_luminance,
        "luminance_variance": quality.luminance_variance,
        "issues": list(quality.issues),
    }


@app.get("/api/v1/platform", response_model=PlatformInfo)
def platform_info() -> PlatformInfo:
    return PlatformInfo(
        api_version="v1",
        app_version=APP_VERSION,
        service="DermCareAI Clinic Platform API",
        environment=os.getenv("APP_ENV", "development"),
        capabilities=[
            "clinical-workflow",
            "ai-decision-support",
            "ai-safety-abstention",
            "model-provenance",
            "billing-and-payments",
            "pharmacy-integrity",
            "notifications",
            "hash-chained-audit",
            "request-correlation",
            "privacy-safe-observability",
            "encounter-first-clinical-record",
            "multi-clinic-tenant-scope",
            "consent-and-retention-metadata",
            "longitudinal-lesion-tracking",
            "model-validation-and-approval-ledger",
            "clinical-signoff",
            "follow-up-management",
            "clinician-reviewed-ai-assessments",
        ],
        generated_at=utc_now(),
    )


@app.get("/api/v1/health/live")
def platform_liveness() -> Dict[str, Any]:
    return {"status": "alive", "version": APP_VERSION, "request_id": get_request_id()}


@app.get("/api/v1/health/ready", response_model=ReadinessResponse)
def platform_readiness() -> ReadinessResponse:
    model_status = model_service.status()
    registry = model_status["registry"]
    registry_ok = all(
        (not item.get("materialized")) or bool(item.get("hash_matches"))
        for item in registry.values()
    )
    auth_enabled = os.getenv("FIREBASE_AUTH_REQUIRED", "true").lower() == "true"
    readiness_findings = evaluate_readiness(
        app_env=APP_ENV,
        database_url=os.getenv("CLINICAL_DATABASE_URL") or os.getenv("DATABASE_URL", ""),
        commerce_database_url=os.getenv("COMMERCE_DATABASE_URL") or os.getenv("DATABASE_URL", ""),
        cors_origins=configured_origins,
        app_version=APP_VERSION,
        firebase_auth_required=auth_enabled,
        redis_configured=redis_configured(),
    )
    blocking_findings = [finding for finding in readiness_findings if finding.severity == "block"]
    components = {
        "model_service": ReadinessComponent(
            status="ok" if model_status["loaded"] else "degraded",
            detail=model_status["mode"],
        ),
        "model_registry": ReadinessComponent(
            status="ok" if registry_ok else "degraded",
            detail="registry integrity checks passed"
            if registry_ok
            else "one or more materialized model hashes do not match",
        ),
        "clinic_auth": ReadinessComponent(
            status="ok" if auth_enabled else "not_configured",
            detail="Firebase authentication enforced"
            if auth_enabled
            else "FIREBASE_AUTH_REQUIRED is disabled",
        ),
        "deployment_contract": ReadinessComponent(
            status="ok" if not blocking_findings else "degraded",
            detail="Production deployment contract passed"
            if not blocking_findings
            else "; ".join(f"{finding.code}: {finding.message}" for finding in blocking_findings),
        ),
    }
    overall = "ready" if all(component.status == "ok" for component in components.values()) else "degraded"
    return ReadinessResponse(
        status=overall,
        version=APP_VERSION,
        components=components,
        generated_at=utc_now(),
    )


@app.get("/api/v1/observability/metrics")
def platform_metrics(_: dict[str, Any] = Depends(require_roles("admin", "auditor"))) -> Dict[str, Any]:
    return {"version": APP_VERSION, "metrics": observability_snapshot()}


@app.get("/api/v1/ai/policy", response_model=AIGovernanceCard)
def ai_policy() -> AIGovernanceCard:
    return AIGovernanceCard(
        **build_governance_card(
            model_name="DermCareAI decision-support policy",
            model_provenance="Application-level safety contract",
            confidence_threshold=MIN_CONFIDENCE,
            research_model=True,
        )
    )


@app.get("/")
def read_root() -> Dict[str, str]:
    return {"service": "DermCareAI", "version": APP_VERSION, "status": "ok"}


@app.get("/health")
def health_check() -> Dict[str, Any]:
    status = model_service.status()
    return {
        "status": "healthy" if status["loaded"] else "degraded",
        "version": APP_VERSION,
        "request_id": get_request_id(),
        "service": status,
    }


@app.post("/self-heal")
def self_heal(request: Request, user: dict[str, Any] = Depends(require_roles("admin"))) -> Dict[str, Any]:
    user_key = client_key(request, user["uid"])
    enforce_rate_limit(f"self-heal:{user_key}", limit=3, window_seconds=300)
    recovered = model_service.recover()
    return {"recovered": recovered, "status": model_service.status()}


@app.get("/models")
def model_status(_: dict[str, Any] = Depends(require_roles("admin", "auditor"))) -> Dict[str, Any]:
    return {"version": APP_VERSION, **model_service.status()}


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: Request, file: UploadFile = File(...), user: dict[str, Any] = Depends(require_roles("doctor", "admin"))) -> Dict[str, Any]:
    user_key = client_key(request, user["uid"])
    enforce_rate_limit(f"predict:{user_key}", limit=30, window_seconds=60)
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
        if model_service.recover():
            try:
                return model_service.process_image(contents)
            except Exception as retry_exc:
                raise HTTPException(status_code=503, detail="AI service temporarily unavailable") from retry_exc
        raise HTTPException(status_code=503, detail="AI service unavailable") from exc
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail="Unable to process image") from exc
