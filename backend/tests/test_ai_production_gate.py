import json
from pathlib import Path

from ai_release_evidence import _placeholder, validate_manifest_data, validate_manifest_file
from model_registry import production_artifact_eligible


def test_production_ai_is_not_eligible_without_approved_deployment():
    ok, reason = production_artifact_eligible(model_dir="/tmp/nonexistent-dermcareai-models", app_env="production")
    assert ok is False
    assert (
        "physician-final" in reason
        or "production AI deployment" in reason
        or "governance" in reason
    )


def test_full_template_is_not_valid():
    template_path = Path(__file__).resolve().parents[2] / "docs" / "ai-validation" / "release-manifest.template.json"
    ok, problems = validate_manifest_file(template_path)
    assert ok is False
    assert problems


def test_evidence_manifest_rejects_template_or_missing_clinical_evidence():
    template = {
        "schema_version": 2,
        "release_status": "not_ready",
        "research_only": True,
        "intended_use_statement": "Describe the exact intended clinical use, target population, workflow, exclusions and limitations using actual approved language.",
    }
    problems = validate_manifest_data(template)
    assert "release_status must be 'approved'" in problems
    assert "research_only must be false for a production clinical release" in problems
    assert "model: missing object" in problems


def test_validator_rejects_boolean_and_blank_evidence_values():
    manifest = {
        "schema_version": 2,
        "release_status": "approved",
        "research_only": False,
        "intended_use_statement": "Clinical decision support for the specified patient population with explicit exclusions and clinician review.",
        "model": {"name": "melanoma_binary", "version": "1.0.0", "artifact_sha256": "a" * 64},
        "dataset": {"name": "locked", "version": "1", "locked_test_set_manifest": "dataset.json", "manifest_sha256": "b" * 64, "provenance_ref": False, "inclusion_exclusion_ref": "criteria"},
        "metrics": {k: {"value": True, "ci95": [True, True]} for k in ("sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc")},
        "calibration": {"status": "completed", "method": " ", "result": "real", "evidence_ref": "calibration"},
        "subgroups": {"status": "completed", "evidence_ref": "subgroups"},
        "ood": {"status": "completed", "evidence_ref": "ood"},
        "abstention": {"status": "completed", "evidence_ref": "abstention"},
        "clinician_review": {"status": "completed", "evidence_ref": "review"},
        "external_validation": {"status": "completed", "evidence_ref": "external"},
        "approval": {"status": "completed", "approvers": [{"id": [], "role": "clinical", "approved_at": "2026-10-04T12:00:00Z", "record_ref": "r1", "record_sha256": "c" * 64}, {"id": "t1", "role": "technical", "approved_at": "2026-10-04T12:01:00Z", "record_ref": "r2", "record_sha256": "d" * 64}]},
        "governance": {"clinical_intended_use_review": {"status": "completed", "evidence_ref": "g1"}, "regulatory_assessment": {"status": "completed", "evidence_ref": "g2"}, "privacy_assessment": {"status": "completed", "evidence_ref": "g3"}},
        "deployment": {"status": "completed", "staging_evidence_ref": "s1", "rollback_evidence_ref": "rb1", "release_artifact_ref": "rel1"},
    }
    problems = validate_manifest_data(manifest)
    assert any("dataset.provenance_ref" in item for item in problems)
    assert any("metrics.sensitivity.value" in item for item in problems)
    assert any("calibration.method" in item for item in problems)
    assert any("approval.approvers[0].id" in item for item in problems)


def test_valid_looking_manifest_still_requires_real_artifact_when_requested(tmp_path):
    manifest = {
        "schema_version": 2,
        "release_status": "approved",
        "research_only": False,
        "intended_use_statement": "Clinical decision support for the specified patient population with explicit exclusions and clinician review.",
        "model": {"name": "melanoma_binary", "version": "1.0.0", "artifact_sha256": "a" * 64},
        "dataset": {"name": "locked", "version": "1", "locked_test_set_manifest": "dataset.json", "manifest_sha256": "b" * 64, "provenance_ref": "prov", "inclusion_exclusion_ref": "criteria"},
        "metrics": {k: {"value": 0.8, "ci95": [0.75, 0.85]} for k in ("sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc")},
        "calibration": {"status": "completed", "method": "bootstrap", "result": "completed", "evidence_ref": "calibration"},
        "subgroups": {"status": "completed", "evidence_ref": "subgroups"},
        "ood": {"status": "completed", "evidence_ref": "ood"},
        "abstention": {"status": "completed", "evidence_ref": "abstention"},
        "clinician_review": {"status": "completed", "evidence_ref": "review"},
        "external_validation": {"status": "completed", "evidence_ref": "external"},
        "approval": {"status": "completed", "approvers": [{"id": "c1", "role": "clinical", "approved_at": "2026-10-04T12:00:00Z", "record_ref": "r1", "record_sha256": "c" * 64}, {"id": "t1", "role": "technical", "approved_at": "2026-10-04T12:01:00Z", "record_ref": "r2", "record_sha256": "d" * 64}]},
        "governance": {"clinical_intended_use_review": {"status": "completed", "evidence_ref": "g1"}, "regulatory_assessment": {"status": "completed", "evidence_ref": "g2"}, "privacy_assessment": {"status": "completed", "evidence_ref": "g3"}},
        "deployment": {"status": "completed", "staging_evidence_ref": "s1", "rollback_evidence_ref": "rb1", "release_artifact_ref": "rel1"},
    }
    path = tmp_path / "release-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    ok, problems = validate_manifest_file(path, model_dir=tmp_path, require_artifact=True)
    assert ok is False
    assert any("model artifact is missing" in item for item in problems)


def test_placeholder_matching_rejects_only_complete_placeholder_values():
    assert _placeholder("METHOD")
    assert not _placeholder("isotonic regression method")
    assert not _placeholder("evidence/external-validation-results.json")


def test_requested_artifact_verification_requires_model_directory_and_mapping(tmp_path):
    missing_directory = validate_manifest_data({}, require_artifact=True)
    assert "model artifact verification requires model_dir" in missing_directory

    unmapped_model = validate_manifest_data(
        {"model": {"name": "custom_model"}},
        model_dir=tmp_path,
        require_artifact=True,
    )
    assert any("model artifact cannot be verified" in item for item in unmapped_model)
