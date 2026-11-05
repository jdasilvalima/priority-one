"""The 5 tables: turn a snapshot into rows, write the seed, read the rows back."""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

COLUMNS = {
    "users": ("user_id", "name", "title"),
    "accounts": ("account_id", "name", "sub_vertical", "revenue_eur", "owner_id"),
    "sync_runs": ("source", "as_of"),
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
    "sync_runs": "source",
    "scores": "rank",
    "signals": "account_id, sort_order",
}


def _pick(row: dict, table: str) -> dict:
    return {column: row[column] for column in COLUMNS[table]}


def rows_from_snapshot(snapshot: dict) -> dict[str, list[dict]]:
    return {
        "users": [_pick(snapshot["user"], "users")],
        "accounts": [_pick(account, "accounts") for account in snapshot["book"]],
        "sync_runs": [{"source": source, "as_of": moment} for source, moment in snapshot["as_of"].items()],
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
        "as_of": {row["source"]: row["as_of"] for row in rows["sync_runs"]},
        "book": rows["accounts"],
        "accounts": [
            {**book[row["account_id"]], **row, "signals": signals[row["account_id"]]}
            for row in rows["scores"]
        ],
    }


def _literal(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, list):
        return f"array[{', '.join(_literal(item) for item in value)}]::text[]"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, datetime):
        value = value.isoformat()
    return "'" + str(value).replace("'", "''") + "'"


def seed_sql(rows: dict[str, list[dict]]) -> str:
    lines = ["begin;", f"truncate {', '.join(COLUMNS)};"]
    for table in COLUMNS:
        table_rows = rows.get(table)
        if table_rows:
            values = ",\n".join(f"  ({', '.join(_literal(v) for v in row.values())})" for row in table_rows)
            lines.append(f"insert into {table} ({', '.join(table_rows[0])}) values\n{values};")
    lines.append("commit;")
    return "\n".join(lines) + "\n"


def read_rows(url: str) -> dict[str, list[dict]]:
    # prepare_threshold=None: the transaction pooler does not support prepared statements.
    with psycopg.connect(url, prepare_threshold=None, row_factory=dict_row, connect_timeout=10) as connection:
        return {
            table: connection.execute(f"select {', '.join(columns)} from {table} order by {ORDER[table]}").fetchall()
            for table, columns in COLUMNS.items()
        }
