import os
import pytest
from sqlalchemy import create_engine


def test_clinical_store_requires_postgres_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CLINICAL_DATABASE_URL", "sqlite:///should-not-be-used.db")
    from storage import require_postgres_in_production
    with pytest.raises(RuntimeError):
        require_postgres_in_production(create_engine("sqlite:///:memory:"), "Clinical store")
