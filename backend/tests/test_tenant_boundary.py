import pytest

from tenant_boundary import TenantBoundaryError, require_tenant_match


def test_tenant_boundary_accepts_exact_match():
    resource = {"organization_id": "org-a", "clinic_id": "clinic-a", "id": "R1"}
    assert require_tenant_match(resource, organization_id="org-a", clinic_id="clinic-a") == resource


def test_tenant_boundary_rejects_cross_organization():
    resource = {"organization_id": "org-b", "clinic_id": "clinic-a", "id": "R1"}
    with pytest.raises(TenantBoundaryError):
        require_tenant_match(resource, organization_id="org-a", clinic_id="clinic-a")


def test_tenant_boundary_rejects_cross_clinic():
    resource = {"organization_id": "org-a", "clinic_id": "clinic-b", "id": "R1"}
    with pytest.raises(TenantBoundaryError):
        require_tenant_match(resource, organization_id="org-a", clinic_id="clinic-a")
