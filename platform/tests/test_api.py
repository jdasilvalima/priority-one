"""The API behind the page: login, reading the week, saving what the Account Manager does."""

import json
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import api
from app.db import NoRunYet, rows_from_snapshot
from app.sources import load_playbook, load_raw
from app.week import DEMO_NOW, take_snapshot

PASSWORD = "open-sesame"
DEMO_WEEK = Path(__file__).resolve().parent.parent.parent / "demo" / "public" / "week.json"


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def store(monkeypatch):
    """The database, replaced by a list. The real one is covered by tests/test_stack.py."""
    saved = []
    rows = rows_from_snapshot(take_snapshot(load_raw(), DEMO_NOW, load_playbook()))
    monkeypatch.setenv("APP_PASSWORD", PASSWORD)
    monkeypatch.setenv("SESSION_SECRET", "a-long-random-secret")
    monkeypatch.setenv("SCORING_CLOCK", DEMO_NOW.isoformat())
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.setattr(api.db, "connect", FakeConnection)
    monkeypatch.setattr(api.db, "read_rows", lambda c: rows)
    monkeypatch.setattr(api.db, "read_actions", lambda c, week: [a for a in saved if a["week"] == week])
    monkeypatch.setattr(api.db, "latest_run", lambda c: {"run_id": 1})

    def save(connection, account_id, week, kind, reason):
        if account_id == "001_unknown":
            return False
        saved.append({"account_id": account_id, "week": week, "kind": kind, "reason": reason})
        return True

    def undo(connection, account_id, week):
        saved[:] = [a for a in saved if not (a["account_id"] == account_id and a["kind"] == "snoozed")]

    monkeypatch.setattr(api.db, "save_action", save)
    monkeypatch.setattr(api.db, "undo_snooze", undo)
    return saved


@pytest.fixture
def client(store):
    return TestClient(api.app)


@pytest.fixture
def signed_in(client):
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 204
    return client


def test_right_password_sets_a_protected_cookie(client):
    cookie = client.post("/api/login", json={"password": PASSWORD}).headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Secure" not in cookie


def test_cookie_is_secure_when_the_site_uses_https(client, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    assert "Secure" in client.post("/api/login", json={"password": PASSWORD}).headers["set-cookie"]


def test_wrong_password_gets_no_cookie(client):
    response = client.post("/api/login", json={"password": "nope"})
    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_week_needs_a_session(client):
    assert client.get("/api/week").status_code == 401


def test_forged_cookie_is_refused(client):
    client.cookies.set("session", "9999999999.forged")
    assert client.get("/api/week").status_code == 401


def test_logout_ends_the_session(signed_in):
    assert signed_in.post("/api/logout").status_code == 204
    assert signed_in.get("/api/week").status_code == 401


def test_week_is_the_demo_week_plus_the_action_state(signed_in):
    week = signed_in.get("/api/week").json()
    demo = json.loads(DEMO_WEEK.read_text(encoding="utf-8"))
    assert week["snoozed"] == []
    assert week["need_you_count"] == demo["need_you_count"]
    assert week["scoring"] == demo["scoring"]
    names = [c["name"] for g in week["groups"] for c in g["cards"]]
    assert names == [c["name"] for g in demo["groups"] for c in g["cards"]]


@pytest.mark.parametrize("method,path", [
    ("post", "/api/accounts/001_northwind/actions"),
    ("delete", "/api/accounts/001_northwind/snooze"),
])
def test_writing_needs_a_session(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_logging_an_account_is_saved_for_this_week(signed_in, store):
    response = signed_in.post("/api/accounts/001_northwind/actions", json={"kind": "logged"})
    assert response.status_code == 204
    assert store == [{"account_id": "001_northwind", "week": "2026-W45", "kind": "logged", "reason": None}]


def test_snoozing_then_undoing_restores_the_list(signed_in):
    signed_in.post("/api/accounts/001_northwind/actions", json={"kind": "snoozed"})
    assert signed_in.get("/api/week").json()["need_you_count"] == 4
    assert signed_in.delete("/api/accounts/001_northwind/snooze").status_code == 204
    assert signed_in.get("/api/week").json()["need_you_count"] == 5


def test_flag_needs_a_reason(signed_in):
    assert signed_in.post("/api/accounts/001_northwind/actions", json={"kind": "flagged"}).status_code == 422


def test_flag_keeps_the_reason(signed_in, store):
    body = {"kind": "flagged", "reason": "Wrong next step"}
    assert signed_in.post("/api/accounts/001_northwind/actions", json=body).status_code == 204
    assert store[0]["reason"] == "Wrong next step"


def test_reason_length_is_limited(signed_in):
    body = {"kind": "flagged", "reason": "x" * 201}
    assert signed_in.post("/api/accounts/001_northwind/actions", json=body).status_code == 422


def test_unknown_kind_is_refused(signed_in):
    assert signed_in.post("/api/accounts/001_northwind/actions", json={"kind": "deleted"}).status_code == 422


def test_unknown_account_is_404(signed_in):
    assert signed_in.post("/api/accounts/001_unknown/actions", json={"kind": "logged"}).status_code == 404


def test_database_failure_gives_503_without_details(signed_in, monkeypatch):
    def fail(connection):
        raise psycopg.OperationalError("could not connect to host db as priority_api")

    monkeypatch.setattr(api.db, "read_rows", fail)
    response = signed_in.get("/api/week")
    assert response.status_code == 503
    assert "priority_api" not in response.text


def test_no_finished_sync_gives_503(signed_in, monkeypatch):
    def nothing(connection):
        raise NoRunYet

    monkeypatch.setattr(api.db, "read_rows", nothing)
    assert signed_in.get("/api/week").status_code == 503


def test_health_is_public_and_says_when_data_is_ready(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_health_is_503_until_the_first_sync_ends(client, monkeypatch):
    monkeypatch.setattr(api.db, "latest_run", lambda c: None)
    assert client.get("/api/health").status_code == 503


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_no_generated_documentation_is_public(client, path):
    assert client.get(path).status_code == 404
