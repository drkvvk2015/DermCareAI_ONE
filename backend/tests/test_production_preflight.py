from scripts.production_preflight import evaluate_environment


def base_env() -> dict[str, str]:
    return {
        "APP_ENV": "production",
        "APP_VERSION": "5.1.0",
        "FIREBASE_AUTH_REQUIRED": "true",
        "DATABASE_URL": "postgresql+psycopg://app:strong-secret@db.example/dermcareai",
        "CLINICAL_DATABASE_URL": "postgresql+psycopg://app:strong-secret@clinical-db.example/dermcareai",
        "COMMERCE_DATABASE_URL": "postgresql+psycopg://app:strong-secret@commerce-db.example/dermcareai",
        "CORS_ORIGINS": "https://clinic.example.com,https://admin.example.com",
        "GOOGLE_CLOUD_PROJECT": "dermcareai-prod",
        "ENABLE_EMBEDDED_DERM_MODEL": "false",
        "MIN_CONFIDENCE": "0.70",
        "MAX_IMAGE_BYTES": "12582912",
    }


def statuses(env: dict[str, str]) -> dict[str, str]:
    return {item.name: item.status for item in evaluate_environment(env)}


def test_production_baseline_passes_required_checks() -> None:
    result = statuses(base_env())
    assert result["APP_ENV"] == "PASS"
    assert result["FIREBASE_AUTH_REQUIRED"] == "PASS"
    assert result["DATABASE_URL"] == "PASS"
    assert result["CLINICAL_DATABASE_URL"] == "PASS"
    assert result["COMMERCE_DATABASE_URL"] == "PASS"
    assert result["CORS_ORIGINS"] == "PASS"
    assert result["Firebase credentials"] == "PASS"
    assert result["ENABLE_EMBEDDED_DERM_MODEL"] == "PASS"


def test_rejects_sqlite_and_wildcard_cors() -> None:
    env = base_env()
    env["DATABASE_URL"] = "sqlite:///clinical.db"
    env["CORS_ORIGINS"] = "*"
    result = statuses(env)
    assert result["DATABASE_URL"] == "FAIL"
    assert result["CORS_ORIGINS"] == "FAIL"


def test_rejects_research_model_in_production() -> None:
    env = base_env()
    env["ENABLE_EMBEDDED_DERM_MODEL"] = "true"
    assert statuses(env)["ENABLE_EMBEDDED_DERM_MODEL"] == "FAIL"


def test_rejects_http_origins() -> None:
    env = base_env()
    env["CORS_ORIGINS"] = "https://clinic.example.com,http://localhost:8081"
    assert statuses(env)["CORS_ORIGINS"] == "FAIL"


def test_optional_integrations_can_be_absent_or_partial_without_failing_core_gate() -> None:
    env = base_env()
    env["RAZORPAY_KEY_ID"] = "id"
    env["RAZORPAY_KEY_SECRET"] = "secret"
    result = statuses(env)
    assert result["Razorpay"] == "WARN"


def test_placeholder_database_is_rejected() -> None:
    env = base_env()
    env["DATABASE_URL"] = "postgresql+psycopg://app:staging-only-change-me@db.example/dermcareai"
    assert statuses(env)["DATABASE_URL"] == "FAIL"
