"""The 5 JSON files, read end to end, must give the page in the design."""

from decimal import Decimal
from pathlib import Path

import pytest

from app.scoring import compute_run
from app.sources import load_playbook, load_raw
from tests.builders import NOW

ROOT = Path(__file__).resolve().parent.parent

# rank, account, signals, tier, raw score, shown score, formula, action, minutes, effort
EXPECTED = [
    (1, "001_northwind", {"sig_auth_or_volume_drop", "sig_escalated_case"}, "Critical", "200", 200,
     "(50 + 50) × 2", "act_auth_analysis_call", 45, "Medium"),
    (2, "001_kestrel", {"sig_competitor_named", "sig_renewal_no_opp"}, "Critical", "160", 160,
     "(50 + 30) × 2", "act_renewal_exec_meeting", 180, "Heavy"),
    (3, "001_halcyon", {"sig_escalated_case", "sig_no_contact_60d"}, "Critical", "82.5", 83,
     "(50 + 5) × 1.5", "act_escalated_call", 20, "Quick"),
    (4, "001_pico", {"sig_champion_left", "sig_renewal_no_opp"}, "High", "90", 90,
     "(30 + 30) × 1.5", "act_new_contact_intro", 10, "Quick"),
    (5, "001_vantor", {"sig_ramp_below_commit"}, "High", "60", 60,
     "30 × 2", "act_ramp_review", 60, "Medium"),
    (6, "001_lumen", {"sig_cases_piling_up", "sig_low_satisfaction"}, "Medium", "45", 45,
     "(15 + 15) × 1.5", "act_case_review", 30, "Medium"),
    (7, "001_bloom", {"sig_low_satisfaction"}, "Medium", "15", 15,
     "15 × 1", "act_feedback_call", 30, "Medium"),
    (8, "001_orbit", {"sig_no_contact_60d"}, "Low", "7.5", 8,
     "5 × 1.5", "act_checkin_email", 10, "Quick"),
]

EVIDENCE = {
    "001_northwind": ["Auth rate 82.1%, down 6.2 pts vs baseline", "2 urgent cases, 1 past SLA (case 00481523)"],
    "001_kestrel": ["Competitor named on 30 Oct QBR", "Renews 11 Dec, no renewal opportunity open"],
    "001_halcyon": ["Payout case 4 days past SLA", "No call or meeting in 63 days"],
    "001_pico": ["Head of Payments left, Tom Hughes took over", "Renews 5 Jan, no renewal opportunity open"],
    "001_vantor": ["Processed volume 38% below commitment"],
    "001_lumen": ["4 cases in 30 days", "Survey score 5"],
    "001_bloom": ["Survey score 6"],
    "001_orbit": ["No call or meeting in 70 days"],
}

ACTION_TEXT = {
    "001_northwind": "Call Jana Weber (Head of Payments Ops) today",
    "001_kestrel": "Book a renewal meeting with Marc Dubois (CFO) and your manager",
    "001_halcyon": "Call Siobhan Kelly (Finance Director) with a fix date from Support",
    "001_pico": "Send an intro email to Tom Hughes",
    "001_vantor": "Ramp review with Erik Lund (COO): what is not live yet?",
}


@pytest.fixture(scope="module")
def playbook():
    return load_playbook()


@pytest.fixture(scope="module")
def raw():
    return load_raw()


@pytest.fixture(scope="module")
def run(raw, playbook):
    return compute_run(raw, NOW, playbook)


@pytest.fixture(scope="module")
def by_id(run):
    return {a["account_id"]: a for a in run["accounts"]}


@pytest.mark.parametrize("rank,account,signals,tier,raw_score,display,formula,action,minutes,effort", EXPECTED)
def test_account_matches_design(by_id, rank, account, signals, tier, raw_score, display, formula, action, minutes, effort):
    result = by_id[account]
    assert {s["signal_id"] for s in result["signals"]} == signals
    assert result["tier"] == tier
    assert result["rank"] == rank
    assert result["score_raw"] == Decimal(raw_score)
    assert result["score_display"] == display
    assert result["formula"] == formula
    assert result["action_id"] == action
    assert result["effort_minutes"] == minutes
    assert result["effort_band"] == effort


@pytest.mark.parametrize("account,expected", EVIDENCE.items())
def test_evidence_matches_design(by_id, account, expected):
    assert [s["evidence_text"] for s in by_id[account]["signals"]] == expected


@pytest.mark.parametrize("account,expected", ACTION_TEXT.items())
def test_action_text_matches_design(by_id, account, expected):
    assert by_id[account]["action_text"] == expected


def test_only_the_8_stories_fire(run):
    assert {a["account_id"] for a in run["accounts"]} == {row[1] for row in EXPECTED}


def test_34_healthy_accounts_fire_nothing(run):
    assert run["healthy_count"] == 34


def test_5_accounts_need_jade_and_3_can_wait(run, playbook):
    listed = [a for a in run["accounts"] if a["tier"] in playbook["list_tiers"]]
    assert len(listed) == 5
    assert len(run["accounts"]) - len(listed) == 3


def test_13_signals_fire_in_total(run):
    assert sum(len(a["signals"]) for a in run["accounts"]) == 13


# The data files themselves
def test_book_has_42_accounts_owned_by_jade(raw):
    accounts = raw["salesforce"]["accounts"]["records"]
    assert len(accounts) == 42
    assert {a["OwnerId"] for a in accounts} == {"005_jade"}


def test_salesforce_has_8_lists(raw):
    lists = {k for k in raw["salesforce"] if k != "as_of"}
    assert lists == {"accounts", "users", "contact_roles", "contracts", "opportunities", "cases", "events", "surveys"}


def test_payments_has_63_days_for_each_account(raw):
    rows = raw["payments"]["rows"]
    assert len(rows) == 2646
    codes = {a["Merchant_Account_Code__c"] for a in raw["salesforce"]["accounts"]["records"]}
    assert {r["merchant_account_code"] for r in rows} == codes
    assert len({r["date"] for r in rows}) == 63


def test_data_dates_are_set(raw):
    assert raw["salesforce"]["as_of"] == "2026-11-02T07:00:00Z"
    assert raw["gong"]["as_of"] == "2026-11-02T05:00:00Z"
    assert raw["payments"]["exported_at"] == "2026-11-02T05:00:00Z"
    assert max(e["detected_at"] for e in raw["clay"]["events"]) == "2026-11-01T21:00:00Z"


def test_playbook_has_9_rules_and_10_actions(playbook):
    assert len(playbook["signals"]) == 9
    assert len(playbook["actions"]) == 10


@pytest.mark.parametrize("path", [
    "config/playbook.json", "data/salesforce.json", "data/gong.json", "data/clay.json", "data/payments.json",
])
def test_employer_name_is_not_in_the_files(path):
    assert ("ad" + "yen") not in (ROOT / path).read_text(encoding="utf-8").lower()
