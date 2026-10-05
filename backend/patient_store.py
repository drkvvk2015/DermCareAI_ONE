from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

try:
    import firebase_admin
    from firebase_admin import firestore
except ImportError:  # pragma: no cover
    firebase_admin = None
    firestore = None

try:
    from google.api_core import exceptions as _gexc
except ImportError:  # pragma: no cover
    _gexc = None

logger = logging.getLogger(__name__)

PATIENTS_COLLECTION = "patients"
DOCTORS_COLLECTION = "doctors"


class PatientStoreUnavailable(RuntimeError):
    """Firebase Admin or Firestore is not configured or not reachable."""


class ActiveDoctorRequired(PermissionError):
    """The calling doctor has no active doctors/{uid} record."""


def _client():
    if firebase_admin is None or firestore is None:
        raise PatientStoreUnavailable("Firebase Admin SDK is not available")
    try:
        # The app is initialized by auth.get_current_user before any route reaches this store.
        app = firebase_admin.get_app()
    except ValueError as exc:
        raise PatientStoreUnavailable("Firebase Admin app is not initialized") from exc
    try:
        return firestore.client(app=app)
    except Exception as exc:
        raise PatientStoreUnavailable("Firestore client is not configured") from exc


def _patient_id(organization_id: str, clinic_id: str, doctor_id: str, operation_key: str) -> str:
    # Deterministic so a retry after a partial failure converges on the same document.
    raw = "\x00".join((organization_id, clinic_id, doctor_id, operation_key.strip()))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def create_patient(
    *,
    organization_id: str,
    clinic_id: str,
    doctor_id: str,
    patient: dict[str, Any],
    operation_key: str,
    require_active_doctor: bool,
) -> str:
    """Write a patient to the existing Firestore `patients` collection and return its ID."""
    client = _client()
    patient_id = _patient_id(organization_id, clinic_id, doctor_id, operation_key)
    document = {
        "name": patient["name"],
        "age": patient["age"],
        "gender": patient["gender"],
        "phone": patient["phone"],
        "email": patient["email"],
        "address": patient["address"],
        "medicalHistory": patient["medicalHistory"],
        "allergies": patient["allergies"],
        "currentMedications": patient["currentMedications"],
        "organizationId": organization_id,
        "clinicId": clinic_id,
        "doctorId": doctor_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "upcomingVisit": None,
    }
    try:
        if require_active_doctor:
            snapshot = client.collection(DOCTORS_COLLECTION).document(doctor_id).get()
            record = snapshot.to_dict() if snapshot.exists else None
            if not record or record.get("status") != "active":
                raise ActiveDoctorRequired("An active doctor record is required")
        try:
            client.collection(PATIENTS_COLLECTION).document(patient_id).create(document)
        except Exception as exc:
            if _gexc is None or not isinstance(exc, _gexc.AlreadyExists):
                raise
    except ActiveDoctorRequired:
        raise
    except Exception as exc:
        logger.error("Patient registry write failed: %s", type(exc).__name__)
        raise PatientStoreUnavailable("Patient registry is unavailable") from exc
    return patient_id
