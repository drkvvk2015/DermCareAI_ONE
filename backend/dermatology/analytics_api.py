# ruff: noqa: B008
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import require_roles
from dermatology.analytics import cohort_summary


router = APIRouter(
    prefix="/api/v1/dermatology/analytics",
    tags=["dermatology-analytics"],
)


@router.post("/cohort-summary")
def cohort(
    records: list[dict[str, object]],
    user: dict = Depends(require_roles("admin", "auditor", "doctor")),
):
    claims = user.get("claims", {})
    if not (claims.get("organization_id") or claims.get("organizationId")):
        raise HTTPException(status_code=403, detail="Clinical tenant context is missing")
    return cohort_summary(records)
