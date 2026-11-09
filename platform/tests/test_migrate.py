"""Only new migrations run, in file order."""

from pathlib import Path

from app.migrate import MIGRATIONS, pending


def test_pending_keeps_new_files_in_order():
    files = [Path("db/002_roles.sql"), Path("db/001_tables.sql"), Path("db/003_more.sql")]
    assert [f.name for f in pending({"001_tables.sql"}, files)] == ["002_roles.sql", "003_more.sql"]


def test_nothing_is_pending_when_all_ran():
    assert pending({"001_tables.sql"}, [Path("db/001_tables.sql")]) == []


def test_migration_files_exist():
    assert [f.name for f in pending(set(), list(MIGRATIONS.glob("*.sql")))] == ["001_tables.sql", "002_roles.sql"]


def test_no_password_is_stored_in_a_migration():
    for file in MIGRATIONS.glob("*.sql"):
        assert "password" not in file.read_text(encoding="utf-8").lower()
