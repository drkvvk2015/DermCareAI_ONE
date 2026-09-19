"""Versioned platform contracts for DermCareAI's API and AI governance layer."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class PlatformInfo(BaseModel):
    api_version: str
    app_version: str
    service: str
    environment: str
    capabilities: list[str]
    generated_at: str


class ReadinessComponent(BaseModel):
    status: Literal["ok", "degraded", "not_configured"]
    detail: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded"]
    version: str
    components: dict[str, ReadinessComponent]
    generated_at: str


class AIGovernanceCard(BaseModel):
    decision_type: Literal["clinical_decision_support"]
    intended_use: str
    diagnostic_status: Literal["not_a_diagnosis"]
    human_review_required: bool = True
    abstention_enabled: bool = True
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    model_provenance: str
    model_name: str
    research_model: bool
    safety_controls: list[str]
    limitations: list[str]


class PredictionEnvelope(BaseModel):
    request_id: str
    prediction: dict[str, Any]
    governance: AIGovernanceCard


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
