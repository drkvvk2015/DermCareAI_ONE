from __future__ import annotations


def test_dermatology_tenant_boundary_contract_is_explicit():
    """Document the resource-level isolation contract enforced by the API/store layer."""
    resources = {
        "encounter": {"organization_id", "clinic_id", "patient_id"},
        "lesion": {"organization_id", "clinic_id", "patient_id"},
        "media": {"organization_id", "clinic_id", "patient_id", "encounter_id"},
        "ai_review": {"organization_id", "clinic_id", "patient_id", "encounter_id"},
        "prescription": {"organization_id", "clinic_id", "patient_id", "encounter_id"},
        "pharmacy": {"organization_id", "clinic_id"},
        "invoice": {"organization_id", "clinic_id"},
        "followup": {"organization_id", "clinic_id", "patient_id", "encounter_id"},
    }
    for resource, required_scope in resources.items():
        assert {"organization_id", "clinic_id"}.issubset(required_scope), resource
