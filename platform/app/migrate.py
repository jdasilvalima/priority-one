"""Bring the database up to date with the owner's login. Runs once, before the other services."""

import os
from pathlib import Path

import psycopg
from psycopg import sql

MIGRATIONS = Path(__file__).resolve().parent.parent / "db"
ROLE_SECRETS = {"priority_api": "API_DB_PASSWORD", "priority_sync": "SYNC_DB_PASSWORD"}


def pending(applied: set[str], files: list[Path]) -> list[Path]:
    return sorted((file for file in files if file.name not in applied), key=lambda file: file.name)


def main() -> None:
    with psycopg.connect(connect_timeout=10) as connection:
        connection.execute(
            "create table if not exists schema_migrations "
            "(name text primary key, applied_at timestamptz not null default now())",
        )
        applied = {row[0] for row in connection.execute("select name from schema_migrations")}
        for file in pending(applied, list(MIGRATIONS.glob("*.sql"))):
            connection.execute(file.read_text(encoding="utf-8"))
            connection.execute("insert into schema_migrations (name) values (%s)", [file.name])
            print(f"applied {file.name}", flush=True)
        for role, variable in ROLE_SECRETS.items():
            connection.execute(
                sql.SQL("alter role {} password {}").format(sql.Identifier(role), sql.Literal(os.environ[variable])),
            )
    print("database ready", flush=True)


if __name__ == "__main__":
    main()
