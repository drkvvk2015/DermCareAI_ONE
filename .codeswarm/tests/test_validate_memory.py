from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from validate_memory import validate_memory  # noqa: E402


def learning_record(record_id: str, date: str = "2026-11-06") -> str:
    return f"""### {record_id}

- Date (UTC): {date}
- Run ID: run-test-001
- Source stage: DEBUG
- Pattern: A deterministic test pattern.
- Root cause: A test root cause supported by evidence.
- Evidence: A reproducible unit-test result.
- Action: Apply a specific corrective action.
- Affected area: CodeSwarm test suite
- Occurrences: 1
- Confidence: medium
"""


class MemoryValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.memory = self.root / ".codeswarm" / "memory"
        self.memory.mkdir(parents=True)
        (self.memory / "snapshots").mkdir()
        (self.memory / "schema-version").write_text("1.1.0\n", encoding="utf-8")
        (self.memory / "prompt-versions.md").write_text(
            "# Prompt versions\n\nAppend-only test fixture.\n", encoding="utf-8"
        )
        self.records = learning_record("LEARNING-0001") + "\n" + learning_record(
            "LEARNING-0002", "2026-11-06"
        )
        (self.memory / "learnings.md").write_text(
            "# CodeSwarm Learnings\n\n" + self.records + "\n## Entry Format\n",
            encoding="utf-8",
        )
        self.write_manifest()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_manifest(self, **overrides) -> None:
        manifest = {
            "schemaVersion": 1,
            "schema_version": "1.1.0",
            "project": "DermCareAI_ONE",
            "files": {
                "learnings": "learnings.md",
                "schemaVersion": "schema-version",
                "promptVersions": "prompt-versions.md",
                "snapshots": "snapshots/",
            },
            "recordCount": 2,
            "record_count": 2,
            "firstRecordId": "LEARNING-0001",
            "first_record_id": "LEARNING-0001",
            "latestRecordId": "LEARNING-0002",
            "latest_record_id": "LEARNING-0002",
            "latestRecordHash": None,
            "latest_record_hash": None,
            "integrityStatus": "UNVERIFIED",
            "integrity_status": "UNVERIFIED",
        }
        manifest.update(overrides)
        (self.memory / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

    def test_structural_pass_without_hash_is_unverified_not_failure(self) -> None:
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "PASS")
        self.assertEqual(report.cryptographic_status, "UNVERIFIED")
        self.assertEqual(report.overall_status, "UNVERIFIED")
        self.assertEqual(report.record_count, 2)
        self.assertEqual(report.issues, [])

    def test_matching_latest_record_hash_passes(self) -> None:
        baseline = validate_memory(self.root)
        digest = baseline.computed_latest_record_hash
        self.write_manifest(latestRecordHash=digest, latest_record_hash=digest)
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "PASS")
        self.assertEqual(report.cryptographic_status, "VERIFIED")
        self.assertEqual(report.overall_status, "PASS")

    def test_hash_mismatch_fails(self) -> None:
        self.write_manifest(
            latestRecordHash="0" * 64,
            latest_record_hash="0" * 64,
        )
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "PASS")
        self.assertEqual(report.cryptographic_status, "MISMATCH")
        self.assertEqual(report.overall_status, "FAILURE")
        self.assertTrue(any("SHA-256 does not match" in item for item in report.cryptographic_issues))
        self.assertEqual(report.repairability, "MANUAL_REVIEW_REQUIRED")

    def test_record_count_mismatch_fails(self) -> None:
        self.write_manifest(recordCount=99, record_count=99)
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("Record count mismatch" in item for item in report.issues))

    def test_duplicate_ids_fail(self) -> None:
        duplicate = learning_record("LEARNING-0001")
        (self.memory / "learnings.md").write_text(
            "# CodeSwarm Learnings\n\n" + duplicate + "\n" + duplicate + "\n## Entry Format\n",
            encoding="utf-8",
        )
        self.write_manifest(
            recordCount=2,
            record_count=2,
            firstRecordId="LEARNING-0001",
            first_record_id="LEARNING-0001",
            latestRecordId="LEARNING-0001",
            latest_record_id="LEARNING-0001",
        )
        report = validate_memory(self.root)
        self.assertEqual(report.overall_status, "FAILURE")
        self.assertTrue(any("Duplicate learning record IDs" in item for item in report.issues))

    def test_metadata_only_mismatch_offers_candidate_without_writing(self) -> None:
        before = (self.memory / "learnings.md").read_bytes()
        self.write_manifest(recordCount=9, record_count=9)
        report = validate_memory(self.root)
        self.assertEqual(report.repairability, "METADATA_ONLY_SAFE")
        self.assertIsNotNone(report.manifest_rebuild_candidate)
        self.assertEqual(report.manifest_rebuild_candidate["record_count"], 2)
        self.assertEqual((self.memory / "learnings.md").read_bytes(), before)

    def test_malformed_record_fails(self) -> None:
        (self.memory / "learnings.md").write_text(
            "# CodeSwarm Learnings\n\n### LEARNING-0001\n\n- Date (UTC): 2026-11-06\n\n## Entry Format\n",
            encoding="utf-8",
        )
        self.write_manifest(
            recordCount=1,
            record_count=1,
            latestRecordId="LEARNING-0001",
            latest_record_id="LEARNING-0001",
        )
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("missing required fields" in item for item in report.issues))

    def test_out_of_order_learning_ids_fail(self) -> None:
        out_of_order = learning_record("LEARNING-0002") + "\n" + learning_record("LEARNING-0001")
        (self.memory / "learnings.md").write_text(
            "# CodeSwarm Learnings\n\n" + out_of_order + "\n## Entry Format\n",
            encoding="utf-8",
        )
        self.write_manifest(
            recordCount=2,
            record_count=2,
            firstRecordId="LEARNING-0002",
            first_record_id="LEARNING-0002",
            latestRecordId="LEARNING-0001",
            latest_record_id="LEARNING-0001",
        )
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("not in ascending numeric order" in item for item in report.issues))

    def test_manifest_path_traversal_fails(self) -> None:
        (self.memory / "manifest.json").write_text(
            json.dumps({
                "schema_version": "1.1.0",
                "record_count": 2,
                "first_record_id": "LEARNING-0001",
                "latest_record_id": "LEARNING-0002",
                "latest_record_hash": None,
                "files": {
                    "learnings": "../../outside.md",
                    "schemaVersion": "schema-version",
                    "promptVersions": "prompt-versions.md",
                },
            }),
            encoding="utf-8",
        )
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("escapes the memory directory" in item for item in report.issues))

    def test_missing_prompt_version_file_fails(self) -> None:
        (self.memory / "prompt-versions.md").unlink()
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("Required file is missing" in item for item in report.issues))

    def test_alias_disagreement_fails(self) -> None:
        self.write_manifest(recordCount=2, record_count=3)
        report = validate_memory(self.root)
        self.assertEqual(report.overall_status, "FAILURE")
        self.assertTrue(any("Manifest alias mismatch" in item for item in report.issues))

    def test_schema_version_mismatch_fails(self) -> None:
        self.write_manifest(schema_version="9.9.9")
        report = validate_memory(self.root)
        self.assertEqual(report.overall_status, "FAILURE")
        self.assertTrue(any("Schema version mismatch" in item for item in report.issues))

    def test_read_only_knowledge_graph_and_intelligence_are_derived(self) -> None:
        report = validate_memory(self.root)
        graph = report.knowledge_graph
        intelligence = report.engineering_intelligence
        self.assertEqual(graph["projection"], "READ_ONLY_DERIVED_FROM_LEARNING_RECORDS")
        self.assertEqual(intelligence["record_count"], 2)
        self.assertEqual(intelligence["knowledge_graph_node_count"], len(graph["nodes"]))
        self.assertEqual(intelligence["knowledge_graph_edge_count"], len(graph["edges"]))
        self.assertEqual(len(intelligence["repeated_patterns"]), 1)
        self.assertEqual(intelligence["repeated_patterns"][0]["occurrences"], 2)
        self.assertEqual(
            intelligence["repeated_patterns"][0]["record_ids"],
            ["LEARNING-0001", "LEARNING-0002"],
        )
        self.assertEqual(intelligence["confidence_distribution"], {"medium": 2})

    def test_knowledge_graph_does_not_merge_non_identical_patterns(self) -> None:
        second = learning_record("LEARNING-0002").replace(
            "A deterministic test pattern.",
            "A DETERMINISTIC TEST PATTERN.",
        )
        (self.memory / "learnings.md").write_text(
            "# CodeSwarm Learnings\n\n"
            + learning_record("LEARNING-0001")
            + "\n"
            + second
            + "\n## Entry Format\n",
            encoding="utf-8",
        )
        report = validate_memory(self.root)
        self.assertEqual(report.engineering_intelligence["repeated_patterns"], [])
        pattern_nodes = [
            node for node in report.knowledge_graph["nodes"]
            if node["type"] == "pattern"
        ]
        self.assertEqual(len(pattern_nodes), 2)

    def test_validator_does_not_modify_memory_files(self) -> None:
        before = {
            path.relative_to(self.memory): path.read_bytes()
            for path in self.memory.iterdir()
            if path.is_file()
        }
        validate_memory(self.root)
        after = {
            path.relative_to(self.memory): path.read_bytes()
            for path in self.memory.iterdir()
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_fractional_manifest_record_count_is_rejected(self) -> None:
        self.write_manifest(recordCount=2.9, record_count=2.9)
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("exact JSON integer" in item for item in report.issues))
        self.assertEqual(report.repairability, "MANUAL_REVIEW_REQUIRED")

    def test_malformed_active_learning_heading_requires_manual_review(self) -> None:
        malformed = self.records.replace(
            "### LEARNING-0001", "### LEARNING-0001x", 1
        )
        (self.memory / "learnings.md").write_text(
            "# CodeSwarm Learnings\n\n" + malformed + "\n## Entry Format\n",
            encoding="utf-8",
        )
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("Malformed active learning record heading" in item for item in report.issues))
        self.assertEqual(report.repairability, "MANUAL_REVIEW_REQUIRED")
        self.assertIsNone(report.manifest_rebuild_candidate)

    def test_malformed_learning_heading_inside_fenced_example_is_ignored(self) -> None:
        (self.memory / "learnings.md").write_text(
            "# CodeSwarm Learnings\n\n"
            + self.records
            + "\n## Entry Format\n\n~~~markdown\n### LEARNING-0001x\n~~~\n",
            encoding="utf-8",
        )
        report = validate_memory(self.root)
        self.assertEqual(report.record_count, 2)
        self.assertFalse(any("Malformed active learning record heading" in item for item in report.issues))

    def test_empty_required_field_cannot_borrow_next_line(self) -> None:
        malformed = self.records.replace(
            "- Evidence: A reproducible unit-test result.",
            "- Evidence:\n- Action: Apply a specific corrective action.",
            1,
        )
        (self.memory / "learnings.md").write_text(
            "# CodeSwarm Learnings\n\n" + malformed + "\n## Entry Format\n",
            encoding="utf-8",
        )
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("LEARNING-0001 is missing required fields: Evidence" in item for item in report.issues))
        self.assertEqual(report.repairability, "MANUAL_REVIEW_REQUIRED")

    def test_hash_alias_conflict_is_mismatch_and_not_repairable(self) -> None:
        digest = validate_memory(self.root).computed_latest_record_hash
        self.write_manifest(
            recordCount=9,
            record_count=9,
            latestRecordHash=digest,
            latest_record_hash=None,
        )
        report = validate_memory(self.root)
        self.assertEqual(report.cryptographic_status, "MISMATCH")
        self.assertTrue(any("aliases conflict" in item for item in report.cryptographic_issues))
        self.assertEqual(report.repairability, "MANUAL_REVIEW_REQUIRED")
        self.assertIsNone(report.manifest_rebuild_candidate)

    def test_manifest_files_map_is_required_and_complete(self) -> None:
        manifest = json.loads((self.memory / "manifest.json").read_text(encoding="utf-8"))
        del manifest["files"]["snapshots"]
        (self.memory / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("Manifest files.snapshots is missing" in item for item in report.issues))

    def test_snapshot_manifest_path_traversal_fails(self) -> None:
        manifest = json.loads((self.memory / "manifest.json").read_text(encoding="utf-8"))
        manifest["files"]["snapshots"] = "../../outside"
        (self.memory / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("Manifest files.snapshots must reference" in item for item in report.issues))

    def test_missing_snapshot_directory_fails(self) -> None:
        (self.memory / "snapshots").rmdir()
        report = validate_memory(self.root)
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertTrue(any("missing or invalid directory" in item for item in report.issues))


if __name__ == "__main__":
    unittest.main()
