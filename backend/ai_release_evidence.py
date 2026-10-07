"""Clinical AI evidence-package validation and controlled artifact checks."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PLACEHOLDER_VALUES = {
    "MODEL_NAME", "MODEL_VERSION", "64_HEX_SHA256", "LOCKED_TEST_SET_NAME",
    "DATASET_VERSION", "PATH_OR_DIGEST", "RESULT_WITH_CI", "METHOD", "RESULT",
    "ATTACHMENT_OR_TABLE", "INDEPENDENT_SITE_OR_DATASET", "ACCOUNTABLE_APPROVER",
    "ACCOUNTABLE_ID", "ACCOUNTABLE_ID_2", "APPROVAL_RECORD", "EVIDENCE_REFERENCE",
    "ISO8601", "PLACEHOLDER",
    "Describe the exact intended clinical use, target population, workflow, exclusions and limitations using actual approved language.",
}
MODEL_FILES = {
    "melanoma_binary": "melanoma_classifier.pth",
    "skin_lesion_7class": "FinetunedNasNetMobile.keras",
}


def _placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    return not normalized or normalized in PLACEHOLDER_VALUES


def _required_string(value: Any, field: str, problems: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip() or _placeholder(value):
        problems.append(f"{field}: missing, blank, non-string, or placeholder")
        return None
    return value.strip()


def _finite_unit_interval(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and 0 <= float(value) <= 1


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.strip()))


def _iso8601(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest_data(data: dict[str, Any], *, model_dir: str | Path | None = None, require_artifact: bool = False) -> list[str]:
    problems: list[str] = []
    if data.get("schema_version") != 2:
        problems.append("schema_version must be 2")
    if data.get("release_status") != "approved":
        problems.append("release_status must be 'approved'")
    if data.get("research_only") is not False:
        problems.append("research_only must be false for a production clinical release")
    _required_string(data.get("intended_use_statement"), "intended_use_statement", problems)

    model = data.get("model")
    if not isinstance(model, dict):
        problems.append("model: missing object")
        model = {}
    _required_string(model.get("name"), "model.name", problems)
    _required_string(model.get("version"), "model.version", problems)
    artifact_hash = _required_string(model.get("artifact_sha256"), "model.artifact_sha256", problems)
    if artifact_hash and not _valid_sha256(artifact_hash):
        problems.append("model.artifact_sha256 must be a 64-character SHA-256 digest")

    dataset = data.get("dataset")
    if not isinstance(dataset, dict):
        problems.append("dataset: missing object")
        dataset = {}
    for field in ("name", "version", "locked_test_set_manifest", "provenance_ref", "inclusion_exclusion_ref"):
        _required_string(dataset.get(field), f"dataset.{field}", problems)
    manifest_digest = _required_string(dataset.get("manifest_sha256"), "dataset.manifest_sha256", problems)
    if manifest_digest and not _valid_sha256(manifest_digest):
        problems.append("dataset.manifest_sha256 must be a 64-character SHA-256 digest")

    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        problems.append("metrics: missing object")
        metrics = {}
    for field in ("sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc"):
        entry = metrics.get(field)
        if not isinstance(entry, dict):
            problems.append(f"metrics.{field}: must contain value and ci95")
            continue
        if not _finite_unit_interval(entry.get("value")):
            problems.append(f"metrics.{field}.value must be numeric in [0,1]")
        ci = entry.get("ci95")
        if not isinstance(ci, list) or len(ci) != 2 or not all(_finite_unit_interval(v) for v in ci) or float(ci[0]) > float(ci[1]):
            problems.append(f"metrics.{field}.ci95 must be [low, high] within [0,1]")

    calibration = data.get("calibration")
    if not isinstance(calibration, dict):
        problems.append("calibration: missing object")
        calibration = {}
    _required_string(calibration.get("method"), "calibration.method", problems)
    _required_string(calibration.get("result"), "calibration.result", problems)
    _required_string(calibration.get("evidence_ref"), "calibration.evidence_ref", problems)
    if calibration.get("status") != "completed":
        problems.append("calibration.status must be completed")

    for section in ("subgroups", "ood", "abstention", "clinician_review", "external_validation"):
        payload = data.get(section)
        if not isinstance(payload, dict):
            problems.append(f"{section}: missing object")
            continue
        if payload.get("status") != "completed":
            problems.append(f"{section}.status must be completed")
        _required_string(payload.get("evidence_ref"), f"{section}.evidence_ref", problems)

    approval = data.get("approval")
    if not isinstance(approval, dict):
        problems.append("approval: missing object")
        approval = {}
    if approval.get("status") != "completed":
        problems.append("approval.status must be completed")
    approvers = approval.get("approvers")
    if not isinstance(approvers, list) or len(approvers) < 2:
        problems.append("approval.approvers requires at least two accountable approvers")
    else:
        ids: set[str] = set(); roles: set[str] = set()
        for index, approver in enumerate(approvers):
            if not isinstance(approver, dict):
                problems.append(f"approval.approvers[{index}] must be an object"); continue
            approver_id = _required_string(approver.get("id"), f"approval.approvers[{index}].id", problems)
            role = _required_string(approver.get("role"), f"approval.approvers[{index}].role", problems)
            _required_string(approver.get("record_ref"), f"approval.approvers[{index}].record_ref", problems)
            record_hash = _required_string(approver.get("record_sha256"), f"approval.approvers[{index}].record_sha256", problems)
            if not approver.get("approved_at") or not _iso8601(approver.get("approved_at")):
                problems.append(f"approval.approvers[{index}].approved_at must be ISO-8601")
            if record_hash and not _valid_sha256(record_hash):
                problems.append(f"approval.approvers[{index}].record_sha256 must be a SHA-256 digest")
            if approver_id is not None: ids.add(approver_id)
            if role is not None: roles.add(role)
        if len(ids) < 2: problems.append("approval.approvers must identify two distinct accountable people")
        if len(roles) < 2: problems.append("approval.approvers must include two distinct accountability roles")

    governance = data.get("governance")
    if not isinstance(governance, dict):
        problems.append("governance: missing object"); governance = {}
    for field in ("clinical_intended_use_review", "regulatory_assessment", "privacy_assessment"):
        payload = governance.get(field)
        if not isinstance(payload, dict):
            problems.append(f"governance.{field}: missing object"); continue
        if payload.get("status") != "completed": problems.append(f"governance.{field}.status must be completed")
        _required_string(payload.get("evidence_ref"), f"governance.{field}.evidence_ref", problems)

    deployment = data.get("deployment")
    if not isinstance(deployment, dict):
        problems.append("deployment: missing object"); deployment = {}
    if deployment.get("status") != "completed": problems.append("deployment.status must be completed")
    for field in ("staging_evidence_ref", "rollback_evidence_ref", "release_artifact_ref"):
        _required_string(deployment.get(field), f"deployment.{field}", problems)

    if require_artifact:
        if model_dir is None:
            problems.append("model artifact verification requires model_dir")
        else:
            model_name = model.get("name")
            file_name = MODEL_FILES.get(model_name) if isinstance(model_name, str) else None
            if not file_name:
                problems.append("model artifact cannot be verified because model.name is not mapped to a controlled artifact")
            else:
                artifact_path = Path(model_dir) / file_name
                if not artifact_path.is_file():
                    problems.append(f"model artifact is missing at {artifact_path}")
                elif sha256_file(artifact_path).lower() != str(model.get("artifact_sha256", "")).lower():
                    problems.append("model artifact SHA-256 does not match manifest")
    return problems


def validate_manifest_file(path: str | Path, *, model_dir: str | Path | None = None, require_artifact: bool = False) -> tuple[bool, list[str]]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return False, [f"evidence manifest is unreadable: {exc}"]
    if not isinstance(data, dict):
        return False, ["evidence manifest root must be a JSON object"]
    problems = validate_manifest_data(data, model_dir=model_dir, require_artifact=require_artifact)
    return not problems, problems


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not _placeholder(value)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _evidence_ref(value: Any, label: str, problems: list[str]) -> None:
    if not isinstance(value, dict):
        problems.append(f"{label}: evidence reference must be an object"); return
    if not _text(value.get("uri")): problems.append(f"{label}.uri: secure evidence location is required")
    if not _valid_sha256(value.get("sha256")): problems.append(f"{label}.sha256: a 64-character SHA-256 digest is required")


def validate_ai_release_manifest(
    manifest: Any,
    *,
    expected_model_name: str | None = None,
    expected_model_version: str | None = None,
    expected_artifact_sha256: str | None = None,
) -> list[str]:
    """Compatibility entry point backed by the single strict schema-v2 validator."""
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]
    problems = validate_manifest_data(manifest)
    model = manifest.get("model") if isinstance(manifest.get("model"), dict) else {}
    if expected_model_name and model.get("name") != expected_model_name:
        problems.append("manifest model.name does not match the active production model")
    if expected_model_version and model.get("version") != expected_model_version:
        problems.append("manifest model.version does not match the active production model")
    artifact_sha = model.get("artifact_sha256")
    if expected_artifact_sha256 and str(artifact_sha).lower() != expected_artifact_sha256.lower():
        problems.append("manifest artifact SHA-256 does not match the active production model")
    return problems
