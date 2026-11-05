"""Write db/seed.sql: read the 5 JSON files, score the accounts, turn the result into SQL.

Run: python scripts/make_seed.py
Then run db/seed.sql in the Supabase SQL editor.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import rows_from_snapshot, seed_sql  # noqa: E402
from app.sources import load_playbook, load_raw  # noqa: E402
from app.week import DEMO_NOW, take_snapshot  # noqa: E402


def main() -> None:
    rows = rows_from_snapshot(take_snapshot(load_raw(), DEMO_NOW, load_playbook()))
    target = ROOT / "db" / "seed.sql"
    target.parent.mkdir(exist_ok=True)
    target.write_text(seed_sql(rows), encoding="utf-8", newline="\n")
    print(", ".join(f"{table}: {len(table_rows)}" for table, table_rows in rows.items()))


if __name__ == "__main__":
    main()
