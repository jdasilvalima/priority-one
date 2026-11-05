"""GET /api/week: the only route, and what happens when the database is away."""

import json
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

import api.week as api
from app.db import rows_from_snapshot
from app.sources import load_playbook, load_raw
from app.week import DEMO_NOW, take_snapshot

SECRET_URL = "postgresql://week_reader:s3cret@pooler.example.com:6543/postgres"
PAGE_JSON = Path(__file__).resolve().parent.parent / "web" / "public" / "week.json"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_READONLY", SECRET_URL)
    return TestClient(api.app)


def test_week_is_the_json_the_page_expects(client, monkeypatch):
    rows = rows_from_snapshot(take_snapshot(load_raw(), DEMO_NOW, load_playbook()))
    monkeypatch.setattr(api, "read_rows", lambda url: rows)
    response = client.get("/api/week")
    assert response.status_code == 200
    assert response.json() == json.loads(PAGE_JSON.read_text(encoding="utf-8"))


def test_route_connects_with_the_read_only_address(client, monkeypatch):
    seen = []
    def remember(url):
        seen.append(url)
        raise psycopg.OperationalError("stop here")
    monkeypatch.setattr(api, "read_rows", remember)
    client.get("/api/week")
    assert seen == [SECRET_URL]


def test_database_failure_gives_503_without_the_address(client, monkeypatch):
    def fail(url):
        raise psycopg.OperationalError(f"could not connect to {url}")
    monkeypatch.setattr(api, "read_rows", fail)
    response = client.get("/api/week")
    assert response.status_code == 503
    assert "s3cret" not in response.text
    assert "pooler" not in response.text


def test_missing_setting_gives_503(client, monkeypatch):
    monkeypatch.delenv("DATABASE_URL_READONLY")
    assert client.get("/api/week").status_code == 503


def test_empty_database_gives_503(client, monkeypatch):
    empty = {"users": [], "accounts": [], "sync_runs": [], "scores": [], "signals": []}
    monkeypatch.setattr(api, "read_rows", lambda url: empty)
    assert client.get("/api/week").status_code == 503


@pytest.mark.parametrize("method", ["post", "put", "delete", "patch"])
def test_nothing_can_be_written(client, method):
    assert getattr(client, method)("/api/week").status_code == 405


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_no_generated_documentation_is_public(client, path):
    assert client.get(path).status_code == 404
