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
        self.assertEqual(report.structural_status, "FAILURE")
        self.assertEqual(report.cryptographic_status, "MISMATCH")
        self.assertEqual(report.overall_status, "FAILURE")

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


if __name__ == "__main__":
    unittest.main()
