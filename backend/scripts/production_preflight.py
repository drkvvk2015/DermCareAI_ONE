from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_release_evidence import validate_ai_release_manifest


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in ("change-me", "changeme", "example.com", "placeholder", "staging-only"))


def _check_database_url(value: str) -> CheckResult:
    if not value:
        return CheckResult("DATABASE_URL", "FAIL", "DATABASE_URL is required in production.")
    if not value.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")):
        return CheckResult("DATABASE_URL", "FAIL", "Production persistence must use PostgreSQL.")
    if _looks_like_placeholder(value):
        return CheckResult("DATABASE_URL", "FAIL", "DATABASE_URL contains a placeholder value.")
    return CheckResult("DATABASE_URL", "PASS", "PostgreSQL connection string is configured.")


def _check_cors(value: str) -> CheckResult:
    origins = [item.strip() for item in value.split(",") if item.strip()]
    if not origins or "*" in origins:
        return CheckResult("CORS_ORIGINS", "FAIL", "Production CORS_ORIGINS must explicitly list approved origins.")
    invalid = [origin for origin in origins if urlparse(origin).scheme != "https"]
    if invalid:
        return CheckResult("CORS_ORIGINS", "FAIL", "Production origins must use HTTPS.")
    return CheckResult("CORS_ORIGINS", "PASS", f"{len(origins)} explicit HTTPS origin(s) configured.")


def evaluate_environment(env: Mapping[str, str] | None = None) -> list[CheckResult]:
    values = os.environ if env is None else env
    results: list[CheckResult] = []

    app_env = values.get("APP_ENV", "")
    results.append(CheckResult("APP_ENV", "PASS" if app_env == "production" else "FAIL", "APP_ENV must be exactly 'production'."))

    auth_required = values.get("FIREBASE_AUTH_REQUIRED", "").lower()
    results.append(
        CheckResult(
            "FIREBASE_AUTH_REQUIRED",
            "PASS" if auth_required == "true" else "FAIL",
            "Firebase authentication must be enforced in production.",
        )
    )

    app_version = values.get("APP_VERSION", "").strip()
    results.append(
        CheckResult(
            "APP_VERSION",
            "PASS" if app_version and not app_version.lower().startswith(("dev", "0.0.0")) else "FAIL",
            "A non-development application version is required.",
        )
    )

    results.append(_check_database_url(values.get("DATABASE_URL", "")))
    results.append(_check_cors(values.get("CORS_ORIGINS", "")))

    privacy_approved = values.get("PRIVACY_OPERATIONS_APPROVED", "false").lower() == "true"
    policy_version = values.get("PRIVACY_POLICY_VERSION", "").strip()
    results.append(
        CheckResult(
            "PRIVACY_OPERATIONS_APPROVED",
            "PASS" if privacy_approved and bool(policy_version) and not _looks_like_placeholder(policy_version) else "FAIL",
            "A clinic-approved privacy operations runbook and version must be recorded before production use.",
        )
    )

    firebase_configured = bool(
        values.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        or values.get("GOOGLE_APPLICATION_CREDENTIALS")
        or values.get("GOOGLE_CLOUD_PROJECT")
    )
    results.append(
        CheckResult(
            "Firebase credentials",
            "PASS" if firebase_configured else "FAIL",
            "Provide Firebase service-account JSON, ADC credentials, or a Google Cloud project identity.",
        )
    )

    embedded = values.get("ENABLE_EMBEDDED_DERM_MODEL", "false").lower()
    results.append(
        CheckResult(
            "ENABLE_EMBEDDED_DERM_MODEL",
            "PASS" if embedded == "false" else "FAIL",
            "The embedded research model must not be enabled in production.",
        )
    )

    if values.get("AI_ENABLED_IN_PRODUCTION", "false").lower() == "true":
        manifest_path = values.get("AI_RELEASE_MANIFEST_PATH", "").strip()
        if not manifest_path:
            results.append(CheckResult("AI release evidence", "FAIL", "AI_RELEASE_MANIFEST_PATH is required when production AI is enabled."))
        else:
            try:
                manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
                problems = validate_ai_release_manifest(manifest)
            except (OSError, json.JSONDecodeError) as exc:
                problems = [f"Evidence manifest cannot be read: {exc}"]
            if problems:
                results.append(CheckResult("AI release evidence", "FAIL", "Evidence package is incomplete: " + "; ".join(problems[:4])))
            else:
                results.append(CheckResult("AI release evidence", "PASS", "Approved evidence package is structurally complete; model identity is checked at runtime."))
    else:
        results.append(CheckResult("AI release evidence", "PASS", "Production AI is disabled; no clinical evidence package is required."))

    try:
        confidence = float(values.get("MIN_CONFIDENCE", "0.70"))
        confidence_ok = 0.0 <= confidence <= 1.0
    except ValueError:
        confidence_ok = False
    results.append(
        CheckResult(
            "MIN_CONFIDENCE",
            "PASS" if confidence_ok else "FAIL",
            "MIN_CONFIDENCE must be numeric and within [0, 1].",
        )
    )

    try:
        max_image_bytes = int(values.get("MAX_IMAGE_BYTES", str(12 * 1024 * 1024)))
        image_limit_ok = 0 < max_image_bytes <= 20 * 1024 * 1024
    except ValueError:
        image_limit_ok = False
    results.append(
        CheckResult(
            "MAX_IMAGE_BYTES",
            "PASS" if image_limit_ok else "FAIL",
            "MAX_IMAGE_BYTES must be a positive integer no larger than 20 MiB.",
        )
    )

    optional_integrations = {
        "Razorpay": (
            values.get("RAZORPAY_KEY_ID"),
            values.get("RAZORPAY_KEY_SECRET"),
            values.get("RAZORPAY_WEBHOOK_SECRET"),
        ),
        "WhatsApp": (
            values.get("META_WHATSAPP_ACCESS_TOKEN"),
            values.get("META_WHATSAPP_PHONE_NUMBER_ID"),
        ),
        "SMS": (
            values.get("SMS_PROVIDER_URL"),
            values.get("SMS_PROVIDER_TOKEN"),
            values.get("SMS_SENDER_ID"),
        ),
    }
    for name, parts in optional_integrations.items():
        configured = all(parts)
        partial = any(parts) and not configured
        status = "PASS" if configured or not partial else "WARN"
        detail = "Optional integration configured." if configured else (
            "Optional integration is not configured." if not partial else "Optional integration is partially configured."
        )
        results.append(CheckResult(name, status, detail))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DermCareAI production configuration without printing secrets.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    results = evaluate_environment()
    failed = any(item.status == "FAIL" for item in results)

    if args.json:
        print(json.dumps([item.__dict__ for item in results], indent=2))
    else:
        for item in results:
            print(f"[{item.status}] {item.name}: {item.detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
