"""One sync: fetch the 4 sources, score, store. A failure keeps the last good week."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app import sync
from app.sources import SOURCE_NAMES, load_playbook, load_raw
from app.week import DEMO_NOW

MOMENT = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
EVERY = timedelta(minutes=60)


class FakeConnection:
    def __init__(self):
        self.log = []

    def commit(self):
        self.log.append("commit")

    def rollback(self):
        self.log.append("rollback")


@pytest.fixture
def connection(monkeypatch):
    fake = FakeConnection()
    monkeypatch.setattr(sync.db, "start_run", lambda c: c.log.append("start") or 7)
    monkeypatch.setattr(sync.db, "write_rows", lambda c, run, rows: c.log.append(("write", run, len(rows["scores"]))))
    monkeypatch.setattr(sync.db, "finish_run", lambda c, run: c.log.append(("finish", run)))
    monkeypatch.setattr(sync.db, "fail_run", lambda c, run, reason: c.log.append(("fail", run, reason)))
    return fake


def test_first_start_on_an_empty_database_syncs():
    assert sync.is_due(None, MOMENT, EVERY)


def test_recent_run_is_not_repeated():
    assert not sync.is_due(MOMENT - timedelta(minutes=59), MOMENT, EVERY)


def test_run_is_due_after_the_interval():
    assert sync.is_due(MOMENT - EVERY, MOMENT, EVERY)


def test_good_sync_writes_then_marks_the_run_finished(connection):
    assert sync.sync_once(connection, load_raw, DEMO_NOW, load_playbook())
    assert connection.log == ["start", "commit", ("write", 7, 8), ("finish", 7), "commit"]


def test_source_failure_marks_the_run_failed_and_writes_nothing(connection):
    def unreachable():
        raise httpx.ConnectError("no route to sources:8001")

    assert not sync.sync_once(connection, unreachable, DEMO_NOW, load_playbook())
    assert connection.log == ["start", "commit", "rollback", ("fail", 7, "ConnectError"), "commit"]


def test_broken_export_marks_the_run_failed(connection):
    assert not sync.sync_once(connection, lambda: {"salesforce": {}}, DEMO_NOW, load_playbook())
    assert ("fail", 7, "KeyError") in connection.log


def test_fetch_reads_every_source_over_http():
    raw = load_raw()
    seen = []

    def answer(request: httpx.Request) -> httpx.Response:
        name = request.url.path.strip("/")
        seen.append(name)
        return httpx.Response(200, json=raw[name])

    fetched = sync.fetch_raw("http://sources:8001", httpx.MockTransport(answer))
    assert fetched == raw
    assert sorted(seen) == sorted(SOURCE_NAMES)


def test_fetch_raises_when_a_source_answers_with_an_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        sync.fetch_raw("http://sources:8001", transport)
