from __future__ import annotations
from collections import Counter
from typing import Iterable, Mapping

def diagnosis_counts(values: Iterable[str]) -> dict[str, int]:
    counts = Counter(value.strip() for value in values if value and value.strip())
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

def followup_completion_rate(statuses: Iterable[str]) -> float:
    normalized = [status.strip().lower() for status in statuses if status and status.strip()]
    if not normalized:
        return 0.0
    completed = sum(status == "completed" for status in normalized)
    return round(completed / len(normalized) * 100.0, 2)

def cohort_summary(records: Iterable[Mapping[str, object]]) -> dict[str, object]:
    records_list = list(records)
    return {
        "encounters": len(records_list),
        "diagnoses": diagnosis_counts(str(record.get("diagnosis","")) for record in records_list),
        "followup_completion_rate": followup_completion_rate(
            str(record.get("followup_status","")) for record in records_list
        ),
    }
