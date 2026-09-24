from production_readiness import evaluate_readiness


def test_production_readiness_blocks_sqlite_and_wildcard_cors():
    findings = evaluate_readiness(
        app_env="production",
        database_url="sqlite:///app.db",
        cors_origins="*",
        app_version="1.0.0",
    )
    codes = {item.code for item in findings}
    assert {"DB-001", "WEB-001"} <= codes


def test_production_readiness_accepts_explicit_postgres_configuration():
    findings = evaluate_readiness(
        app_env="production",
        database_url="postgresql://db/app",
        cors_origins="https://clinic.example",
        app_version="1.0.0",
    )
    assert findings == []
