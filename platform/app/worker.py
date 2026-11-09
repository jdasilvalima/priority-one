"""The sync service. On an empty database it syncs at once, then every SYNC_EVERY_MINUTES."""

import os
import time
from datetime import datetime, timedelta, timezone
from functools import partial

import psycopg

from app import db, sync
from app.clock import scoring_now
from app.sources import load_playbook

CHECK_SECONDS = 60


def tick(every: timedelta, sources_url: str) -> None:
    with db.connect() as connection:
        last = db.latest_run(connection)
        if not sync.is_due(last["finished_at"] if last else None, datetime.now(timezone.utc), every):
            return
        succeeded = sync.sync_once(connection, partial(sync.fetch_raw, sources_url), scoring_now(), load_playbook())
        print(f"sync {'succeeded' if succeeded else 'failed'}", flush=True)


def main() -> None:
    every = timedelta(minutes=int(os.environ.get("SYNC_EVERY_MINUTES", "60")))
    sources_url = os.environ["SOURCES_URL"]
    while True:
        try:
            tick(every, sources_url)
        except psycopg.Error as error:
            print(f"sync skipped: {type(error).__name__}", flush=True)
        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    main()
