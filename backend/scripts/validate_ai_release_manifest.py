from __future__ import annotations

import sys

from ai_release_evidence import validate_manifest_file


def main(path: str) -> int:
    ok, problems = validate_manifest_file(path)
    if ok:
        print("AI RELEASE EVIDENCE: PASS")
        return 0

    print("AI RELEASE EVIDENCE: FAIL")
    for problem in problems:
        print(f"- {problem}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/ai-validation/release-manifest.json"))
