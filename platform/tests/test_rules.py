"""Each of the 9 rules: one case on each side of its threshold."""

from datetime import timedelta

import pytest

from app.rules import run_rules
from app.sources import load_playbook
from tests.builders import (
    NOW, TODAY, call, case, champion, contract, job_change, make_facts, meeting,
    opportunity, payment, payments, survey,
)

ESCALATED = "sig_escalated_case"
DROP = "sig_auth_or_volume_drop"
COMPETITOR = "sig_competitor_named"
RENEWAL = "sig_renewal_no_opp"
CHAMPION = "sig_champion_left"
RAMP = "sig_ramp_below_commit"
CASES = "sig_cases_piling_up"
SURVEY = "sig_low_satisfaction"
NO_CONTACT = "sig_no_contact_60d"


@pytest.fixture(scope="module")
def playbook():
    return load_playbook()


def fired(playbook, **overrides) -> set[str]:
    return {s["signal_id"] for s in run_rules(make_facts(**overrides), NOW, playbook)}


def signal(playbook, signal_id, **overrides) -> dict:
    return next(s for s in run_rules(make_facts(**overrides), NOW, playbook) if s["signal_id"] == signal_id)


def test_default_account_fires_nothing(playbook):
    assert fired(playbook) == set()


# 1. Escalated case
@pytest.mark.parametrize("fields", [
    {"escalated": True},
    {"priority": "Urgent"},
    {"violated": True},
])
def test_open_serious_case_fires(playbook, fields):
    assert ESCALATED in fired(playbook, cases=[case(**fields)])


def test_closed_escalated_case_does_not_fire(playbook):
    assert ESCALATED not in fired(playbook, cases=[case(escalated=True, closed=True)])


def test_ordinary_open_case_does_not_fire(playbook):
    assert ESCALATED not in fired(playbook, cases=[case()])


def test_two_urgent_cases_count_as_one_signal(playbook):
    cases = [case(priority="Urgent", number="1"), case(priority="Urgent", number="2")]
    signals = run_rules(make_facts(cases=cases), NOW, playbook)
    assert [s["signal_id"] for s in signals].count(ESCALATED) == 1


# 2. Auth rate or volume drop
def test_auth_rate_down_2_points_fires(playbook):
    rows = payments(recent={"approved": 8800}, baseline={"approved": 9000})
    assert DROP in fired(playbook, payments=rows)


def test_auth_rate_down_under_2_points_does_not_fire(playbook):
    rows = payments(recent={"approved": 8810}, baseline={"approved": 9000})
    assert DROP not in fired(playbook, payments=rows)


def test_volume_down_20_percent_fires(playbook):
    rows = payments(recent={"volume": 800.0}, baseline={"volume": 1000.0})
    assert DROP in fired(playbook, payments=rows)


def test_volume_down_under_20_percent_does_not_fire(playbook):
    rows = payments(recent={"volume": 810.0}, baseline={"volume": 1000.0})
    assert DROP not in fired(playbook, payments=rows)


def test_auth_rate_is_sum_over_sum_not_average_of_days(playbook):
    # Mean of daily rates: (50% + 90 x 6) / 7 = 84.3%, which would fire. Weighted by attempts: 89.9%.
    rows = [payment(1, attempts=10, approved=5)] + [payment(age) for age in range(2, 36)]
    assert DROP not in fired(playbook, payments=rows)


def test_no_payment_rows_does_not_fire(playbook):
    assert DROP not in fired(playbook, payments=[])


def test_days_without_attempts_do_not_crash(playbook):
    rows = payments(recent={"attempts": 0, "approved": 0})
    assert DROP not in fired(playbook, payments=rows)


def test_todays_partial_row_is_ignored(playbook):
    rows = payments() + [payment(0, volume=1.0, attempts=100, approved=1)]
    assert DROP not in fired(playbook, payments=rows)


# 3. Competitor named
def test_competitor_on_call_14_days_ago_fires(playbook):
    assert COMPETITOR in fired(playbook, calls=[call(14, competitors=2)])


def test_competitor_on_call_15_days_ago_does_not_fire(playbook):
    assert COMPETITOR not in fired(playbook, calls=[call(15, competitors=2)])


def test_tracker_count_zero_does_not_fire(playbook):
    assert COMPETITOR not in fired(playbook, calls=[call(3, competitors=0)])


def test_other_tracker_does_not_fire(playbook):
    assert COMPETITOR not in fired(playbook, calls=[call(3, competitors=4, tracker="Pricing")])


# 4. Renewal
def test_contract_ending_in_90_days_fires(playbook):
    assert RENEWAL in fired(playbook, contracts=[contract(90)])


def test_contract_ending_in_91_days_does_not_fire(playbook):
    assert RENEWAL not in fired(playbook, contracts=[contract(91)])


def test_contract_already_ended_does_not_fire(playbook):
    assert RENEWAL not in fired(playbook, contracts=[contract(-1)])


def test_open_renewal_opportunity_does_not_fire(playbook):
    assert RENEWAL not in fired(playbook, contracts=[contract(30)], opportunities=[opportunity()])


def test_closed_renewal_opportunity_fires(playbook):
    assert RENEWAL in fired(playbook, contracts=[contract(30)], opportunities=[opportunity(closed=True)])


