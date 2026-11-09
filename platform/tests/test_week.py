"""What the page receives. One JSON, already worded for the screen."""

import json
from datetime import datetime, timezone

import pytest

from app.sources import load_playbook, load_raw
from app.week import build_week, effort_label, fresh_label, money_label, scoring_guide
from tests.builders import NOW


@pytest.fixture(scope="module")
def week():
    return build_week(load_raw(), NOW, load_playbook())


@pytest.fixture(scope="module")
def cards(week):
    return {c["account_id"]: c for group in week["groups"] for c in group["cards"]}


def at(hour: int, minute: int = 0, day: int = 2, month: int = 11) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=timezone.utc)


def test_page_is_plain_json(week):
    json.dumps(week)


def test_header(week):
    assert week["user"] == {"name": "Jade D.", "initials": "JD", "title": "Account Manager", "account_count": 42}
    assert week["week_label"] == "Week 45 · Mon 2 Nov 2026"


def test_title_count_and_old_alerts(week):
    assert week["need_you_count"] == 5
    assert week["alerts"] == {"total": 38, "tools": 5}


def test_source_pills_in_design_order(week):
    assert week["sources"] == [
        {"label": "Salesforce", "fresh": "12 min ago"},
        {"label": "Payments DB", "fresh": "06:00"},
        {"label": "Clay", "fresh": "yesterday"},
        {"label": "Gong", "fresh": "06:00"},
    ]


def test_groups_are_critical_then_high_with_continuous_ranks(week):
    assert [g["tier"] for g in week["groups"]] == ["Critical", "High"]
    assert [c["rank"] for g in week["groups"] for c in g["cards"]] == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("account,headline", [
    ("001_northwind", "Approvals fell 6.2 pts and 2 urgent cases are open."),
    ("001_kestrel", "A competitor was named on the last call and the renewal is in 39 days."),
    ("001_halcyon", "A payout case is 4 days past SLA and nobody has spoken to them in 63 days."),
    ("001_pico", "Your champion left in October and the renewal is in 64 days."),
    ("001_vantor", "75 days after go-live, volume is 38% below what they committed."),
])
def test_headline(cards, account, headline):
    assert cards[account]["headline"] == headline


@pytest.mark.parametrize("account,meta", [
    ("001_northwind", "Fashion e-commerce · €2.4M / yr"),
    ("001_kestrel", "Online travel · €3.1M / yr"),
    ("001_halcyon", "Hospitality · €420k / yr"),
    ("001_pico", "Subscription boxes · €310k / yr"),
    ("001_vantor", "Online gaming · €1.6M / yr"),
])
def test_line_under_the_name(cards, account, meta):
    assert cards[account]["meta"] == meta


@pytest.mark.parametrize("account,prepare", [
    ("001_northwind", "decline analysis and call notes"),
    ("001_kestrel", "meeting invite and value review"),
    ("001_pico", "intro email draft"),
])
def test_prepare_line_lists_what_to_get_ready(cards, account, prepare):
    assert cards[account]["prepare"] == prepare


@pytest.mark.parametrize("account,effort", [
    ("001_northwind", "Medium · ~45 min"),
    ("001_kestrel", "Heavy · ~3 h"),
    ("001_vantor", "Medium · ~1 h"),
    ("001_pico", "Quick · ~10 min"),
])
def test_effort_on_the_card(cards, account, effort):
    assert cards[account]["effort"] == effort


def test_signal_rows_name_their_source_and_freshness(cards):
    assert cards["001_northwind"]["signals"][0] == {
        "label": "Auth rate or volume drop", "tier": "Critical", "points": 50,
        "evidence": "Auth rate 82.1%, down 6.2 pts vs baseline", "source": "Payments DB", "fresh": "06:00",
    }
    assert cards["001_pico"]["signals"][0]["source"] == "Clay"
    assert cards["001_pico"]["signals"][0]["fresh"] == "yesterday"
    assert cards["001_kestrel"]["signals"][0]["source"] == "Gong"


def test_calculation_uses_equals_when_exact(cards):
    assert cards["001_kestrel"]["equation"] == "(50 + 30) × 2 = 160"


def test_calculation_uses_about_when_rounded(cards):
    assert cards["001_halcyon"]["equation"] == "(50 + 5) × 1.5 ≈ 83"


def test_card_explains_the_size_multiplier(cards):
    assert cards["001_kestrel"]["size_label"] == "Large, over €1M / yr"
    assert cards["001_kestrel"]["size_multiplier"] == "2"
    assert cards["001_halcyon"]["size_multiplier"] == "1.5"


