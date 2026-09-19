from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, Result


def database_url(url_env: str, path_env: str, default_path: str) -> str:
    raw = os.getenv(url_env) or os.getenv("DATABASE_URL")
    if raw:
        normalized = raw.strip()
        if normalized.startswith("postgres://"):
            normalized = "postgresql+psycopg://" + normalized[len("postgres://"):]
        elif normalized.startswith("postgresql://"):
            normalized = "postgresql+psycopg://" + normalized[len("postgresql://"):]
        return normalized

    path = Path(os.getenv(path_env, default_path))
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


def create_store_engine(url_env: str, path_env: str, default_path: str) -> Engine:
    url = database_url(url_env, path_env, default_path)
    kwargs: dict[str, Any] = {
        "future": True,
        "pool_pre_ping": True,
    }
    if url.startswith("sqlite://"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update({"pool_size": 5, "max_overflow": 10, "pool_recycle": 1800})
    return create_engine(url, **kwargs)


def is_sqlite(engine: Engine) -> bool:
    return engine.url.get_backend_name() == "sqlite"


def is_postgres(engine: Engine) -> bool:
    return engine.url.get_backend_name() == "postgresql"


def require_postgres_in_production(engine: Engine, store_name: str) -> None:
    if os.getenv("APP_ENV", "development").lower() == "production" and is_sqlite(engine):
        raise RuntimeError(
            f"{store_name} is configured with SQLite in production. "
            "Set DATABASE_URL or the store-specific database URL to managed PostgreSQL."
        )


@contextmanager
def transaction(engine: Engine) -> Iterator[Connection]:
    with engine.begin() as conn:
        yield conn


def execute(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> Result[Any]:
    return conn.execute(text(sql), params or {})
