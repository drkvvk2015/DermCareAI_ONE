from production_readiness import evaluate_readiness


def test_production_readiness_requires_both_postgres_stores_and_auth():
    findings = evaluate_readiness(
        app_env="production",
        database_url="sqlite:///clinical.db",
        commerce_database_url="sqlite:///commerce.db",
        cors_origins="*",
        app_version="5.1.0",
        firebase_auth_required=False,
    )
    codes = {item.code for item in findings}
    assert {"DB-001", "DB-002", "WEB-001", "AUTH-001"} <= codes


def test_production_readiness_accepts_explicit_postgres_contract():
    findings = evaluate_readiness(
        app_env="production",
        database_url="postgresql+psycopg://clinical/example",
        commerce_database_url="postgresql+psycopg://commerce/example",
        cors_origins="https://clinic.example",
        app_version="5.1.0",
        firebase_auth_required=True,
        redis_configured=True,
    )
    assert findings == []

def test_production_readiness_requires_redis_for_distributed_rate_limiting():
    findings = evaluate_readiness(
        app_env="production",
        database_url="postgresql+psycopg://clinical/example",
        commerce_database_url="postgresql+psycopg://commerce/example",
        cors_origins="https://clinic.example",
        app_version="5.1.0",
        firebase_auth_required=True,
        redis_configured=False,
    )
    assert any(item.code == "RATE-001" for item in findings)
