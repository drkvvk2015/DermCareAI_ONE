from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in ("change-me", "changeme", "example.com", "placeholder", "staging-only"))


def _check_database_url(value: str, name: str = "DATABASE_URL") -> CheckResult:
    if not value:
        return CheckResult(name, "FAIL", f"{name} is required in production.")
    if not value.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")):
        return CheckResult(name, "FAIL", "Production persistence must use PostgreSQL.")
    if _looks_like_placeholder(value):
        return CheckResult(name, "FAIL", f"{name} contains a placeholder value.")
    return CheckResult(name, "PASS", "PostgreSQL connection string is configured.")


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

    # Each persistent store has its own production connection setting. Keep the legacy
    # DATABASE_URL check for deployments that still expose the shared alias, while
    # requiring the actual clinical and commerce store URLs when they are configured.
    results.append(_check_database_url(values.get("DATABASE_URL", "")))
    results.append(_check_database_url(values.get("CLINICAL_DATABASE_URL", values.get("DATABASE_URL", "")), "CLINICAL_DATABASE_URL"))
    results.append(_check_database_url(values.get("COMMERCE_DATABASE_URL", values.get("DATABASE_URL", "")), "COMMERCE_DATABASE_URL"))
    results.append(_check_cors(values.get("CORS_ORIGINS", "")))

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