def test_open_upsell_opportunity_fires(playbook):
    assert RENEWAL in fired(playbook, contracts=[contract(30)], opportunities=[opportunity(kind="Upsell")])


# 5. Champion left
def test_champion_left_90_days_ago_fires(playbook):
    assert CHAMPION in fired(playbook, contacts=[champion()], job_changes=[job_change(90)])


def test_champion_left_91_days_ago_does_not_fire(playbook):
    assert CHAMPION not in fired(playbook, contacts=[champion()], job_changes=[job_change(91)])


def test_other_contact_leaving_does_not_fire(playbook):
    assert CHAMPION not in fired(playbook, contacts=[champion()], job_changes=[job_change(contact_id="003_other")])


def test_champion_promotion_does_not_fire(playbook):
    assert CHAMPION not in fired(playbook, contacts=[champion()], job_changes=[job_change(change_type="promoted")])


# 6. Ramp below commitment
def ramp_facts(days_live: int, volume_30_days: float, commitment: float = 3000.0) -> dict:
    return dict(
        go_live=TODAY - timedelta(days=days_live),
        contracts=[contract(400, commitment)],
        payments=[payment(age, volume=volume_30_days / 30) for age in range(1, 31)],
    )


def test_25_percent_below_after_60_days_fires(playbook):
    assert RAMP in fired(playbook, **ramp_facts(60, 2250.0))


def test_24_percent_below_does_not_fire(playbook):
    assert RAMP not in fired(playbook, **ramp_facts(60, 2280.0))


def test_59_days_after_go_live_does_not_fire(playbook):
    assert RAMP not in fired(playbook, **ramp_facts(59, 1000.0))


def test_no_commitment_does_not_fire(playbook):
    facts = ramp_facts(90, 1000.0)
    facts["contracts"] = [contract(400, None)]
    assert RAMP not in fired(playbook, **facts)


def test_no_go_live_date_does_not_fire(playbook):
    facts = ramp_facts(90, 1000.0)
    facts["go_live"] = None
    assert RAMP not in fired(playbook, **facts)


def test_no_volume_data_does_not_fire(playbook):
    facts = ramp_facts(90, 1000.0)
    facts["payments"] = []
    assert RAMP not in fired(playbook, **facts)


# 7. Cases piling up
def test_three_cases_in_30_days_fires(playbook):
    assert CASES in fired(playbook, cases=[case(1), case(10), case(30)])


def test_two_cases_in_30_days_does_not_fire(playbook):
    assert CASES not in fired(playbook, cases=[case(1), case(10)])


def test_third_case_at_31_days_does_not_fire(playbook):
    assert CASES not in fired(playbook, cases=[case(1), case(10), case(31)])


def test_closed_cases_still_count(playbook):
    assert CASES in fired(playbook, cases=[case(1, closed=True), case(2, closed=True), case(3, closed=True)])


# 8. Low satisfaction
def test_score_6_fires(playbook):
    assert SURVEY in fired(playbook, surveys=[survey(6)])


def test_score_7_does_not_fire(playbook):
    assert SURVEY not in fired(playbook, surveys=[survey(7)])


def test_only_latest_score_counts(playbook):
    assert SURVEY not in fired(playbook, surveys=[survey(3, age_days=90), survey(9, age_days=5)])


def test_no_survey_does_not_fire(playbook):
    assert SURVEY not in fired(playbook, surveys=[])


# 9. No contact
def test_last_call_60_days_ago_fires(playbook):
    assert NO_CONTACT in fired(playbook, calls=[call(60)])


def test_last_call_59_days_ago_does_not_fire(playbook):
    assert NO_CONTACT not in fired(playbook, calls=[call(59)])


def test_recent_meeting_counts_as_contact(playbook):
    assert NO_CONTACT not in fired(playbook, calls=[call(70)], meetings=[meeting(10)])


def test_future_meeting_is_not_contact(playbook):
    assert NO_CONTACT in fired(playbook, calls=[call(70)], meetings=[meeting(-7)])


def test_no_history_at_all_fires(playbook):
    assert NO_CONTACT in fired(playbook, calls=[], meetings=[])


# What the "why" shows
def test_signal_carries_tier_points_and_source_record(playbook):
    result = signal(playbook, ESCALATED, cases=[case(priority="Urgent", number="00481523")])
    assert result["tier"] == "Critical"
    assert result["points"] == 50
    assert result["source_record_id"] == "500_00481523"
    assert result["sources"] == ["salesforce"]


@pytest.mark.parametrize("cases,expected", [
    ([case(priority="Urgent", number="1")], "1 urgent case (case 1)"),
    ([case(priority="Urgent", number="1"), case(priority="Urgent", number="2")], "2 urgent cases (case 1)"),
    ([case(violated=True, late_days=1, kind="Payout")], "Payout case 1 day past SLA"),
])
def test_escalated_evidence_wording(playbook, cases, expected):
    assert signal(playbook, ESCALATED, cases=cases)["evidence_text"] == expected


def test_volume_drop_evidence(playbook):
    rows = payments(recent={"volume": 700.0}, baseline={"volume": 1000.0})
    assert signal(playbook, DROP, payments=rows)["evidence_text"] == "Volume down 30% vs baseline"


def test_no_history_evidence(playbook):
    assert signal(playbook, NO_CONTACT, calls=[], meetings=[])["evidence_text"] == "No call or meeting on record"
