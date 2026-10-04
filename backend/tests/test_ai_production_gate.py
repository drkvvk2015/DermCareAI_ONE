import json

from ai_release_evidence import validate_manifest_data
from model_registry import production_artifact_eligible


def test_production_ai_is_not_eligible_without_approved_deployment(tmp_path):
    ok, reason = production_artifact_eligible(model_dir=str(tmp_path), app_env="production")
    assert ok is False
    assert "production AI deployment" in reason or "governance" in reason


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


def test_valid_looking_manifest_still_requires_real_artifact_when_requested(tmp_path):
    manifest = {
        "schema_version": 2,
        "release_status": "approved",
        "research_only": False,
        "intended_use_statement": "Clinical decision support for the specified patient population with explicit exclusions and clinician review.",
        "model": {"name": "melanoma_binary", "version": "1.0.0", "artifact_sha256": "a" * 64},
        "dataset": {
            "name": "locked",
            "version": "1",
            "locked_test_set_manifest": "dataset.json",
            "manifest_sha256": "b" * 64,
            "provenance_ref": "prov",
            "inclusion_exclusion_ref": "criteria",
        },
        "metrics": {k: {"value": 0.8, "ci95": [0.75, 0.85]} for k in ("sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc")},
        "calibration": {"status": "completed", "evidence_ref": "calibration"},
        "subgroups": {"status": "completed", "evidence_ref": "subgroups"},
        "ood": {"status": "completed", "evidence_ref": "ood"},
        "abstention": {"status": "completed", "evidence_ref": "abstention"},
        "clinician_review": {"status": "completed", "evidence_ref": "review"},
        "external_validation": {"status": "completed", "evidence_ref": "external"},
        "approval": {
            "status": "completed",
            "approvers": [
                {"id": "c1", "role": "clinical", "approved_at": "2026-10-04T12:00:00Z", "record_ref": "r1", "record_sha256": "c" * 64},
                {"id": "t1", "role": "technical", "approved_at": "2026-10-04T12:01:00Z", "record_ref": "r2", "record_sha256": "d" * 64},
            ],
        },
        "governance": {
            "clinical_intended_use_review": {"status": "completed", "evidence_ref": "g1"},
            "regulatory_assessment": {"status": "completed", "evidence_ref": "g2"},
            "privacy_assessment": {"status": "completed", "evidence_ref": "g3"},
        },
        "deployment": {
            "status": "completed",
            "staging_evidence_ref": "s1",
            "rollback_evidence_ref": "rb1",
            "release_artifact_ref": "rel1",
        },
    }
    path = tmp_path / "release-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    from ai_release_evidence import validate_manifest_file
    ok, problems = validate_manifest_file(path, model_dir=tmp_path, require_artifact=True)
    assert ok is False
    assert any("model artifact is missing" in item for item in problems)
