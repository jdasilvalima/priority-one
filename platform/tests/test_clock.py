"""Which moment the scoring uses, and how a week is named."""

from datetime import datetime, timezone

from app.clock import scoring_now, week_key
from app.week import DEMO_NOW


def test_fixed_clock_for_the_mock_sources(monkeypatch):
    monkeypatch.setenv("SCORING_CLOCK", "2026-11-02T07:12:00+00:00")
    assert scoring_now() == DEMO_NOW


def test_real_clock_when_nothing_is_set(monkeypatch):
    monkeypatch.delenv("SCORING_CLOCK", raising=False)
    before = datetime.now(timezone.utc)
    assert before <= scoring_now() <= datetime.now(timezone.utc)


def test_empty_setting_means_the_real_clock(monkeypatch):
    monkeypatch.setenv("SCORING_CLOCK", "")
    before = datetime.now(timezone.utc)
    assert before <= scoring_now() <= datetime.now(timezone.utc)


def test_week_key():
    assert week_key(DEMO_NOW) == "2026-W45"


def test_week_key_pads_and_uses_the_iso_year():
    assert week_key(datetime(2027, 1, 3, tzinfo=timezone.utc)) == "2026-W53"
    assert week_key(datetime(2027, 1, 4, tzinfo=timezone.utc)) == "2027-W01"
