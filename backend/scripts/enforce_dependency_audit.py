from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {label} report {path}: {exc}") from exc


def _package(value: Any) -> str:
    return re.sub(r"[-_.]+", "-", str(value).strip().lower())


def _npm_advisory_sources(
    vulnerabilities: dict[str, Any],
    package: str,
    seen: set[str] | None = None,
) -> list[tuple[str, str]]:
    visited = set() if seen is None else seen
    if package in visited:
        return []
    visited.add(package)
    finding = vulnerabilities.get(package, {})
    sources: list[tuple[str, str]] = []
    for item in finding.get("via", []) if isinstance(finding, dict) else []:
        if isinstance(item, str) and item in vulnerabilities:
            sources.extend(_npm_advisory_sources(vulnerabilities, item, visited))
        elif isinstance(item, dict):
            url = str(item.get("url") or "")
            stable_ids = re.findall(r"(?:GHSA-[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}|CVE-\d{4}-\d+)", url, re.IGNORECASE)
            if stable_ids:
                sources.extend((package, advisory) for advisory in stable_ids)
            elif item.get("source") is not None:
                sources.append((package, str(item["source"])))
    return sorted(set(sources), key=lambda source: (source[0].casefold(), source[1].upper()))


def _exceptions(payload: Any) -> tuple[dict[tuple[str, str, str], dict[str, str]], list[str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("exceptions"), list):
        raise ValueError("Exception file must contain an exceptions array")
    active: dict[tuple[str, str, str], dict[str, str]] = {}
    errors: list[str] = []
    today = datetime.now(timezone.utc).date()
    for index, item in enumerate(payload["exceptions"]):
        label = f"exceptions[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        ecosystem = item.get("ecosystem")
        package = item.get("package")
        advisory = item.get("advisory")
        reason = item.get("reason")
        owner = item.get("owner")
        expires_on = item.get("expires_on")
        if ecosystem not in {"npm", "python"}:
            errors.append(f"{label}.ecosystem must be npm or python")
            continue
        if not all(isinstance(value, str) and value.strip() for value in (package, advisory, reason, owner, expires_on)):
            errors.append(f"{label} requires package, advisory, reason, owner, and expires_on")
            continue
        try:
            expiry = date.fromisoformat(expires_on)
        except ValueError:
            errors.append(f"{label}.expires_on must use YYYY-MM-DD")
            continue
        if expiry < today:
            errors.append(f"{label} expired on {expires_on}; remove it or renew it with review")
            continue
        key = (ecosystem, _package(package), advisory.strip().upper())
        if key in active:
            errors.append(f"{label} duplicates an existing exception")
            continue
        active[key] = item
    return active, errors


def _matching_exception(
    active: dict[tuple[str, str, str], dict[str, str]],
    ecosystem: str,
    package: str,
    advisories: list[str],
) -> bool:
    keys = [(ecosystem, _package(package), advisory.strip().upper()) for advisory in advisories if advisory]
    return bool(keys) and all(key in active for key in keys)


def _matching_npm_exceptions(
    active: dict[tuple[str, str, str], dict[str, str]],
    sources: list[tuple[str, str]],
) -> bool:
    """Match npm exceptions against the affected package at the end of each via chain."""
    return bool(sources) and all(
        ("npm", _package(package), advisory.strip().upper()) in active
        for package, advisory in sources
    )


def enforce(npm_mobile: Any, npm_web: Any, python_reports: list[tuple[str, Any]], exception_payload: Any) -> list[str]:
    active, problems = _exceptions(exception_payload)

    for label, report in (("mobile npm", npm_mobile), ("webapp npm", npm_web)):
        if not isinstance(report, dict) or not isinstance(report.get("auditReportVersion"), int) or not isinstance(report.get("vulnerabilities"), dict):
            problems.append(f"{label}: invalid or incomplete npm audit report")
            continue
        for package, finding in report["vulnerabilities"].items():
            if not isinstance(finding, dict) or finding.get("severity") not in {"high", "critical"}:
                continue
            sources = _npm_advisory_sources(report["vulnerabilities"], package)
            if not _matching_npm_exceptions(active, sources):
                advisories = sorted({advisory for _, advisory in sources}, key=str.upper)
                problems.append(f"{label}: {package} has an unexcepted high/critical advisory ({', '.join(advisories) or 'advisory ID unavailable'})")

    for label, python in python_reports:
        if not isinstance(python, dict) or not isinstance(python.get("dependencies"), list):
            problems.append(f"{label}: invalid or incomplete pip-audit report")
            continue
        for dependency in python["dependencies"]:
            if not isinstance(dependency, dict):
                problems.append(f"{label}: malformed dependency entry in pip-audit report")
                continue
            package = dependency.get("name", "unknown")
            for vulnerability in dependency.get("vulns", []):
                if not isinstance(vulnerability, dict):
                    problems.append(f"{label}: malformed vulnerability entry for {package}")
                    continue
                advisory_ids = [str(vulnerability.get("id") or "")]
                aliases = vulnerability.get("aliases", [])
                if isinstance(aliases, list):
                    advisory_ids.extend(str(alias) for alias in aliases)
                if not any(_matching_exception(active, "python", package, [advisory]) for advisory in advisory_ids):
                    problems.append(f"{label}: {package} has an unexcepted vulnerability ({advisory_ids[0] or 'advisory ID unavailable'})")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce dependency audit thresholds and time-limited advisory exceptions.")
    parser.add_argument("--mobile", type=Path, required=True)
    parser.add_argument("--webapp", type=Path, required=True)
    parser.add_argument("--python-runtime", type=Path, required=True)
    parser.add_argument("--python-ci", type=Path, required=True)
    parser.add_argument("--exceptions", type=Path, default=Path("security/dependency-audit-exceptions.json"))
    args = parser.parse_args()
    try:
        problems = enforce(
            _load(args.mobile, "mobile npm"),
            _load(args.webapp, "webapp npm"),
            [
                ("Python runtime", _load(args.python_runtime, "Python runtime")),
                ("Python CI", _load(args.python_ci, "Python CI")),
            ],
            _load(args.exceptions, "dependency exception"),
        )
    except ValueError as exc:
        print(f"DEPENDENCY AUDIT: FAIL ({exc})")
        return 1
    if problems:
        print("DEPENDENCY AUDIT: FAIL")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("DEPENDENCY AUDIT: PASS (high/critical npm findings and all Python findings are blocked unless a valid temporary exception exists)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
