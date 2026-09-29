"""CLI adapter for producing machine-readable, conservative CI repair evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from auto_repair import DEFAULT_MAX_ATTEMPTS, build_repair_report, report_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a guardrailed repair proposal/report.")
    parser.add_argument("--log", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--path", action="append", default=[], dest="paths")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--idempotency-key")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Request mutation mode; this implementation intentionally blocks it.",
    )
    args = parser.parse_args()

    log_text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    report = build_repair_report(
        log_text,
        paths=args.paths,
        dry_run=not args.apply,
        attempt=args.attempt,
        max_attempts=args.max_attempts,
        idempotency_key=args.idempotency_key,
    )
    Path(args.output).write_text(report_json(report), encoding="utf-8")
    print(report_json(report), end="")
    return 0 if report["status"] == "eligible-for-reviewed-proposal" else 2


if __name__ == "__main__":
    raise SystemExit(main())
