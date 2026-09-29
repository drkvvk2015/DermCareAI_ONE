from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_ai_release_manifest import _validate_manifest, validate_file


@pytest.fixture
def complete_manifest() -> dict:
    digest = "a" * 64
    revision = "b" * 40
    evidence = "test-fixture://evidence"
    return {
        "schema_version": "1.0",
        "manifest_id": "test-fixture-manifest",
        "created_at": "2026-01-01T00:00:00Z",
        "release_status": "approved",
        "intended_use_statement": "Test fixture only; not a clinical intended use.",
        "research_only": False,
        "reproducibility": {
            "evaluation_code_revision": revision,
            "environment": "test-fixture environment",
            "dependency_lock_sha256": digest,
            "random_seed": 7,
            "protocol_version": "test-fixture",
        },
        "model": {
            "name": "test-fixture-model",
            "version": "test-fixture",
            "artifact_sha256": digest,
            "source_repository": "test-fixture://model",
            "source_revision": revision,
            "training_data_manifest": "test-fixture://training-data",
            "training_data_manifest_sha256": digest,
        },
        "dataset": {
            "name": "test-fixture-dataset",
            "version": "test-fixture",
            "locked_test_set_manifest": "test-fixture://locked-test-set",
            "manifest_sha256": digest,
            "source": "test-fixture only",
            "inclusion_exclusion_criteria": "test-fixture only",
            "split": "test-fixture",
            "sample_count": 10,
            "intended_population_prevalence": 0.5,
        },
        "metrics": {
            name: {
                "value": 0.5,
                "ci95_lower": 0.4,
                "ci95_upper": 0.6,
                "evidence": evidence,
            }
            for name in ("sensitivity", "specificity", "ppv", "npv", "roc_auc", "pr_auc")
        },
        "calibration": {
            "status": "completed",
            "method": "test-fixture",
            "result": "test-fixture",
            "evidence": evidence,
        },
        "subgroups": {
            "status": "completed",
            "results": "test-fixture",
            "evidence": evidence,
            "groups": [
                {
                    "name": "test-fixture group",
                    "sample_count": 5,
                    "results": "test-fixture",
                    "evidence": evidence,
                }
            ],
        },
        "ood": {
            "status": "completed",
            "response_policy": "test-fixture",
            "results": "test-fixture",
            "evidence": evidence,
            "challenge_sets": [
                {
                    "name": "test-fixture challenge",
                    "sample_count": 5,
                    "observed_behavior": "test-fixture",
                    "evidence": evidence,
                }
            ],
        },
        "abstention": {
            "status": "completed",
            "policy": "test-fixture",
            "threshold": 0.5,
            "coverage": 0.5,
            "selective_risk": 0.5,
            "results": "test-fixture",
            "evidence": evidence,
        },
        "clinician_review": {
            "status": "completed",
            "reviewer_count": 1,
            "override_analysis": "test-fixture",
            "evidence": evidence,
        },
        "external_validation": {
            "status": "completed",
            "independent": True,
            "site_or_dataset": "test-fixture",
            "results": "test-fixture",
            "evidence": evidence,
        },
        "approval": {
            "status": "completed",
            "approved_by": "test-fixture",
            "approved_at": "2026-01-02T00:00:00Z",
            "decision_id": "test-fixture",
            "audit_record": evidence,
        },
        "deployment": {
            "status": "completed",
            "rollback_plan": "test-fixture",
            "evidence": evidence,
        },
    }


def test_complete_test_fixture_passes_manifest_checks(complete_manifest: dict) -> None:
    assert _validate_manifest(complete_manifest) == []


def test_incomplete_and_contradictory_evidence_is_rejected(complete_manifest: dict) -> None:
    manifest = copy.deepcopy(complete_manifest)
    manifest["model"]["artifact_sha256"] = "not-a-digest"
    manifest["dataset"]["locked_test_set_manifest"] = None
    manifest["metrics"]["sensitivity"]["ci95_lower"] = 0.7
    manifest["subgroups"]["groups"] = []
    manifest["external_validation"]["status"] = "not_assessed"
    problems = _validate_manifest(manifest)

    assert any("model.artifact_sha256" in problem for problem in problems)
    assert any("dataset.locked_test_set_manifest" in problem for problem in problems)
    assert any("metrics.sensitivity" in problem for problem in problems)
    assert any("subgroups.groups" in problem for problem in problems)
    assert any("external_validation.status" in problem for problem in problems)


def test_research_only_manifest_cannot_be_approved(complete_manifest: dict) -> None:
    manifest = copy.deepcopy(complete_manifest)
    manifest["research_only"] = True

    problems = _validate_manifest(manifest)

    assert "research_only model cannot have an approved clinical release status" in problems


@pytest.mark.parametrize(
    "manifest",
    [
        [],
        {"release_status": []},
        {"release_status": "approved", "reproducibility": {"evaluation_code_revision": []}},
    ],
)
def test_wrong_root_and_field_types_are_rejected_without_crashing(manifest: object) -> None:
    assert _validate_manifest(manifest)


@pytest.mark.parametrize("contents", [b"{invalid", b"\xff"])
def test_invalid_json_files_are_reported(tmp_path: Path, contents: bytes) -> None:
    manifest_path = tmp_path / "invalid.json"
    manifest_path.write_bytes(contents)

    assert validate_file(str(manifest_path))[0].startswith("manifest: unable to read valid JSON")


def test_template_keeps_external_validation_and_approval_unmet() -> None:
    template_path = (
        Path(__file__).parents[2]
        / "docs"
        / "ai-validation"
        / "release-manifest.template.json"
    )
    manifest = json.loads(template_path.read_text(encoding="utf-8"))
    problems = _validate_manifest(manifest)

    assert manifest["research_only"] is True
    assert manifest["release_status"] == "not_ready"
    assert manifest["external_validation"]["status"] == "not_assessed"
    assert manifest["approval"]["status"] == "not_assessed"
    assert any("release_status must be 'approved'" in problem for problem in problems)
    assert any("external_validation.status must be 'completed'" in problem for problem in problems)
    assert any("approval.status must be 'completed'" in problem for problem in problems)
