"""Score = sum of churn points x client size. Nothing else changes it."""

from decimal import Decimal

import pytest

from app.scoring import pick_action, rank, score
from app.sources import load_playbook
from tests.builders import job_change, make_facts, primary

CRITICAL = {"signal_id": "sig_competitor_named", "tier": "Critical", "points": 50}
HIGH = {"signal_id": "sig_renewal_no_opp", "tier": "High", "points": 30}
LOW = {"signal_id": "sig_no_contact_60d", "tier": "Low", "points": 5}


@pytest.fixture(scope="module")
def playbook():
    return load_playbook()


def test_adds_points_then_multiplies_by_size(playbook):
    result = score([CRITICAL, HIGH], 3100000, playbook)
    assert result["points_sum"] == 80
    assert result["size_multiplier"] == Decimal("2")
    assert result["score_raw"] == Decimal("160")
    assert result["formula"] == "(50 + 30) × 2"


def test_single_signal_formula_has_no_brackets(playbook):
    assert score([HIGH], 1600000, playbook)["formula"] == "30 × 2"


@pytest.mark.parametrize("points,revenue,raw,display", [
    ([CRITICAL, LOW], 420000, "82.5", 83),
    ([LOW], 260000, "7.5", 8),
])
def test_half_rounds_up_for_display_only(playbook, points, revenue, raw, display):
    result = score(points, revenue, playbook)
    assert result["score_raw"] == Decimal(raw)
    assert result["score_display"] == display


@pytest.mark.parametrize("revenue,band,multiplier", [
    (99999, "Small", "1"),
    (100000, "Medium", "1.5"),
    (1000000, "Medium", "1.5"),
    (1000001, "Large", "2"),
])
def test_size_band_limits(playbook, revenue, band, multiplier):
    result = score([HIGH], revenue, playbook)
    assert result["size_band"] == band
    assert result["size_multiplier"] == Decimal(multiplier)


def test_tier_is_the_highest_fired(playbook):
    assert score([LOW, CRITICAL], 500000, playbook)["tier"] == "Critical"


def test_first_matching_action_wins(playbook):
    facts = make_facts(contacts=[primary()])
    result = pick_action([CRITICAL, HIGH], facts, playbook)
    assert result["action_id"] == "act_renewal_exec_meeting"
    assert result["action_text"] == "Book a renewal meeting with Marc Dubois (CFO) and your manager"
    assert result["effort_minutes"] == 180
    assert result["effort_band"] == "Heavy"


def test_new_contact_comes_from_the_replacement(playbook):
    left = {"signal_id": "sig_champion_left", "tier": "High", "points": 30}
    change = job_change(replacement={"name": "Tom Hughes", "title": "Head of Payments"})
    result = pick_action([left], make_facts(job_changes=[change]), playbook)
    assert result["action_text"] == "Send an intro email to Tom Hughes"


def test_missing_primary_contact_is_not_guessed(playbook):
    result = pick_action([LOW], make_facts(contacts=[]), playbook)
    assert result["action_text"] == "Send your main contact a check-in email and propose a QBR"


@pytest.mark.parametrize("minutes,band", [(20, "Quick"), (21, "Medium"), (60, "Medium"), (61, "Heavy")])
def test_effort_band_limits(minutes, band):
    from app.scoring import effort_band
    assert effort_band(minutes, load_playbook()) == band


def test_every_signal_has_an_action(playbook):
    alone = {a["when_all"][0] for a in playbook["actions"] if len(a["when_all"]) == 1}
    assert {s["signal_id"] for s in playbook["signals"]} <= alone


def row(account_id, tier, raw, minutes):
    return {"account_id": account_id, "tier": tier, "score_raw": Decimal(raw), "effort_minutes": minutes}


def order(rows, playbook):
    return [r["account_id"] for r in rank(rows, playbook)]


def test_tier_beats_score(playbook):
    assert order([row("a", "High", "90", 10), row("b", "Critical", "83", 20)], playbook) == ["b", "a"]


def test_higher_score_first_inside_a_tier(playbook):
    assert order([row("a", "High", "60", 10), row("b", "High", "90", 10)], playbook) == ["b", "a"]


def test_equal_score_puts_less_effort_first(playbook):
    assert order([row("a", "High", "60", 60), row("b", "High", "60", 10)], playbook) == ["b", "a"]


def test_full_tie_uses_account_id(playbook):
    assert order([row("b", "High", "60", 10), row("a", "High", "60", 10)], playbook) == ["a", "b"]


def test_rank_starts_at_1(playbook):
    ranked = rank([row("a", "High", "60", 10), row("b", "High", "90", 10)], playbook)
    assert [(r["account_id"], r["rank"]) for r in ranked] == [("b", 1), ("a", 2)]
