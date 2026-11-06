#!/usr/bin/env python3
"""Read-only structural and cryptographic consistency validator for CodeSwarm memory.

Hash contract:
- Select the latest Markdown learning block beginning with
  "### LEARNING-<digits>".
- End the block before the next "### LEARNING-<digits>" or "## " section.
- Normalize CRLF/CR to LF, remove trailing LF characters, then append exactly
  one LF. SHA-256 is calculated over the resulting UTF-8 bytes.

This detects changes against a stored digest. It is not a digital signature and
does not prove authorship if both the record and manifest are changed together.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

LEARNING_HEADING = re.compile(r"(?m)^###\s+(LEARNING-\d+)\s*$")
SECTION_HEADING = re.compile(r"(?m)^##\s+")
SHA256_RE = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{64})$")

REQUIRED_FIELDS = {
    "Date (UTC)": re.compile(r"(?m)^- Date \(UTC\):\s*\S.+$"),
    "Run ID": re.compile(r"(?m)^- Run ID:\s*\S.+$"),
    "Source stage": re.compile(r"(?m)^- Source stage:\s*\S.+$"),
    "Pattern": re.compile(r"(?m)^- Pattern:\s*\S.+$"),
    "Root cause": re.compile(r"(?m)^- Root cause:\s*\S.+$"),
    "Evidence": re.compile(r"(?m)^- Evidence:\s*\S.+$"),
    "Action": re.compile(r"(?m)^- Action:\s*\S.+$"),
    "Affected area": re.compile(r"(?m)^- Affected area:\s*\S.+$"),
    "Occurrences": re.compile(r"(?m)^- Occurrences:\s*\d+\s*$"),
    "Confidence": re.compile(r"(?m)^- Confidence:\s*(low|medium|high)\s*$"),
}

ALIASES = (
    ("recordCount", "record_count"),
    ("firstRecordId", "first_record_id"),
    ("latestRecordId", "latest_record_id"),
    ("latestRecordHash", "latest_record_hash"),
    ("integrityStatus", "integrity_status"),
    ("cryptographicIntegrity", "cryptographic_integrity"),
    ("recordHashAlgorithm", "record_hash_algorithm"),
    ("recordHashScope", "record_hash_scope"),
)


@dataclass
class ValidationReport:
    overall_status: str = "FAILURE"
    structural_status: str = "FAILURE"
    cryptographic_status: str = "UNVERIFIED"
    schema_version: Optional[str] = None
    record_count: int = 0
    manifest_record_count: Optional[int] = None
    first_record_id: Optional[str] = None
    latest_record_id: Optional[str] = None
    computed_latest_record_hash: Optional[str] = None
    stored_latest_record_hash: Optional[str] = None
    issues: list[str] = field(default_factory=list)
    cryptographic_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    knowledge_graph: dict[str, Any] = field(default_factory=dict)
    engineering_intelligence: dict[str, Any] = field(default_factory=dict)
    read_only: bool = True
    repairability: str = "NONE"
    manifest_rebuild_candidate: Optional[dict[str, Any]] = None


def _read_text(path: Path, issues: list[str]) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append("Required file is missing: " + str(path))
    except UnicodeDecodeError:
        issues.append("File is not valid UTF-8: " + str(path))
    except OSError as exc:
        issues.append("Cannot read file " + str(path) + ": " + str(exc))
    return None


def _canonical_record_block(text: str, start: int, end: int) -> bytes:
    block = text[start:end].replace("\r\n", "\n").replace("\r", "\n")
    block = block.rstrip("\n") + "\n"
    return block.encode("utf-8")


def _extract_records(text: str) -> list[tuple[str, bytes, str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    matches = list(LEARNING_HEADING.finditer(text))
    records: list[tuple[str, bytes, str]] = []

    for index, match in enumerate(matches):
        start = match.start()
        next_entry = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        section_match = SECTION_HEADING.search(text, match.end())
        next_section = section_match.start() if section_match else len(text)
        end = min(next_entry, next_section)

        block_text = text[start:end].rstrip("\n") + "\n"
        records.append(
            (
                match.group(1),
                block_text.encode("utf-8"),
                block_text,
            )
        )

    return records


def _manifest_value(manifest: dict[str, Any], snake: str, camel: str) -> Any:
    if snake in manifest:
        return manifest[snake]
    return manifest.get(camel)


def _record_field(block: str, field_name: str) -> Optional[str]:
    match = re.search(
        r"(?m)^- " + re.escape(field_name) + r":\s*(.*?)\s*$",
        block,
    )
    if not match:
        return None
    value = match.group(1).strip()
    return value if value else None


def _stable_node_id(prefix: str, label: str) -> str:
    normalized = " ".join(label.casefold().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return prefix + "-" + digest


def _build_knowledge_views(
    records: list[tuple[str, bytes, str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()
    area_counts: dict[str, int] = {}
    stage_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    patterns: dict[str, list[str]] = {}
    low_confidence_records: list[str] = []

    for record_id, _, block in records:
        pattern = _record_field(block, "Pattern")
        root_cause = _record_field(block, "Root cause")
        affected_area = _record_field(block, "Affected area")
        source_stage = (_record_field(block, "Source stage") or "UNKNOWN").upper()
        confidence = (_record_field(block, "Confidence") or "unknown").lower()

        nodes[record_id] = {
            "id": record_id,
            "type": "learning",
            "label": pattern or record_id,
            "source_stage": source_stage,
            "confidence": confidence,
        }
        stage_counts[source_stage] = stage_counts.get(source_stage, 0) + 1
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

        if confidence == "low":
            low_confidence_records.append(record_id)

        if affected_area:
            area_id = _stable_node_id("AREA", affected_area)
            nodes[area_id] = {
                "id": area_id,
                "type": "affected_area",
                "label": affected_area,
            }
            edges.add((record_id, "AFFECTS", area_id))
            area_counts[affected_area] = area_counts.get(affected_area, 0) + 1

        if pattern:
            pattern_id = _stable_node_id("PATTERN", pattern)
            nodes[pattern_id] = {
                "id": pattern_id,
                "type": "pattern",
                "label": pattern,
            }
            edges.add((record_id, "IDENTIFIES_PATTERN", pattern_id))
            patterns.setdefault(pattern, []).append(record_id)

        if root_cause:
            cause_id = _stable_node_id("CAUSE", root_cause)
            nodes[cause_id] = {
                "id": cause_id,
                "type": "root_cause",
                "label": root_cause,
            }
            edges.add((record_id, "ROOT_CAUSE", cause_id))

    repeated_patterns = [
        {"pattern": label, "record_ids": sorted(record_ids), "occurrences": len(record_ids)}
        for label, record_ids in patterns.items()
        if len(record_ids) > 1
    ]
    repeated_patterns.sort(key=lambda item: (-item["occurrences"], item["pattern"]))

    graph = {
        "projection": "READ_ONLY_DERIVED_FROM_LEARNING_RECORDS",
        "nodes": sorted(nodes.values(), key=lambda item: item["id"]),
        "edges": [
            {"from": source, "type": relation, "to": target}
            for source, relation, target in sorted(edges)
        ],
    }
    intelligence = {
        "record_count": len(records),
        "affected_area_counts": dict(sorted(area_counts.items())),
        "source_stage_distribution": dict(sorted(stage_counts.items())),
        "confidence_distribution": dict(sorted(confidence_counts.items())),
        "repeated_patterns": repeated_patterns,
        "low_confidence_records": sorted(low_confidence_records),
        "knowledge_graph_node_count": len(nodes),
        "knowledge_graph_edge_count": len(edges),
        "interpretation": (
            "Exact-text grouping only. Similar but non-identical patterns are not "
            "automatically merged. Use as navigation and prioritization evidence, "
            "not as proof of causality."
        ),
    }
    return graph, intelligence


def validate_memory(repo_root: Path) -> ValidationReport:
    memory_dir = repo_root / ".codeswarm" / "memory"
    report = ValidationReport()
    issues = report.issues
    warnings = report.warnings

    schema_text = _read_text(memory_dir / "schema-version", issues)
    manifest_text = _read_text(memory_dir / "manifest.json", issues)
    learnings_text = _read_text(memory_dir / "learnings.md", issues)
    prompt_versions_text = _read_text(memory_dir / "prompt-versions.md", issues)

    if any(value is None for value in (
        schema_text, manifest_text, learnings_text, prompt_versions_text
    )):
        report.overall_status = "FAILURE"
        report.structural_status = "FAILURE"
        return report

    try:
        manifest = json.loads(manifest_text)
    except json.JSONDecodeError as exc:
        issues.append("manifest.json is invalid JSON: " + str(exc))
        report.overall_status = "FAILURE"
        report.structural_status = "FAILURE"
        return report

    if not isinstance(manifest, dict):
        issues.append("manifest.json root must be a JSON object.")
        report.overall_status = "FAILURE"
        report.structural_status = "FAILURE"
        return report

    schema_version = schema_text.strip()
    manifest_schema = manifest.get("schema_version", manifest.get("schemaVersion"))
    report.schema_version = schema_version

    if not schema_version:
        issues.append("schema-version is empty.")
    if not isinstance(manifest_schema, (str, int, float)):
        issues.append("manifest schema_version/schemaVersion is missing or invalid.")
    elif str(manifest_schema) != schema_version:
        issues.append(
            "Schema version mismatch: schema-version file is "
            + schema_version + " but manifest declares " + str(manifest_schema) + "."
        )

    for camel, snake in ALIASES:
        if camel in manifest and snake in manifest and manifest[camel] != manifest[snake]:
            issues.append(
                "Manifest alias mismatch: " + camel + " differs from " + snake + "."
            )

    records = _extract_records(learnings_text)
    ids = [record[0] for record in records]
    report.record_count = len(records)
    report.knowledge_graph, report.engineering_intelligence = _build_knowledge_views(records)

    if not records:
        issues.append("No learning records were found in learnings.md.")
    if len(ids) != len(set(ids)):
        issues.append("Duplicate learning record IDs were found.")

    numeric_ids = [int(value.rsplit("-", 1)[1]) for value in ids]
    if numeric_ids != sorted(numeric_ids):
        issues.append("Learning record IDs are not in ascending numeric order.")

    for record_id, _, block in records:
        missing = [
            field_name for field_name, pattern in REQUIRED_FIELDS.items()
            if not pattern.search(block)
        ]
        if missing:
            issues.append(
                record_id + " is missing required fields: " + ", ".join(missing) + "."
            )

    if records:
        report.first_record_id = ids[0]
        report.latest_record_id = ids[-1]

    raw_count = _manifest_value(manifest, "record_count", "recordCount")
    try:
        manifest_count = int(raw_count)
        report.manifest_record_count = manifest_count
    except (TypeError, ValueError):
        issues.append("Manifest record_count/recordCount is missing or not an integer.")
        manifest_count = None

    if manifest_count is not None and manifest_count != len(records):
        issues.append(
            "Record count mismatch: manifest declares "
            + str(manifest_count) + " but learnings.md contains "
            + str(len(records)) + "."
        )

    manifest_first = _manifest_value(manifest, "first_record_id", "firstRecordId")
    manifest_latest = _manifest_value(manifest, "latest_record_id", "latestRecordId")

    if records and manifest_first != ids[0]:
        issues.append(
            "First record mismatch: manifest declares "
            + str(manifest_first) + " but first record is " + ids[0] + "."
        )
    if records and manifest_latest != ids[-1]:
        issues.append(
            "Latest record mismatch: manifest declares "
            + str(manifest_latest) + " but latest record is " + ids[-1] + "."
        )

    if not prompt_versions_text.strip():
        issues.append("prompt-versions.md is empty.")

    file_map = manifest.get("files")
    if file_map is not None:
        if not isinstance(file_map, dict):
            issues.append("Manifest files entry must be an object.")
        else:
            for key in ("learnings", "schemaVersion", "promptVersions"):
                relative = file_map.get(key)
                if not isinstance(relative, str) or not relative.strip():
                    issues.append("Manifest files." + key + " is missing or invalid.")
                    continue
                candidate = memory_dir / relative
                try:
                    candidate.resolve().relative_to(memory_dir.resolve())
                except ValueError:
                    issues.append("Manifest files." + key + " escapes the memory directory.")
                    continue
                if not candidate.is_file():
                    issues.append("Manifest references a missing file: " + str(candidate))

    if records:
        latest_hash = hashlib.sha256(records[-1][1]).hexdigest()
        report.computed_latest_record_hash = latest_hash
    stored_hash = _manifest_value(manifest, "latest_record_hash", "latestRecordHash")
    report.stored_latest_record_hash = stored_hash

    if stored_hash in (None, ""):
        report.cryptographic_status = "UNVERIFIED"
        warnings.append(
            "No stored latest-record SHA-256 exists; structural integrity can still pass. "
            "A bootstrap baseline may be established from this repository snapshot."
        )
    elif not isinstance(stored_hash, str):
        report.cryptographic_status = "MISMATCH"
        report.cryptographic_issues.append("Stored latest_record_hash must be a string or null.")
    else:
        match = SHA256_RE.fullmatch(stored_hash.strip())
        if not match:
            report.cryptographic_status = "MISMATCH"
            report.cryptographic_issues.append("Stored latest_record_hash is not a valid SHA-256 value.")
        elif report.computed_latest_record_hash and (
            match.group(1).lower() != report.computed_latest_record_hash.lower()
        ):
            report.cryptographic_status = "MISMATCH"
            report.cryptographic_issues.append("Latest learning record SHA-256 does not match the manifest.")
        elif report.computed_latest_record_hash:
            report.cryptographic_status = "VERIFIED"

    # Keep structural and cryptographic results independent. A digest mismatch
    # fails overall memory integrity, but does not make the record structure fail.
    report.structural_status = "FAILURE" if issues else "PASS"

    if report.structural_status == "FAILURE" or report.cryptographic_status == "MISMATCH":
        report.overall_status = "FAILURE"
    elif report.cryptographic_status == "UNVERIFIED":
        report.overall_status = "UNVERIFIED"
    else:
        report.overall_status = "PASS"

    # Only manifest metadata drift is eligible for deterministic reconstruction.
    # Never rebuild metadata after malformed records, duplicate IDs, schema drift,
    # path violations, missing files, invalid JSON, or a stored digest mismatch.
    metadata_prefixes = (
        "Manifest alias mismatch:",
        "Record count mismatch:",
        "First record mismatch:",
        "Latest record mismatch:",
    )
    if issues and all(issue.startswith(metadata_prefixes) for issue in issues):
        if report.cryptographic_status != "MISMATCH" and records:
            candidate = dict(manifest)
            count = len(records)
            first_id = ids[0]
            latest_id = ids[-1]
            latest_hash = report.computed_latest_record_hash

            candidate["recordCount"] = count
            candidate["record_count"] = count
            candidate["firstRecordId"] = first_id
            candidate["first_record_id"] = first_id
            candidate["latestRecordId"] = latest_id
            candidate["latest_record_id"] = latest_id
            candidate["latestRecordHash"] = latest_hash
            candidate["latest_record_hash"] = latest_hash
            candidate["recordHashAlgorithm"] = "sha256"
            candidate["record_hash_algorithm"] = "sha256"
            candidate["recordHashScope"] = "normalized-latest-record-block-v1"
            candidate["record_hash_scope"] = "normalized-latest-record-block-v1"
            candidate["structuralIntegrity"] = "PASS"
            candidate["structural_integrity"] = "PASS"
            candidate["cryptographicIntegrity"] = "VERIFIED"
            candidate["cryptographic_integrity"] = "VERIFIED"
            candidate["integrityStatus"] = "PASS"
            candidate["integrity_status"] = "PASS"

            report.repairability = "METADATA_ONLY_SAFE"
            report.manifest_rebuild_candidate = candidate
        else:
            report.repairability = "MANUAL_REVIEW_REQUIRED"
    elif issues or report.cryptographic_status == "MISMATCH":
        report.repairability = "MANUAL_REVIEW_REQUIRED"

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root (defaults to the parent of .codeswarm/tools).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    args = parser.parse_args()

    report = validate_memory(args.repo_root.resolve())
    payload = asdict(report)

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("CodeSwarm Memory Validation")
        print("Overall: " + report.overall_status)
        print("Structural: " + report.structural_status)
        print("Cryptographic: " + report.cryptographic_status)
        print("Records: " + str(report.record_count))
        print("First ID: " + str(report.first_record_id))
        print("Latest ID: " + str(report.latest_record_id))
        print("Computed latest hash: " + str(report.computed_latest_record_hash))
        for issue in report.issues:
            print("ERROR: " + issue)
        for warning in report.warnings:
            print("WARNING: " + warning)

    return 1 if report.overall_status == "FAILURE" else 0


if __name__ == "__main__":
    sys.exit(main())
