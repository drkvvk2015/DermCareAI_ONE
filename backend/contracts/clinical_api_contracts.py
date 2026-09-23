"""Versioned clinical API contracts for DermCareAI.

This module centralizes request/response schemas so the React Native client and
FastAPI backend share a stable contract.
"""

from pydantic import BaseModel

API_VERSION = "v1"

class HealthResponse(BaseModel):
    status: str
    version: str = API_VERSION

class ErrorResponse(BaseModel):
    detail: str
