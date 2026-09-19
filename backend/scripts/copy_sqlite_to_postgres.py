from __future__ import annotations

import argparse
from urllib.parse import urlparse

from sqlalchemy import MetaData, create_engine, text


def normalize_postgres(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy selected SQLite tables into pre-created PostgreSQL schemas.")
    parser.add_argument("--source", required=True, help="SQLite SQLAlchemy URL, for example sqlite:///clinical.db")
    parser.add_argument("--target", required=True, help="PostgreSQL SQLAlchemy URL")
    parser.add_argument("--tables", required=True, help="Comma-separated table names to copy")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    if not args.source.startswith("sqlite://"):
        raise SystemExit("The source must be a SQLite SQLAlchemy URL.")
    target_url = normalize_postgres(args.target)
    if not target_url.startswith("postgresql+psycopg://"):
        raise SystemExit("The target must be PostgreSQL using psycopg.")

    source = create_engine(args.source, future=True)
    target = create_engine(target_url, future=True, pool_pre_ping=True)
    source_meta = MetaData()
    target_meta = MetaData()
    source_meta.reflect(bind=source)
    target_meta.reflect(bind=target)

    tables = [name.strip() for name in args.tables.split(",") if name.strip()]
    for name in tables:
        if name not in source_meta.tables:
            raise SystemExit(f"Source table not found: {name}")
        if name not in target_meta.tables:
            raise SystemExit(f"Target table not found. Run the PostgreSQL schema migration first: {name}")

        source_table = source_meta.tables[name]
        target_table = target_meta.tables[name]

        with source.connect() as src, target.begin() as dst:
            rows = src.execute(source_table.select()).mappings().all()
            if rows:
                dst.execute(target_table.insert(), [dict(row) for row in rows])

            if "id" in target_table.c and name == "audit_events":
                sequence = dst.execute(
                    text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
                    {"table_name": name},
                ).scalar()
                if sequence:
                    dst.execute(
                        text(
                            f"SELECT setval('{sequence}', "
                            "COALESCE((SELECT MAX(id) FROM audit_events), 1))"
                        )
                    )

        print(f"Copied {len(rows)} rows into {name}")

    print("SQLite to PostgreSQL migration completed.")


if __name__ == "__main__":
    main()
