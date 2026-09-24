from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from audit import AuditEvent, record_event
from auth import require_roles
from clinical_store import get_encounter
from prescription_store import (
    cancel_prescription,
    create_prescription,
    get_prescription,
    list_prescriptions,
    mark_prescription_dispensed,
)

router = APIRouter(prefix="/api/v1/prescriptions", tags=["prescriptions"])


def _tenant(user: dict[str, Any]) -> tuple[str, str]:
    claims = user.get("claims", {})
    organization_id = claims.get("organization_id") or claims.get("organizationId")
    clinic_id = claims.get("clinic_id") or claims.get("clinicId")
    if not organization_id or not clinic_id:
        raise HTTPException(status_code=403, detail="Prescription tenant context is missing")
    return str(organization_id), str(clinic_id)


class MedicationItem(BaseModel):
    medicine_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    strength: str = Field(min_length=1, max_length=120)
    dose: str = Field(min_length=1, max_length=120)
    route: str = Field(min_length=1, max_length=80)
    frequency: str = Field(min_length=1, max_length=120)
    duration: str = Field(min_length=1, max_length=120)
    quantity: float = Field(gt=0)
    instructions: str = Field(default="", max_length=1000)


class PrescriptionCreate(BaseModel):
    patient_id: str = Field(min_length=1, max_length=120)
    encounter_id: str = Field(min_length=1, max_length=120)
    instructions: str = Field(default="", max_length=2000)
    items: list[MedicationItem] = Field(min_length=1, max_length=50)


@router.post("")
def create(
    req: PrescriptionCreate,
    user: dict[str, Any] = Depends(require_roles("admin", "doctor")),
):
    organization_id, clinic_id = _tenant(user)
    encounter = get_encounter(req.encounter_id, clinic_id)
    if encounter is None or encounter.get("organization_id") != organization_id or encounter.get("patient_id") != req.patient_id:
        raise HTTPException(status_code=404, detail="Encounter not found for patient and tenant")

    result = create_prescription(
        organization_id=organization_id,
        clinic_id=clinic_id,
        patient_id=req.patient_id,
        encounter_id=req.encounter_id,
        instructions=req.instructions,
        items=[item.model_dump() for item in req.items],
        prescribed_by=str(user.get("uid") or user.get("sub") or "unknown"),
    )
    record_event(
        AuditEvent(
            action="prescription_created",
            resource_type="prescription",
            resource_id=result["id"],
            metadata={"patient_id": req.patient_id, "encounter_id": req.encounter_id, "item_count": len(req.items)},
        ),
        user,
    )
    return result


@router.get("/patient/{patient_id}")
def patient_prescriptions(
    patient_id: str,
    user: dict[str, Any] = Depends(require_roles("admin", "doctor", "pharmacist")),
):
    organization_id, clinic_id = _tenant(user)
    return list_prescriptions(patient_id, organization_id=organization_id, clinic_id=clinic_id)


@router.get("/{prescription_id}")
def read_prescription(
    prescription_id: str,
    user: dict[str, Any] = Depends(require_roles("admin", "doctor", "pharmacist")),
):
    organization_id, clinic_id = _tenant(user)
    result = get_prescription(prescription_id, organization_id=organization_id, clinic_id=clinic_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return result


@router.post("/{prescription_id}/cancel")
def cancel(
    prescription_id: str,
    user: dict[str, Any] = Depends(require_roles("admin", "doctor")),
):
    organization_id, clinic_id = _tenant(user)
    try:
        result = cancel_prescription(
            prescription_id,
            organization_id=organization_id,
            clinic_id=clinic_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Prescription not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_event(
        AuditEvent(
            action="prescription_cancelled",
            resource_type="prescription",
            resource_id=prescription_id,
            metadata={"status": result["status"]},
        ),
        user,
    )
    return result


@router.post("/{prescription_id}/dispense")
def dispense(
    prescription_id: str,
    user: dict[str, Any] = Depends(require_roles("admin", "pharmacist")),
):
    organization_id, clinic_id = _tenant(user)
    prescription = get_prescription(prescription_id, organization_id=organization_id, clinic_id=clinic_id)
    if prescription is None:
        raise HTTPException(status_code=404, detail="Prescription not found")
    # Durable ledger prevents retry paths from decrementing stock twice after allocation.
    try:
        from datetime import datetime, timezone
        from prescription_dispense_ledger import begin_or_get, claim_pending, record_allocated, finalize
        from prescription_pharmacy import dispense_prescription

        ledger = begin_or_get(
            prescription_id=prescription_id,
            organization_id=organization_id,
            clinic_id=clinic_id,
            patient_id=prescription["patient_id"],
        )

        if ledger["status"] == "completed":
            result = mark_prescription_dispensed(
                prescription_id,
                organization_id=organization_id,
                clinic_id=clinic_id,
            )
            allocation = {
                "prescription_id": prescription_id,
                "patient_id": prescription["patient_id"],
                "allocations": ledger["allocations"],
                "idempotent_replay": True,
            }
            return {"prescription": result, "dispensing": allocation}

        if ledger["status"] == "allocated":
            allocation = {
                "prescription_id": prescription_id,
                "patient_id": prescription["patient_id"],
                "allocations": ledger["allocations"],
            }
        else:
            if not claim_pending(
                prescription_id=prescription_id,
                organization_id=organization_id,
                clinic_id=clinic_id,
            ):
                raise ValueError("Prescription dispensing is already in progress; retry after the active request completes")
            allocation = dispense_prescription(
                prescription_id=prescription_id,
                organization_id=organization_id,
                clinic_id=clinic_id,
                patient_id=prescription["patient_id"],
                on=datetime.now(timezone.utc).isoformat(),
            )
            record_allocated(
                prescription_id=prescription_id,
                organization_id=organization_id,
                clinic_id=clinic_id,
                allocations=allocation["allocations"],
            )

        result = mark_prescription_dispensed(
            prescription_id,
            organization_id=organization_id,
            clinic_id=clinic_id,
        )
        finalize(
            prescription_id=prescription_id,
            organization_id=organization_id,
            clinic_id=clinic_id,
        )
    except (KeyError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    record_event(
        AuditEvent(
            action="prescription_dispensed",
            resource_type="prescription",
            resource_id=prescription_id,
            metadata={
                "patient_id": prescription["patient_id"],
                "allocation_count": len(allocation["allocations"]),
            },
        ),
        user,
    )
    return {"prescription": result, "dispensing": allocation}
