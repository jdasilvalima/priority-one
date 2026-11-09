"""The demo folder is a frozen copy of this scoring."""

import json
from pathlib import Path

from app.sources import load_playbook, load_raw
from app.week import DEMO_NOW, build_week

DEMO_WEEK = Path(__file__).resolve().parent.parent.parent / "demo" / "public" / "week.json"


def test_demo_page_shows_exactly_what_this_scoring_computes():
    week = json.loads(json.dumps(build_week(load_raw(), DEMO_NOW, load_playbook())))
    assert json.loads(DEMO_WEEK.read_text(encoding="utf-8")) == week
