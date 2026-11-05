"""Write web/public/week.json from the 5 JSON files, for the page without an API.

Run: python scripts/export_week.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.sources import load_playbook, load_raw  # noqa: E402
from app.week import build_week  # noqa: E402

DEMO_NOW = datetime(2026, 11, 2, 7, 12, tzinfo=timezone.utc)


def main() -> None:
    week = build_week(load_raw(), DEMO_NOW, load_playbook())
    target = ROOT / "web" / "public" / "week.json"
    target.write_text(json.dumps(week, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"week.json: {week['need_you_count']} accounts need Rosa, {len(week['can_wait'])} can wait")


if __name__ == "__main__":
    main()
