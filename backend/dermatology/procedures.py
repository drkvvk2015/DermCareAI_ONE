from __future__ import annotations

from dataclasses import dataclass

from typing import Final


SUPPORTED_PROCEDURES: Final[tuple[str, ...]] = (
    "biopsy", "cryotherapy", "electrocautery", "laser", "dermoscopy",
)

@dataclass(frozen=True)
class ProcedureRecord:
    procedure_type: str
    body_site: str
    indication: str
    consent_id: str
    performed_by: str
    performed_at: str
    outcome: str | None = None

def validate_procedure(record: ProcedureRecord) -> None:
    if record.procedure_type not in SUPPORTED_PROCEDURES:
        raise ValueError(f"Unsupported dermatology procedure: {record.procedure_type}")
    for field_name in ("body_site","indication","consent_id","performed_by","performed_at"):
        if not getattr(record, field_name).strip():
            raise ValueError(f"{field_name} is required")
