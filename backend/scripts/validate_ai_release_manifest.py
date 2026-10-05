from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_release_evidence import validate_ai_release_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the structure and model identity of an AI release evidence package.")
    parser.add_argument("manifest", nargs="?", default="docs/ai-validation/release-manifest.json")
    parser.add_argument("--expected-model-name")
    parser.add_argument("--expected-model-version")
    parser.add_argument("--expected-artifact-sha256")
    args = parser.parse_args()

    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"AI RELEASE EVIDENCE: FAIL ({exc})")
        return 1

    problems = validate_ai_release_manifest(
        manifest,
        expected_model_name=args.expected_model_name,
        expected_model_version=args.expected_model_version,
        expected_artifact_sha256=args.expected_artifact_sha256,
    )
    if problems:
        print("AI RELEASE EVIDENCE: FAIL")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("AI RELEASE EVIDENCE: PASS (structural check only; accountable clinical review remains required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
