"""Versioned clinical API contracts for DermCareAI.

The mobile client and FastAPI service use these small contracts as a stable
boundary. Domain-specific schemas remain in their owning modules.
"""

from pydantic import BaseModel

API_VERSION = "v1"


class HealthResponse(BaseModel):
    status: str
    version: str = API_VERSION


class ErrorResponse(BaseModel):
    detail: str
