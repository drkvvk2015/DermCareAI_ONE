import json
from pathlib import Path


def test_dependabot_compatibility_matrix_covers_open_prs_without_automerge():
    matrix_path = Path(__file__).resolve().parents[2] / "docs" / "dependency-compatibility.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))

    assert matrix["automatic_merge"] is False
    assert {entry["pr"] for entry in matrix["entries"]} == set(range(175, 183))
    assert all(entry["status"] in {"PASS", "NEEDS_REVIEW", "HOLD"} for entry in matrix["entries"])
    assert all(entry["evidence"] and entry["required_validation"] for entry in matrix["entries"])
    assert all(entry["merge_order"] for entry in matrix["entries"])
