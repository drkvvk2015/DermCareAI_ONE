from __future__ import annotations

from typing import Any


class TenantBoundaryError(PermissionError):
    """Raised when a resource crosses an organization/clinic tenant boundary."""


def require_tenant_match(
    resource: dict[str, Any] | None,
    *,
    organization_id: str,
    clinic_id: str,
    resource_name: str = "resource",
) -> dict[str, Any]:
    """Return a resource only when both organization and clinic match exactly."""
    if resource is None:
        raise KeyError(resource_name)
    if str(resource.get("organization_id")) != str(organization_id):
        raise TenantBoundaryError(f"{resource_name} belongs to another organization")
    if str(resource.get("clinic_id")) != str(clinic_id):
        raise TenantBoundaryError(f"{resource_name} belongs to another clinic")
    return resource
