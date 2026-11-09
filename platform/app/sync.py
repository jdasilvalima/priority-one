"""One sync: fetch the 4 sources, score, store. A failure keeps the last good week."""

from collections.abc import Callable
from datetime import datetime, timedelta

import httpx
import psycopg

from app import db
from app.sources import SOURCE_NAMES
from app.week import take_snapshot


def is_due(last_finished: datetime | None, moment: datetime, every: timedelta) -> bool:
    return last_finished is None or moment - last_finished >= every


def fetch_raw(base_url: str, transport: httpx.BaseTransport | None = None) -> dict:
    with httpx.Client(base_url=base_url, transport=transport, timeout=30) as client:
        return {name: client.get(f"/{name}").raise_for_status().json() for name in SOURCE_NAMES}


def sync_once(connection: psycopg.Connection, fetch: Callable[[], dict], now: datetime, playbook: dict) -> bool:
    run_id = db.start_run(connection)
    connection.commit()
    try:
        rows = db.rows_from_snapshot(take_snapshot(fetch(), now, playbook))
        db.write_rows(connection, run_id, rows)
        db.finish_run(connection, run_id)
    except (httpx.HTTPError, ValueError, KeyError, IndexError, psycopg.Error) as error:
        connection.rollback()
        # Only the error type: a message can quote an address or a customer record.
        db.fail_run(connection, run_id, type(error).__name__)
        connection.commit()
        return False
    connection.commit()
    return True
