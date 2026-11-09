"""What the Account Manager did this week changes what the page shows."""

import pytest

from app.sources import load_playbook, load_raw
from app.week import DEMO_NOW, apply_actions, build_week


@pytest.fixture(scope="module")
def week():
    return build_week(load_raw(), DEMO_NOW, load_playbook())


def action(account_id: str, kind: str, reason: str | None = None) -> dict:
    return {"account_id": account_id, "kind": kind, "reason": reason}


def cards(week: dict) -> dict:
    return {card["account_id"]: card for group in week["groups"] for card in group["cards"]}


def test_no_action_keeps_the_list_and_adds_empty_state(week):
    page = apply_actions(week, [])
    assert page["need_you_count"] == 5
    assert page["snoozed"] == []
    assert cards(page)["001_northwind"]["logged"] is False
    assert cards(page)["001_northwind"]["flagged"] is None


def test_logged_account_stays_on_the_list_and_is_marked(week):
    page = apply_actions(week, [action("001_northwind", "logged")])
    assert page["need_you_count"] == 5
    assert cards(page)["001_northwind"]["logged"] is True


def test_flagged_account_shows_the_reason(week):
    page = apply_actions(week, [action("001_northwind", "flagged", "Wrong next step")])
    assert cards(page)["001_northwind"]["flagged"] == "Wrong next step"


def test_snoozed_account_leaves_the_list(week):
    page = apply_actions(week, [action("001_northwind", "snoozed")])
    assert page["need_you_count"] == 4
    assert "001_northwind" not in cards(page)
    assert page["snoozed"] == [{"account_id": "001_northwind", "name": "Northwind Apparel"}]


def test_a_group_with_every_card_snoozed_disappears(week):
    critical = next(g for g in week["groups"] if g["tier"] == "Critical")
    page = apply_actions(week, [action(c["account_id"], "snoozed") for c in critical["cards"]])
    assert [g["tier"] for g in page["groups"]] == ["High"]


def test_the_week_itself_is_not_changed(week):
    apply_actions(week, [action("001_northwind", "snoozed")])
    assert week["need_you_count"] == 5
    assert "snoozed" not in week
