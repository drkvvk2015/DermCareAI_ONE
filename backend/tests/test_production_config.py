import importlib
import os
import sys


def _reload_validator(monkeypatch, **values):
    for key in (
        "APP_ENV",
        "FIREBASE_AUTH_REQUIRED",
        "CORS_ORIGINS",
        "DATABASE_URL",
        "COMMERCE_DATABASE_URL",
        "CLINICAL_DATABASE_URL",
        "AUDIT_DATABASE_URL",
        "AI_GOVERNANCE_DATABASE_URL",
        "FIREBASE_SERVICE_ACCOUNT_JSON",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "CLOUDINARY_API_SECRET",
        "RAZORPAY_KEY_SECRET",
        "RAZORPAY_WEBHOOK_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    sys.modules.pop("scripts.check_production_config", None)
    return importlib.import_module("scripts.check_production_config")


def test_production_validator_accepts_postgres_and_adc(monkeypatch):
    module = _reload_validator(
        monkeypatch,
        APP_ENV="production",
        FIREBASE_AUTH_REQUIRED="true",
        CORS_ORIGINS="https://clinic.example.com",
        DATABASE_URL="postgresql+psycopg://user:pass@db/dermcareai",
        GOOGLE_CLOUD_PROJECT="dermcareai-prod",
        CLOUDINARY_API_SECRET="secret",
        RAZORPAY_KEY_SECRET="secret",
        RAZORPAY_WEBHOOK_SECRET="secret",
    )
    assert module.main() == 0


def test_production_validator_rejects_sqlite(monkeypatch):
    module = _reload_validator(
        monkeypatch,
        APP_ENV="production",
        FIREBASE_AUTH_REQUIRED="true",
        CORS_ORIGINS="https://clinic.example.com",
        DATABASE_URL="sqlite:///local.db",
        GOOGLE_CLOUD_PROJECT="dermcareai-prod",
        CLOUDINARY_API_SECRET="secret",
        RAZORPAY_KEY_SECRET="secret",
        RAZORPAY_WEBHOOK_SECRET="secret",
    )
    assert module.main() == 1
