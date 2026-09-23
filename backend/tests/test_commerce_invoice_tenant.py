from commerce_store import get_invoice, reset_store, save_invoice


def setup_function() -> None:
    reset_store()


def _invoice() -> dict[str, object]:
    return {
        "id": "INV-TENANT-1",
        "patient_id": "patient-1",
        "organization_id": "org-1",
        "clinic_id": "clinic-1",
        "items": [],
        "subtotal": "100.00",
        "tax": "0.00",
        "discount": "0.00",
        "total": "100.00",
        "currency": "INR",
        "status": "unpaid",
        "created_at": "2026-09-23T00:00:00+00:00",
    }


def test_invoice_is_hidden_from_other_tenant() -> None:
    save_invoice(_invoice(), organization_id="org-1", clinic_id="clinic-1")

    assert get_invoice("INV-TENANT-1", organization_id="org-1", clinic_id="clinic-1") is not None
    assert get_invoice("INV-TENANT-1", organization_id="org-1", clinic_id="clinic-2") is None
    assert get_invoice("INV-TENANT-1", organization_id="org-2", clinic_id="clinic-1") is None


def test_invoice_payload_preserves_tenant_identity() -> None:
    save_invoice(_invoice(), organization_id="org-1", clinic_id="clinic-1")
    invoice = get_invoice("INV-TENANT-1", organization_id="org-1", clinic_id="clinic-1")
    assert invoice is not None
    assert invoice["organization_id"] == "org-1"
    assert invoice["clinic_id"] == "clinic-1"
