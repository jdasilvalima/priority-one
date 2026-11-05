"""The one JSON the page reads. Everything is already worded for the screen."""

from datetime import datetime, timedelta, timezone

from app.rules import MONTHS, short_date
from app.scoring import compute_run

# The demo clock is fixed on a Monday in November, so Amsterdam is always UTC+1 here.
AMSTERDAM = timezone(timedelta(hours=1))
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def fresh_label(as_of: datetime, now: datetime) -> str:
    local_as_of, local_now = as_of.astimezone(AMSTERDAM), now.astimezone(AMSTERDAM)
    days = (local_now.date() - local_as_of.date()).days
    minutes = int((now - as_of).total_seconds() // 60)
    if days == 0:
        return f"{minutes} min ago" if minutes < 60 else local_as_of.strftime("%H:%M")
    return "yesterday" if days == 1 else short_date(local_as_of.date())


def money_label(eur: float) -> str:
    if eur >= 1_000_000:
        millions = f"{eur / 1_000_000:.1f}".removesuffix(".0")
        return f"€{millions}M / yr"
    return f"€{round(eur / 1000)}k / yr"


def effort_label(minutes: int, band: str) -> str:
    if minutes < 60:
        return f"{band} · ~{minutes} min"
    hours = f"{minutes / 60:.1f}".removesuffix(".0")
    return f"{band} · ~{hours} h"


def _as_of_by_source(raw: dict) -> dict[str, datetime]:
    return {
        "salesforce": datetime.fromisoformat(raw["salesforce"]["as_of"]),
        "gong": datetime.fromisoformat(raw["gong"]["as_of"]),
        "payments": datetime.fromisoformat(raw["payments"]["exported_at"]),
        "clay": datetime.fromisoformat(max(e["detected_at"] for e in raw["clay"]["events"])),
    }


def _sentence(clauses: list[str]) -> str:
    text = " and ".join(clauses)
    return text[0].upper() + text[1:] + "."


def _equation(row: dict) -> str:
    exact = row["score_raw"] == row["score_display"]
    return f"{row['formula']} {'=' if exact else '≈'} {row['score_display']}"


def _summary(row: dict) -> str:
    lines = [s["evidence_text"] for s in row["signals"]]
    return " · ".join([lines[0]] + [line[0].lower() + line[1:] for line in lines[1:]])


def _card(row: dict, labels: dict, fresh: dict) -> dict:
    return {
        "rank": row["rank"],
        "account_id": row["account_id"],
        "name": row["name"],
        "meta": f"{row['sub_vertical']} · {money_label(row['revenue_eur'])}",
        "headline": _sentence([s["headline_clause"] for s in row["signals"]]),
        "tier": row["tier"],
        "signals": [
            {
                "label": s["label"],
                "tier": s["tier"],
                "points": s["points"],
                "evidence": s["evidence_text"],
                "source": labels[s["sources"][0]],
                "fresh": fresh[s["sources"][0]],
            }
            for s in row["signals"]
        ],
        "score": row["score_display"],
        "formula": row["formula"],
        "equation": _equation(row),
        "size_label": row["size_label"],
        "size_multiplier": str(row["size_multiplier"]),
        "action_text": row["action_text"],
        "effort": effort_label(row["effort_minutes"], row["effort_band"]),
        "effort_band": row["effort_band"],
        "prepare": " and ".join(row["prepare"]),
    }


def build_week(raw: dict, now: datetime, playbook: dict) -> dict:
    run = compute_run(raw, now, playbook)
    fresh = {source: fresh_label(moment, now) for source, moment in _as_of_by_source(raw).items()}
    labels = {s["source"]: s["label"] for s in playbook["sources"]}

    groups = []
    for tier in playbook["list_tiers"]:
        cards = [_card(r, labels, fresh) for r in run["accounts"] if r["tier"] == tier]
        if cards:
            groups.append({"tier": tier, "cards": cards})

    user = raw["salesforce"]["users"]["records"][0]
    local_now = now.astimezone(AMSTERDAM)
    baseline = playbook["baseline"]
    return {
        "user": {
            "name": user["Name"],
            "initials": "".join(part[0] for part in user["Name"].split()),
            "title": user["Title"],
            "account_count": len(raw["salesforce"]["accounts"]["records"]),
        },
        "week_label": (
            f"Week {local_now.isocalendar().week} · {WEEKDAYS[local_now.weekday()]} "
            f"{local_now.day} {MONTHS[local_now.month - 1][:3]} {local_now.year}"
        ),
        "need_you_count": sum(len(g["cards"]) for g in groups),
        "alerts": {"total": baseline["total"], "tools": len(baseline["by_tool"])},
        "sources": [{"label": s["label"], "fresh": fresh[s["source"]]} for s in playbook["sources"]],
        "groups": groups,
        "can_wait": [
            {
                "account_id": r["account_id"],
                "name": r["name"],
                "tier": r["tier"],
                "summary": _summary(r),
                "equation": _equation(r),
            }
            for r in run["accounts"] if r["tier"] not in playbook["list_tiers"]
        ],
        "healthy_count": run["healthy_count"],
    }
