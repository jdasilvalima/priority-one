"""The real stack, through the web server, with the real database.

Run after docker compose up: STACK_URL=http://localhost:8080 python -m pytest tests/test_stack.py
"""

import os

import httpx
import pytest

STACK_URL = os.environ.get("STACK_URL")
PASSWORD = os.environ.get("STACK_PASSWORD", "change-me-page")

pytestmark = pytest.mark.skipif(not STACK_URL, reason="needs a running stack")


@pytest.fixture(scope="module")
def signed_in():
    with httpx.Client(base_url=STACK_URL) as client:
        assert client.post("/api/login", json={"password": PASSWORD}).status_code == 204
        yield client


@pytest.fixture
def stranger():
    with httpx.Client(base_url=STACK_URL) as client:
        yield client


def cards(week: dict) -> dict:
    return {card["name"]: card for group in week["groups"] for card in group["cards"]}


def account_id(client: httpx.Client, name: str) -> str:
    return cards(client.get("/api/week").json())[name]["account_id"]


def test_page_is_served_with_security_headers(stranger):
    response = stranger.get("/")
    assert response.status_code == 200
    assert '<div id="root">' in response.text
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_health_says_the_first_sync_is_done(stranger):
    assert stranger.get("/api/health").json() == {"status": "ok"}


def test_week_needs_a_session(stranger):
    assert stranger.get("/api/week").status_code == 401


def test_writing_needs_a_session(stranger):
    assert stranger.post("/api/accounts/001_northwind/actions", json={"kind": "logged"}).status_code == 401


def test_the_scores_come_back_from_the_database(signed_in):
    scores = {name: card["score"] for name, card in cards(signed_in.get("/api/week").json()).items()}
    assert scores == {
        "Northwind Apparel": 200, "Kestrel Travel Group": 160, "Halcyon Hotels": 83,
        "Pico Subscriptions": 90, "Vantor Gaming": 60,
    }


def test_logging_an_account_is_written_and_read_back(signed_in):
    target = account_id(signed_in, "Pico Subscriptions")
    assert signed_in.post(f"/api/accounts/{target}/actions", json={"kind": "logged"}).status_code == 204
    assert cards(signed_in.get("/api/week").json())["Pico Subscriptions"]["logged"] is True


def test_flag_is_written_and_read_back(signed_in):
    target = account_id(signed_in, "Vantor Gaming")
    body = {"kind": "flagged", "reason": "Wrong next step"}
    assert signed_in.post(f"/api/accounts/{target}/actions", json=body).status_code == 204
    assert cards(signed_in.get("/api/week").json())["Vantor Gaming"]["flagged"] == "Wrong next step"


def test_snooze_leaves_the_list_and_undo_brings_it_back(signed_in):
    target = account_id(signed_in, "Halcyon Hotels")
    assert signed_in.post(f"/api/accounts/{target}/actions", json={"kind": "snoozed"}).status_code == 204
    week = signed_in.get("/api/week").json()
    assert week["need_you_count"] == 4
    assert "Halcyon Hotels" not in cards(week)
    assert signed_in.delete(f"/api/accounts/{target}/snooze").status_code == 204
    assert signed_in.get("/api/week").json()["need_you_count"] == 5


def test_unknown_account_is_404(signed_in):
    assert signed_in.post("/api/accounts/001_unknown/actions", json={"kind": "logged"}).status_code == 404


def test_login_guesses_are_limited_last_in_this_file(stranger):
    codes = [stranger.post("/api/login", json={"password": "guess"}).status_code for _ in range(12)]
    assert codes[0] == 401
    assert codes[-1] == 429