def test_can_wait_lists_medium_and_low(week):
    assert week["can_wait"] == [
        {"account_id": "001_lumen", "name": "Lumen Mobility", "tier": "Medium",
         "summary": "4 cases in 30 days · survey score 5", "equation": "(15 + 15) × 1.5 = 45"},
        {"account_id": "001_bloom", "name": "Bloom & Co Grocers", "tier": "Medium",
         "summary": "Survey score 6", "equation": "15 × 1 = 15"},
        {"account_id": "001_orbit", "name": "Orbit Ticketing", "tier": "Low",
         "summary": "No call or meeting in 70 days", "equation": "5 × 1.5 ≈ 8"},
    ]


def test_healthy_count(week):
    assert week["healthy_count"] == 34


@pytest.mark.parametrize("as_of,label", [
    (at(7, 0), "12 min ago"),
    (at(5, 0), "06:00"),
    (at(21, 0, day=1), "yesterday"),
    (at(9, 0, day=30, month=10), "30 Oct"),
])
def test_fresh_label(as_of, label):
    assert fresh_label(as_of, at(7, 12)) == label


@pytest.mark.parametrize("revenue,label", [
    (85000, "€85k / yr"),
    (1000000, "€1M / yr"),
    (2400000, "€2.4M / yr"),
])
def test_money_label(revenue, label):
    assert money_label(revenue) == label


@pytest.mark.parametrize("minutes,band,label", [
    (10, "Quick", "Quick · ~10 min"),
    (60, "Medium", "Medium · ~1 h"),
    (90, "Heavy", "Heavy · ~1.5 h"),
    (180, "Heavy", "Heavy · ~3 h"),
])
def test_effort_label(minutes, band, label):
    assert effort_label(minutes, band) == label


def issue(scoring: dict, label: str) -> dict:
    return next(i for tier in scoring["tiers"] for i in tier["issues"] if i["label"] == label)


def test_each_issue_is_worth_the_points_of_its_tier(week):
    worth = {i["label"]: tier["points"] for tier in week["scoring"]["tiers"] for i in tier["issues"]}
    assert worth == {
        "Auth rate or volume drop": 50,
        "Escalated support case": 50,
        "Competitor named on a call": 50,
        "Champion left": 30,
        "Renewal within 90 days": 30,
        "Ramp below commitment": 30,
        "Support cases piling up": 15,
        "Low satisfaction score": 15,
        "No call in 60+ days": 5,
    }


def test_scoring_tiers_run_from_most_to_least_serious(week):
    assert [t["tier"] for t in week["scoring"]["tiers"]] == ["Critical", "High", "Medium", "Low"]


def test_scoring_gives_the_size_multipliers(week):
    assert week["scoring"]["sizes"] == [
        {"label": "Small, under €100k / yr", "multiplier": "1"},
        {"label": "Medium, €100k–1M / yr", "multiplier": "1.5"},
        {"label": "Large, over €1M / yr", "multiplier": "2"},
    ]


def test_scoring_names_where_each_issue_comes_from(week):
    assert issue(week["scoring"], "Ramp below commitment")["sources"] == "Payments DB, Salesforce"
    assert issue(week["scoring"], "Competitor named on a call")["sources"] == "Gong"


def test_scoring_explains_when_an_issue_counts_with_the_real_thresholds(week):
    assert issue(week["scoring"], "Competitor named on a call")["when"] == (
        "A competitor was named on a call in the last 14 days"
    )
    assert issue(week["scoring"], "Auth rate or volume drop")["when"] == (
        "Last 7 days vs the previous 28: auth rate down 2 pts or more, or daily volume down 20% or more"
    )


def test_every_threshold_used_by_a_rule_is_shown_to_the_am():
    for signal in load_playbook()["signals"]:
        for name in signal.get("params", {}):
            assert f"{{{name}}}" in signal["rule"], f"{signal['signal_id']} hides {name}"


def test_changing_the_points_changes_the_scoring_page():
    playbook = load_playbook()
    playbook["tier_points"]["Critical"] = 40
    assert scoring_guide(playbook)["tiers"][0]["points"] == 40


def test_changing_a_threshold_changes_the_scoring_page():
    playbook = load_playbook()
    signal = next(s for s in playbook["signals"] if s["signal_id"] == "sig_competitor_named")
    signal["params"]["lookback_days"] = 10
    assert "last 10 days" in issue(scoring_guide(playbook), "Competitor named on a call")["when"]
