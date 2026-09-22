from __future__ import annotations

import os
import sys
from urllib.parse import urlparse


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def main() -> int:
    problems: list[str] = []
    env = os.getenv("APP_ENV", "development").lower()

    if env != "production":
        print(f"Configuration check completed for APP_ENV={env}.")
        return 0

    if os.getenv("FIREBASE_AUTH_REQUIRED", "true").lower() != "true":
        problems.append("FIREBASE_AUTH_REQUIRED must be true in production.")

    cors = os.getenv("CORS_ORIGINS", "").strip()
    if not cors or cors == "*" or "localhost" in cors:
        problems.append("CORS_ORIGINS must explicitly list approved production origins.")

    database_urls = {
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "COMMERCE_DATABASE_URL": os.getenv("COMMERCE_DATABASE_URL"),
        "CLINICAL_DATABASE_URL": os.getenv("CLINICAL_DATABASE_URL"),
        "AUDIT_DATABASE_URL": os.getenv("AUDIT_DATABASE_URL"),
        "AI_GOVERNANCE_DATABASE_URL": os.getenv("AI_GOVERNANCE_DATABASE_URL"),
    }

    for name, value in database_urls.items():
        effective = value or database_urls["DATABASE_URL"]
        if not effective:
            problems.append(f"{name} is missing and no DATABASE_URL fallback is configured.")
            continue
        scheme = urlparse(effective).scheme
        if not scheme.startswith("postgresql") and scheme != "postgres":
            problems.append(f"{name} must resolve to PostgreSQL in production.")

    if not any(
        os.getenv(name)
        for name in ("FIREBASE_SERVICE_ACCOUNT_JSON", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT")
    ):
        problems.append(
            "Firebase Admin credentials are missing. Configure FIREBASE_SERVICE_ACCOUNT_JSON, "
            "GOOGLE_APPLICATION_CREDENTIALS, or workload identity/GOOGLE_CLOUD_PROJECT."
        )

    for name in ("CLOUDINARY_API_SECRET", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET"):
        if not os.getenv(name):
            problems.append(f"{name} is missing.")

    if problems:
        for problem in problems:
            fail(problem)
        return 1

    print("Production configuration contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
