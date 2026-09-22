from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = {
    "model": ["name", "version", "artifact_sha256"],
    "dataset": ["name", "version", "locked_test_set_manifest"],
    "metrics": ["sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc"],
    "calibration": ["method", "result"],
    "subgroups": ["status", "results"],
    "ood": ["status", "results"],
    "abstention": ["status", "results"],
    "clinician_review": ["status", "override_analysis"],
    "external_validation": ["status", "site_or_dataset"],
    "approval": ["status", "approved_by", "approved_at"],
}


def main(path: str) -> int:
    data = json.loads(Path(path).read_text())
    problems: list[str] = []

    for section, fields in REQUIRED.items():
        payload = data.get(section)
        if not isinstance(payload, dict):
            problems.append(f"{section}: missing object")
            continue
        for field in fields:
            value = payload.get(field)
            if value in (None, "", [], {}):
                problems.append(f"{section}.{field}: missing")

    if data.get("release_status") != "approved":
        problems.append("release_status must be 'approved'")

    if data.get("intended_use_statement") in (None, ""):
        problems.append("intended_use_statement: missing")

    if data.get("research_only") is True and data.get("release_status") == "approved":
        problems.append("research_only model cannot have an approved clinical release status")

    if problems:
        print("AI RELEASE EVIDENCE: FAIL")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("AI RELEASE EVIDENCE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/ai-validation/release-manifest.json"))
