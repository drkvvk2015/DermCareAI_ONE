import json
from pathlib import Path

from ai_release_evidence import validate_manifest_data, validate_manifest_file
from model_registry import production_artifact_eligible
from scripts.production_preflight import evaluate_environment


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


def test_production_preflight_uses_release_manifest_path():
    template_path = Path(__file__).resolve().parents[2] / "docs" / "ai-validation" / "release-manifest.template.json"
    results = evaluate_environment(
        {
            "APP_ENV": "production",
            "AI_ENABLED_IN_PRODUCTION": "true",
            "AI_RELEASE_MANIFEST_PATH": str(template_path),
        }
    )
    evidence = next(result for result in results if result.name == "AI release evidence")
    assert "AI_RELEASE_MANIFEST_PATH is required" not in evidence.detail
    assert "Evidence package is incomplete" in evidence.detail


def test_evidence_manifest_rejects_template_or_missing_clinical_evidence():
    template = {
        "schema_version": 2,
        "release_status": "not_ready",
        "research_only": True,
        "intended_use_statement": "Describe the exact intended clinical use, target population, workflow, exclusions and limitations using actual approved language.",
    }
    problems = validate_manifest_data(template)
    assert "release_status must be 'approved'" in problems
    assert "research_only must be false for a clinical release" in problems
    assert "model must be an object" in problems


def test_validator_rejects_boolean_and_blank_evidence_values():
    manifest = {
        "release_status": "approved",
        "research_only": False,
        "intended_use_statement": "Clinical decision support for the specified patient population with explicit exclusions and clinician review.",
        "model": {"name": "melanoma_binary", "version": "1.0.0", "artifact_sha256": "a" * 64},
        "dataset": {"name": "locked", "version": "1", "locked_test_set_manifest": {"uri": "", "sha256": "", "frozen_at": ""}},
        "metrics": {k: {"estimate": True, "ci95": {"lower": True, "upper": True}, "sample_count": True} for k in ("sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc")},
        "calibration": {"method": " ", "expected_calibration_error": None, "brier_score": None, "evidence": {"uri": "", "sha256": ""}},
        "subgroups": {"status": "completed", "evidence": {"uri": "", "sha256": ""}},
        "ood": {"status": "completed", "evidence": {"uri": "", "sha256": ""}},
        "abstention": {"status": "completed", "evidence": {"uri": "", "sha256": ""}},
        "clinician_review": {"status": "completed", "evidence": {"uri": "", "sha256": ""}},
        "external_validation": {"status": "completed", "site_or_dataset": "", "independent_reviewer": "", "evidence": {"uri": "", "sha256": ""}},
        "prospective_evaluation": {"status": "completed", "protocol_id": "", "site_or_cohort": "", "evidence": {"uri": "", "sha256": ""}},
        "approval": {"status": "approved", "approved_by": "", "approved_at": "", "evidence": {"uri": "", "sha256": ""}},
    }
    problems = validate_manifest_data(manifest)
    assert any("dataset locked manifest URI" in item for item in problems)
    assert any("metrics.sensitivity.estimate" in item for item in problems)
    assert any("calibration.method" in item for item in problems)
    assert any("approval.approved_by" in item for item in problems)


def test_valid_looking_manifest_still_requires_real_artifact_when_requested(tmp_path):
    manifest = {
        "schema_version": 2,
        "release_status": "approved",
        "research_only": False,
        "intended_use_statement": "Clinical decision support for the specified patient population with explicit exclusions and clinician review.",
        "model": {"name": "melanoma_binary", "version": "1.0.0", "artifact_sha256": "a" * 64},
        "dataset": {"name": "locked", "version": "1", "locked_test_set_manifest": {"uri": "dataset.json", "sha256": "b" * 64, "frozen_at": "2026-10-04T12:00:00Z"}},
        "metrics": {k: {"estimate": 0.8, "ci95": {"lower": 0.75, "upper": 0.85}, "sample_count": 100} for k in ("sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc")},
        "calibration": {"method": "bootstrap", "expected_calibration_error": 0.1, "brier_score": 0.1, "evidence": {"uri": "calibration", "sha256": "c" * 64}},
        "subgroups": {"status": "completed", "evidence": {"uri": "subgroups", "sha256": "d" * 64}},
        "ood": {"status": "completed", "evidence": {"uri": "ood", "sha256": "e" * 64}},
        "abstention": {"status": "completed", "evidence": {"uri": "abstention", "sha256": "f" * 64}},
        "clinician_review": {"status": "completed", "evidence": {"uri": "review", "sha256": "1" * 64}},
        "external_validation": {"status": "completed", "site_or_dataset": "external", "independent_reviewer": "reviewer", "evidence": {"uri": "external", "sha256": "2" * 64}},
        "prospective_evaluation": {"status": "completed", "protocol_id": "protocol", "site_or_cohort": "cohort", "evidence": {"uri": "prospective", "sha256": "3" * 64}},
        "approval": {"status": "approved", "approved_by": "approver", "approved_at": "2026-10-04T12:00:00Z", "evidence": {"uri": "approval", "sha256": "4" * 64}},
    }
    path = tmp_path / "release-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    ok, problems = validate_manifest_file(path, model_dir=tmp_path, require_artifact=True)
    assert ok is False
    assert any("model artifact is missing" in item for item in problems)
