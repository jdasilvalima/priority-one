"""The tables: turn a snapshot into rows, store a run, read the latest one back, save actions.

Connection settings come from the standard PG* variables, so nobody builds an address by hand.
"""

from collections import defaultdict

import psycopg
from psycopg.rows import dict_row

COLUMNS = {
    "users": ("user_id", "name", "title"),
    "accounts": ("account_id", "name", "sub_vertical", "revenue_eur", "owner_id"),
    "source_exports": ("source", "as_of"),
    "scores": (
        "account_id", "rank", "tier", "score_raw", "score_display", "formula", "size_label",
        "size_multiplier", "action_text", "effort_minutes", "effort_band", "prepare",
    ),
    "signals": (
        "account_id", "sort_order", "signal_id", "label", "tier", "points", "sources",
        "evidence_text", "source_record_id", "headline_clause",
    ),
}
ORDER = {
    "users": "user_id",
    "accounts": "account_id",
    "source_exports": "source",
    "scores": "rank",
    "signals": "account_id, sort_order",
}
RUN_TABLES = ("source_exports", "scores", "signals")


class NoRunYet(Exception):
    """No sync has finished yet, so there is no week to show."""


def connect() -> psycopg.Connection:
    return psycopg.connect(row_factory=dict_row, connect_timeout=10)


def _pick(row: dict, table: str) -> dict:
    return {column: row[column] for column in COLUMNS[table]}


def rows_from_snapshot(snapshot: dict) -> dict[str, list[dict]]:
    return {
        "users": [_pick(snapshot["user"], "users")],
        "accounts": [_pick(account, "accounts") for account in snapshot["book"]],
        "source_exports": [{"source": source, "as_of": moment} for source, moment in snapshot["as_of"].items()],
        "scores": [_pick(row, "scores") for row in snapshot["accounts"]],
        "signals": [
            _pick({**signal, "account_id": row["account_id"], "sort_order": index}, "signals")
            for row in snapshot["accounts"]
            for index, signal in enumerate(row["signals"])
        ],
    }


def snapshot_from_rows(rows: dict[str, list[dict]]) -> dict:
    book = {account["account_id"]: account for account in rows["accounts"]}
    signals = defaultdict(list)
    for signal in rows["signals"]:
        signals[signal["account_id"]].append(signal)
    return {
        "user": rows["users"][0],
        "as_of": {row["source"]: row["as_of"] for row in rows["source_exports"]},
        "book": rows["accounts"],
        "accounts": [
            {**book[row["account_id"]], **row, "signals": signals[row["account_id"]]}
            for row in rows["scores"]
        ],
    }


def start_run(connection: psycopg.Connection) -> int:
    return connection.execute("insert into runs default values returning run_id").fetchone()["run_id"]


def finish_run(connection: psycopg.Connection, run_id: int) -> None:
    connection.execute("update runs set status = 'succeeded', finished_at = now() where run_id = %s", [run_id])


def fail_run(connection: psycopg.Connection, run_id: int, reason: str) -> None:
    connection.execute(
        "update runs set status = 'failed', finished_at = now(), error = %s where run_id = %s", [reason, run_id],
    )


def _upsert(connection: psycopg.Connection, table: str, key: str, rows: list[dict]) -> None:
    columns = COLUMNS[table]
    updates = ", ".join(f"{column} = excluded.{column}" for column in columns if column != key)
    query = (
        f"insert into {table} ({', '.join(columns)}) values ({', '.join(['%s'] * len(columns))}) "
        f"on conflict ({key}) do update set {updates}"
    )
    with connection.cursor() as cursor:
        cursor.executemany(query, [[row[column] for column in columns] for row in rows])


def write_rows(connection: psycopg.Connection, run_id: int, rows: dict[str, list[dict]]) -> None:
    _upsert(connection, "users", "user_id", rows["users"])
    _upsert(connection, "accounts", "account_id", rows["accounts"])
    with connection.cursor() as cursor:
        for table in RUN_TABLES:
            columns = COLUMNS[table]
            query = (
                f"insert into {table} (run_id, {', '.join(columns)}) "
                f"values ({', '.join(['%s'] * (len(columns) + 1))})"
            )
            cursor.executemany(query, [[run_id, *(row[column] for column in columns)] for row in rows[table]])


def latest_run(connection: psycopg.Connection) -> dict | None:
    return connection.execute(
        "select run_id, finished_at from runs where status = 'succeeded' order by run_id desc limit 1",
    ).fetchone()


def read_rows(connection: psycopg.Connection) -> dict[str, list[dict]]:
    run = latest_run(connection)
    if run is None:
        raise NoRunYet
    rows = {}
    for table, columns in COLUMNS.items():
        scope = "where run_id = %s" if table in RUN_TABLES else ""
        params = [run["run_id"]] if table in RUN_TABLES else None
        query = f"select {', '.join(columns)} from {table} {scope} order by {ORDER[table]}"
        rows[table] = connection.execute(query, params).fetchall()
    return rows


def read_actions(connection: psycopg.Connection, week: str) -> list[dict]:
    return connection.execute(
        "select account_id, kind, reason from account_actions where week = %s order by created_at", [week],
    ).fetchall()


def save_action(connection: psycopg.Connection, account_id: str, week: str, kind: str, reason: str | None) -> bool:
    """False when the account does not exist. Saved as the account's owner until single sign-on exists."""
    cursor = connection.execute(
        """
        insert into account_actions (account_id, week, kind, reason, user_id)
        select account_id, %s, %s, %s, owner_id from accounts where account_id = %s
        on conflict (account_id, week, kind) do update set reason = excluded.reason, created_at = now()
        """,
        [week, kind, reason, account_id],
    )
    return cursor.rowcount == 1


def undo_snooze(connection: psycopg.Connection, account_id: str, week: str) -> None:
    connection.execute(
        "delete from account_actions where account_id = %s and week = %s and kind = 'snoozed'", [account_id, week],
    )
