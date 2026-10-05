"""Structural checks for the evidence package required to enable clinical AI."""
from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PLACEHOLDER_PARTS = (
    "placeholder",
    "todo",
    "replace with",
    "result_with_ci",
    "attachment_or_table",
    "site_or_dataset",
    "accountable_approver",
    "64_hex_sha256",
    "model_name",
    "model_version",
    "path_or_digest",
    "protocol_id",
)


def _text(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    lowered = value.lower()
    return not any(part in lowered for part in PLACEHOLDER_PARTS)


def _datetime(value: Any) -> bool:
    if not _text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _evidence_ref(value: Any, label: str, problems: list[str]) -> None:
    if not isinstance(value, dict):
        problems.append(f"{label}: evidence reference must be an object")
        return
    if not _text(value.get("uri")):
        problems.append(f"{label}.uri: secure evidence location is required")
    if not _sha256(value.get("sha256")):
        problems.append(f"{label}.sha256: a 64-character SHA-256 digest is required")


def validate_ai_release_manifest(
    manifest: Any,
    *,
    expected_model_name: str | None = None,
    expected_model_version: str | None = None,
    expected_artifact_sha256: str | None = None,
) -> list[str]:
    """Validate the structure and identity of a clinical AI evidence package.

    This only checks completeness and integrity references. It cannot establish
    that the evidence is scientifically sound or that reviewers are accountable.
    """
    problems: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]

    if manifest.get("release_status") != "approved":
        problems.append("release_status must be 'approved'")
    if manifest.get("research_only") is not False:
        problems.append("research_only must be false for a clinical release")
    if not _text(manifest.get("intended_use_statement")):
        problems.append("intended_use_statement is required")

    model = manifest.get("model")
    if not isinstance(model, dict):
        model = {}
        problems.append("model must be an object")
    for field in ("name", "version"):
        if not _text(model.get(field)):
            problems.append(f"model.{field} is required")
    artifact_sha = model.get("artifact_sha256")
    if not _sha256(artifact_sha):
        problems.append("model.artifact_sha256 must be a 64-character SHA-256 digest")
    if expected_model_name and model.get("name") != expected_model_name:
        problems.append("manifest model.name does not match the active production model")
    if expected_model_version and model.get("version") != expected_model_version:
        problems.append("manifest model.version does not match the active production model")
    if expected_artifact_sha256 and str(artifact_sha).lower() != expected_artifact_sha256.lower():
        problems.append("manifest artifact SHA-256 does not match the active production model")

    dataset = manifest.get("dataset")
    if not isinstance(dataset, dict):
        dataset = {}
        problems.append("dataset must be an object")
    for field in ("name", "version"):
        if not _text(dataset.get(field)):
            problems.append(f"dataset.{field} is required")
    dataset_manifest = dataset.get("locked_test_set_manifest")
    if not isinstance(dataset_manifest, dict):
        dataset_manifest = {}
        problems.append("dataset.locked_test_set_manifest must be an object")
    if not _text(dataset_manifest.get("uri")):
        problems.append("dataset locked manifest URI is required")
    if not _sha256(dataset_manifest.get("sha256")):
        problems.append("dataset locked manifest SHA-256 is required")
    if not _datetime(dataset_manifest.get("frozen_at")):
        problems.append("dataset locked manifest frozen_at must be an ISO 8601 timestamp with timezone")

    metrics = manifest.get("metrics")
    metric_names = ("sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc")
    if not isinstance(metrics, dict):
        metrics = {}
        problems.append("metrics must be an object")
    for name in metric_names:
        metric = metrics.get(name)
        if not isinstance(metric, dict):
            problems.append(f"metrics.{name} must include an estimate, 95% CI, and sample count")
            continue
        estimate = metric.get("estimate")
        interval = metric.get("ci95")
        sample_count = metric.get("sample_count")
        if not _number(estimate) or not 0 <= estimate <= 1:
            problems.append(f"metrics.{name}.estimate must be a number in [0, 1]")
        if not isinstance(interval, dict):
            problems.append(f"metrics.{name}.ci95 must include lower and upper bounds")
        else:
            lower, upper = interval.get("lower"), interval.get("upper")
            if not _number(lower) or not _number(upper) or not 0 <= lower <= upper <= 1:
                problems.append(f"metrics.{name}.ci95 bounds must be ordered numbers in [0, 1]")
            elif _number(estimate) and not lower <= estimate <= upper:
                problems.append(f"metrics.{name}.estimate must fall within its 95% CI")
        if not isinstance(sample_count, int) or isinstance(sample_count, bool) or sample_count < 1:
            problems.append(f"metrics.{name}.sample_count must be a positive integer")

    calibration = manifest.get("calibration")
    if not isinstance(calibration, dict):
        calibration = {}
        problems.append("calibration must be an object")
    if not _text(calibration.get("method")):
        problems.append("calibration.method is required")
    for field in ("expected_calibration_error", "brier_score"):
        value = calibration.get(field)
        if not _number(value) or not 0 <= value <= 1:
            problems.append(f"calibration.{field} must be a number in [0, 1]")
    _evidence_ref(calibration.get("evidence"), "calibration.evidence", problems)

    for section in ("subgroups", "ood", "abstention", "clinician_review"):
        payload = manifest.get(section)
        if not isinstance(payload, dict):
            problems.append(f"{section} must be an object")
            continue
        if payload.get("status") != "completed":
            problems.append(f"{section}.status must be 'completed'")
        _evidence_ref(payload.get("evidence"), f"{section}.evidence", problems)

    external = manifest.get("external_validation")
    if not isinstance(external, dict):
        external = {}
        problems.append("external_validation must be an object")
    if external.get("status") != "completed":
        problems.append("external_validation.status must be 'completed'")
    for field in ("site_or_dataset", "independent_reviewer"):
        if not _text(external.get(field)):
            problems.append(f"external_validation.{field} is required")
    _evidence_ref(external.get("evidence"), "external_validation.evidence", problems)

    prospective = manifest.get("prospective_evaluation")
    if not isinstance(prospective, dict):
        prospective = {}
        problems.append("prospective_evaluation must be an object")
    if prospective.get("status") != "completed":
        problems.append("prospective_evaluation.status must be 'completed'")
    for field in ("protocol_id", "site_or_cohort"):
        if not _text(prospective.get(field)):
            problems.append(f"prospective_evaluation.{field} is required")
    _evidence_ref(prospective.get("evidence"), "prospective_evaluation.evidence", problems)

    approval = manifest.get("approval")
    if not isinstance(approval, dict):
        approval = {}
        problems.append("approval must be an object")
    if approval.get("status") != "approved":
        problems.append("approval.status must be 'approved'")
    if not _text(approval.get("approved_by")):
        problems.append("approval.approved_by is required")
    if not _datetime(approval.get("approved_at")):
        problems.append("approval.approved_at must be an ISO 8601 timestamp with timezone")
    if _text(approval.get("approved_by")) and approval.get("approved_by") == external.get("independent_reviewer"):
        problems.append("the accountable approver must differ from the independent external reviewer")
    _evidence_ref(approval.get("evidence"), "approval.evidence", problems)

    return problems
