from __future__ import annotations

from typing import Any

from commerce_store import atomic_fefo_dispense
from prescription_store import get_prescription


def dispense_prescription(*, prescription_id: str, organization_id: str, clinic_id: str, patient_id: str, on: str) -> dict[str, Any]:
    """Validate a tenant/patient-scoped active prescription and atomically allocate its medicines FEFO.

    This service deliberately performs no prescribing or clinical decision-making. It only
    enforces the prescription-to-dispensing boundary before invoking the existing atomic
    pharmacy allocator.
    """
    prescription = get_prescription(
        prescription_id,
        organization_id=organization_id,
        clinic_id=clinic_id,
    )
    if prescription is None:
        raise KeyError(prescription_id)
    if prescription.get("patient_id") != patient_id:
        raise PermissionError("Prescription patient does not match dispensing patient")
    if prescription.get("status") != "active":
        raise ValueError("Only active prescriptions can be dispensed")

    required: dict[str, float] = {}
    for item in prescription.get("items", []):
        medicine_id = str(item.get("medicine_id", "")).strip()
        if not medicine_id:
            raise ValueError("Prescription item is missing medicine_id")
        quantity = float(item.get("quantity", 0))
        if quantity <= 0:
            raise ValueError("Prescription quantity must be positive")
        required[medicine_id] = required.get(medicine_id, 0.0) + quantity

    allocations = atomic_fefo_dispense(required, on=on, organization_id=organization_id, clinic_id=clinic_id)
    return {"prescription_id": prescription_id, "patient_id": patient_id, "allocations": allocations}
