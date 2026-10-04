from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PLACEHOLDERS = (
    "MODEL_NAME", "MODEL_VERSION", "64_HEX_SHA256", "LOCKED_TEST_SET_NAME",
    "DATASET_VERSION", "PATH_OR_DIGEST", "RESULT_WITH_CI", "METHOD", "RESULT",
    "ATTACHMENT_OR_TABLE", "INDEPENDENT_SITE_OR_DATASET", "ACCOUNTABLE_APPROVER",
    "ISO8601", "PLACEHOLDER",
)

MODEL_FILES = {
    "melanoma_binary": "melanoma_classifier.pth",
    "skin_lesion_7class": "FinetunedNasNetMobile.keras",
}

def _present(value: Any) -> bool:
    return value not in (None, '', [], {})

def _placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return any(token in value for token in PLACEHOLDERS)
    return False

def _iso8601(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def validate_manifest_data(data: dict[str, Any], *, model_dir: str | Path | None = None, require_artifact: bool = False) -> list[str]:
    problems: list[str] = []
    if data.get('schema_version') != 2: problems.append('schema_version must be 2')
    if data.get('release_status') != 'approved': problems.append("release_status must be 'approved'")
    if data.get('research_only') is not False: problems.append('research_only must be false for a production clinical release')
    intended = data.get('intended_use_statement')
    if not isinstance(intended, str) or len(intended.strip()) < 40 or _placeholder(intended):
        problems.append('intended_use_statement must be a completed, non-placeholder statement')

    model = data.get('model')
    if not isinstance(model, dict):
        problems.append('model: missing object')
    else:
        for field in ('name', 'version', 'artifact_sha256'):
            value = model.get(field)
            if not _present(value) or _placeholder(value): problems.append(f'model.{field}: missing or placeholder')
        if model.get('artifact_sha256') and not SHA256_RE.fullmatch(str(model['artifact_sha256'])):
            problems.append('model.artifact_sha256 must be a 64-character SHA-256 digest')

    dataset = data.get('dataset')
    if not isinstance(dataset, dict):
        problems.append('dataset: missing object')
    else:
        for field in ('name', 'version', 'locked_test_set_manifest', 'provenance_ref', 'inclusion_exclusion_ref'):
            value = dataset.get(field)
            if not _present(value) or _placeholder(value): problems.append(f'dataset.{field}: missing or placeholder')
        manifest_digest = dataset.get('manifest_sha256')
        if not isinstance(manifest_digest, str) or not SHA256_RE.fullmatch(manifest_digest):
            problems.append('dataset.manifest_sha256 must be a 64-character SHA-256 digest')

    metrics = data.get('metrics')
    required_metrics = ('sensitivity', 'specificity', 'ppv', 'npv', 'roc_auc', 'pr_auc')
    if not isinstance(metrics, dict):
        problems.append('metrics: missing object')
    else:
        for field in required_metrics:
            entry = metrics.get(field)
            if not isinstance(entry, dict):
                problems.append(f'metrics.{field}: must contain value and ci95'); continue
            value, ci = entry.get('value'), entry.get('ci95')
            if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
                problems.append(f'metrics.{field}.value must be numeric in [0,1]')
            if (not isinstance(ci, list) or len(ci) != 2 or not all(isinstance(item, (int, float)) for item in ci) or not 0 <= float(ci[0]) <= float(ci[1]) <= 1):
                problems.append(f'metrics.{field}.ci95 must be [low, high] within [0,1]')

    evidence_sections = ('calibration', 'subgroups', 'ood', 'abstention', 'clinician_review', 'external_validation')
    for section in evidence_sections:
        payload = data.get(section)
        if not isinstance(payload, dict): problems.append(f'{section}: missing object'); continue
        if payload.get('status') != 'completed': problems.append(f'{section}.status must be completed')
        if not _present(payload.get('evidence_ref')) or _placeholder(payload.get('evidence_ref')):
            problems.append(f'{section}.evidence_ref: missing or placeholder')

    approval = data.get('approval')
    if not isinstance(approval, dict):
        problems.append('approval: missing object')
    else:
        if approval.get('status') != 'completed': problems.append('approval.status must be completed')
        approvers = approval.get('approvers')
        if not isinstance(approvers, list) or len(approvers) < 2: problems.append('approval.approvers requires at least two accountable approvers')
        else:
            ids, roles = set(), set()
            for index, approver in enumerate(approvers):
                if not isinstance(approver, dict): problems.append(f'approval.approvers[{index}] must be an object'); continue
                for field in ('id', 'role', 'approved_at', 'record_ref', 'record_sha256'):
                    if not _present(approver.get(field)) or _placeholder(approver.get(field)): problems.append(f'approval.approvers[{index}].{field}: missing or placeholder')
                ids.add(approver.get('id')); roles.add(approver.get('role'))
                if approver.get('approved_at') and not _iso8601(approver.get('approved_at')): problems.append(f'approval.approvers[{index}].approved_at must be ISO-8601')
                if approver.get('record_sha256') and not SHA256_RE.fullmatch(str(approver['record_sha256'])): problems.append(f'approval.approvers[{index}].record_sha256 must be a SHA-256 digest')
            if len(ids) < 2: problems.append('approval.approvers must identify two distinct accountable people')
            if len(roles) < 2: problems.append('approval.approvers must include two distinct accountability roles')

    governance = data.get('governance')
    if not isinstance(governance, dict): problems.append('governance: missing object')
    else:
        for field in ('clinical_intended_use_review', 'regulatory_assessment', 'privacy_assessment'):
            payload = governance.get(field)
            if not isinstance(payload, dict): problems.append(f'governance.{field}: missing object'); continue
            if payload.get('status') != 'completed': problems.append(f'governance.{field}.status must be completed')
            if not _present(payload.get('evidence_ref')) or _placeholder(payload.get('evidence_ref')): problems.append(f'governance.{field}.evidence_ref: missing or placeholder')

    deployment = data.get('deployment')
    if not isinstance(deployment, dict): problems.append('deployment: missing object')
    else:
        if deployment.get('status') != 'completed': problems.append('deployment.status must be completed')
        for field in ('staging_evidence_ref', 'rollback_evidence_ref', 'release_artifact_ref'):
            if not _present(deployment.get(field)) or _placeholder(deployment.get(field)): problems.append(f'deployment.{field}: missing or placeholder')

    if model_dir is not None and isinstance(model, dict) and _present(model.get('name')):
        file_name = MODEL_FILES.get(str(model['name']))
        if file_name:
            artifact_path = Path(model_dir) / file_name
            if not artifact_path.is_file():
                if require_artifact: problems.append(f'model artifact is missing at {artifact_path}')
            elif sha256_file(artifact_path).lower() != str(model.get('artifact_sha256', '')).lower():
                problems.append('model artifact SHA-256 does not match manifest')
    return problems

def validate_manifest_file(path: str | Path, *, model_dir: str | Path | None = None, require_artifact: bool = False) -> tuple[bool, list[str]]:
    manifest_path = Path(path)
    if not manifest_path.is_file(): return False, [f'evidence manifest is missing: {manifest_path}']
    try: data = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc: return False, [f'evidence manifest is unreadable: {exc}']
    if not isinstance(data, dict): return False, ['evidence manifest root must be a JSON object']
    problems = validate_manifest_data(data, model_dir=model_dir, require_artifact=require_artifact)
    return not problems, problems
