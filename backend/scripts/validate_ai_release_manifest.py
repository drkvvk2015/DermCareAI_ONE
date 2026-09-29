from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
REVISION_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
PLACEHOLDER_RE = re.compile(
    r"(?:placeholder|todo|tbd|not provided|result_with_ci|path_or_digest|"
    r"attachment_or_table|accountable_approver|independent_site_or_dataset|"
    r"64_hex_sha256|model_name|model_version|dataset_name|dataset_version)",
    re.IGNORECASE,
)
METRICS = ("sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc")
COMPLETION_SECTIONS = (
    "calibration",
    "subgroups",
    "ood",
    "abstention",
    "clinician_review",
    "external_validation",
    "approval",
    "deployment",
)
STATUS_VALUES = {"completed", "not_assessed", "not_available"}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER_RE.search(value)


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _revision(value: Any) -> bool:
    return isinstance(value, str) and REVISION_RE.fullmatch(value) is not None


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_manifest(data: Any) -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["manifest: expected an object"]

    def required_string(section: dict[str, Any], name: str, path: str) -> None:
        if not _nonempty_string(section.get(name)):
            problems.append(f"{path}.{name}: missing or placeholder")

    def required_hash(section: dict[str, Any], name: str, path: str) -> None:
        if not _sha256(section.get(name)):
            problems.append(f"{path}.{name}: expected a 64-character SHA-256 digest")

    def require_object(name: str) -> dict[str, Any]:
        value = data.get(name)
        if not isinstance(value, dict):
            problems.append(f"{name}: expected an object")
            return {}
        return value

    if data.get("schema_version") != "1.0":
        problems.append("schema_version: expected '1.0'")
    required_string(data, "manifest_id", "manifest")
    try:
        created_at = datetime.fromisoformat(str(data.get("created_at", "")).replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            raise ValueError
    except ValueError:
        problems.append("created_at: expected an ISO-8601 timestamp with timezone")
    release_status = data.get("release_status")
    if not isinstance(release_status, str) or release_status not in {"approved", "not_ready"}:
        problems.append("release_status: expected 'approved' or 'not_ready'")
    if not isinstance(data.get("research_only"), bool):
        problems.append("research_only: expected a boolean")
    required_string(data, "intended_use_statement", "manifest")

    if data.get("release_status") != "approved":
        problems.append("release_status must be 'approved'")
    if data.get("research_only") is True and data.get("release_status") == "approved":
        problems.append("research_only model cannot have an approved clinical release status")

    reproducibility = require_object("reproducibility")
    if not _revision(reproducibility.get("evaluation_code_revision")):
        problems.append("reproducibility.evaluation_code_revision: expected a 40- or 64-character commit")
    required_string(reproducibility, "environment", "reproducibility")
    required_hash(reproducibility, "dependency_lock_sha256", "reproducibility")
    seed = reproducibility.get("random_seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        problems.append("reproducibility.random_seed: expected a non-negative integer")
    required_string(reproducibility, "protocol_version", "reproducibility")

    model = require_object("model")
    for field in ("name", "version", "source_repository", "training_data_manifest"):
        required_string(model, field, "model")
    required_hash(model, "artifact_sha256", "model")
    required_hash(model, "training_data_manifest_sha256", "model")
    if not _revision(model.get("source_revision")):
        problems.append("model.source_revision: expected a 40- or 64-character commit")

    dataset = require_object("dataset")
    for field in (
        "name",
        "version",
        "locked_test_set_manifest",
        "source",
        "inclusion_exclusion_criteria",
        "split",
    ):
        required_string(dataset, field, "dataset")
    required_hash(dataset, "manifest_sha256", "dataset")
    count = dataset.get("sample_count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        problems.append("dataset.sample_count: expected a positive integer")
    prevalence = dataset.get("intended_population_prevalence")
    if not _number(prevalence) or not 0 < prevalence < 1:
        problems.append("dataset.intended_population_prevalence: expected a number between 0 and 1")

    metrics = require_object("metrics")
    for name in METRICS:
        metric = metrics.get(name)
        if not isinstance(metric, dict):
            problems.append(f"metrics.{name}: expected an object")
            continue
        value = metric.get("value")
        lower = metric.get("ci95_lower")
        upper = metric.get("ci95_upper")
        if not all(_number(part) and 0 <= part <= 1 for part in (value, lower, upper)):
            problems.append(f"metrics.{name}: value and 95% confidence bounds must be between 0 and 1")
        elif lower > value or value > upper:
            problems.append(f"metrics.{name}: value must fall within its confidence interval")
        required_string(metric, "evidence", f"metrics.{name}")

    for section_name, fields in {
        "calibration": ("method", "result", "evidence"),
        "subgroups": ("results", "evidence"),
        "ood": ("results", "evidence"),
        "abstention": ("results", "evidence"),
        "clinician_review": ("override_analysis", "evidence"),
        "external_validation": ("site_or_dataset", "results", "evidence"),
        "approval": ("approved_by", "approved_at", "decision_id", "audit_record"),
        "deployment": ("rollback_plan", "evidence"),
    }.items():
        section = require_object(section_name)
        status = section.get("status")
        if not isinstance(status, str) or status not in STATUS_VALUES:
            problems.append(f"{section_name}.status: expected completed, not_assessed, or not_available")
        for field in fields:
            required_string(section, field, section_name)
        if section_name == "clinician_review":
            reviewers = section.get("reviewer_count")
            if not isinstance(reviewers, int) or isinstance(reviewers, bool) or reviewers <= 0:
                problems.append("clinician_review.reviewer_count: expected a positive integer")
        if section_name == "external_validation" and section.get("independent") is not True:
            problems.append("external_validation.independent: must be true")
        if section_name == "approval":
            try:
                approved_at = datetime.fromisoformat(
                    str(section.get("approved_at", "")).replace("Z", "+00:00")
                )
                if approved_at.tzinfo is None:
                    raise ValueError
            except ValueError:
                problems.append("approval.approved_at: expected an ISO-8601 timestamp with timezone")

    for section_name in COMPLETION_SECTIONS:
        section = data.get(section_name)
        if isinstance(section, dict) and section.get("status") != "completed":
            problems.append(f"{section_name}.status must be 'completed' for an approved release")

    if isinstance(data.get("approval"), dict) and data["approval"].get("status") == "completed":
        if data.get("release_status") != "approved":
            problems.append("approval cannot be completed while release_status is not 'approved'")

    return problems


def validate_file(path: str) -> list[str]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"manifest: unable to read valid JSON ({exc})"]
    return _validate_manifest(data)


def main(path: str) -> int:
    problems = validate_file(path)
    if problems:
        print("AI RELEASE EVIDENCE: FAIL")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("AI RELEASE EVIDENCE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/ai-validation/release-manifest.json"))
