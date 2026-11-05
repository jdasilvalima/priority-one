"""The database only stores the week: what goes in comes back out unchanged."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.db import rows_from_snapshot, seed_sql, snapshot_from_rows
from app.sources import load_playbook, load_raw
from app.week import build_week, render_week, take_snapshot
from tests.builders import NOW

SEED = Path(__file__).resolve().parent.parent / "db" / "seed.sql"
NUMERIC_COLUMNS = ("score_raw", "size_multiplier")


@pytest.fixture(scope="module")
def snapshot():
    return take_snapshot(load_raw(), NOW, load_playbook())


@pytest.fixture(scope="module")
def rows(snapshot):
    return rows_from_snapshot(snapshot)


def as_postgres_returns_it(rows: dict) -> dict:
    """Postgres gives numeric columns back as Decimal, whatever went in."""
    return {
        table: [
            {k: Decimal(str(v)) if k in NUMERIC_COLUMNS else v for k, v in row.items()}
            for row in table_rows
        ]
        for table, table_rows in rows.items()
    }


def test_each_table_holds_the_expected_rows(rows):
    assert {table: len(table_rows) for table, table_rows in rows.items()} == {
        "users": 1, "accounts": 42, "sync_runs": 4, "scores": 8, "signals": 13,
    }


def test_week_read_from_rows_equals_week_built_from_files(rows):
    playbook = load_playbook()
    rebuilt = snapshot_from_rows(as_postgres_returns_it(rows))
    assert render_week(rebuilt, NOW, playbook) == build_week(load_raw(), NOW, playbook)


def test_signals_keep_their_order_inside_an_account(rows):
    northwind = [s for s in rows["signals"] if s["account_id"] == "001_northwind"]
    assert [s["sort_order"] for s in northwind] == list(range(len(northwind)))


def test_seed_empties_the_tables_before_filling_them(rows):
    sql = seed_sql(rows)
    assert sql.startswith("begin;\ntruncate users, accounts, sync_runs, scores, signals;\n")
    assert sql.endswith("commit;\n")


def test_seed_escapes_quotes():
    rows = {"users": [{"user_id": "u", "name": "O'Brien", "title": "AM"}]}
    assert "'O''Brien'" in seed_sql(rows)


def test_seed_writes_every_value_type():
    moment = datetime(2026, 11, 2, 7, 0, tzinfo=timezone.utc)
    rows = {"sync_runs": [{"source": "gong", "as_of": moment, "n": Decimal("1.5"), "tags": ["a"], "none": None}]}
    assert "('gong', '2026-11-02T07:00:00+00:00', 1.5, array['a']::text[], null)" in seed_sql(rows)


def test_seed_file_is_up_to_date(rows):
    assert SEED.read_text(encoding="utf-8") == seed_sql(rows)
