"""Prove the read-only access works, with the real login.

Needs DATABASE_URL_READONLY in .env. Run: python scripts/check_db.py
It prints no password. It tries one write that changes nothing and must be refused.
"""

import json
import sys
from pathlib import Path
from urllib.parse import unquote

import psycopg

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import read_rows, snapshot_from_rows  # noqa: E402
from app.sources import load_playbook  # noqa: E402
from app.week import DEMO_NOW, render_week  # noqa: E402

KEY = "DATABASE_URL_READONLY"


def env_value(text: str, key: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def masked(text: str, url: str) -> str:
    """Read the password by hand: the driver cannot parse every address, and its errors quote them."""
    password = url.split("://", 1)[-1].rpartition("@")[0].partition(":")[2]
    for form in sorted({password, unquote(password)} - {""}, key=len, reverse=True):
        text = text.replace(form, "***")
    return text


def write_is_refused(url: str) -> bool:
    with psycopg.connect(url, prepare_threshold=None, connect_timeout=10) as connection:
        try:
            connection.execute("update users set title = title")
        except psycopg.errors.InsufficientPrivilege:
            return True
        connection.rollback()
        return False


def main() -> None:
    env_file = ROOT / ".env"
    url = env_value(env_file.read_text(encoding="utf-8"), KEY) if env_file.exists() else ""
    if not url:
        sys.exit(f"Fill {KEY} in .env first.")
    try:
        rows = read_rows(url)
        refused = write_is_refused(url)
    except psycopg.Error as error:
        sys.exit(f"Connection failed: {masked(str(error), url)}")

    week = json.loads(json.dumps(render_week(snapshot_from_rows(rows), DEMO_NOW, load_playbook())))
    page = json.loads((ROOT / "web" / "public" / "week.json").read_text(encoding="utf-8"))
    same = week == page
    print(f"Connected, {sum(len(table_rows) for table_rows in rows.values())} rows read")
    print(f"Same JSON as the page: {same}")
    print(f"Write refused: {refused}")
    sys.exit(0 if same and refused else 1)


if __name__ == "__main__":
    main()
