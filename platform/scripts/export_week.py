"""Write demo/public/week.json from the 5 JSON files. This is the only link between the two folders.

Run: python scripts/export_week.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.sources import load_playbook, load_raw  # noqa: E402
from app.week import DEMO_NOW, build_week  # noqa: E402


def main() -> None:
    week = build_week(load_raw(), DEMO_NOW, load_playbook())
    target = ROOT.parent / "demo" / "public" / "week.json"
    target.write_text(json.dumps(week, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"week.json: {week['need_you_count']} accounts need Jade, {len(week['can_wait'])} can wait")


if __name__ == "__main__":
    main()
