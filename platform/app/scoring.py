"""Score = sum of churn points x client size. Then the next action and the rank."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from app.facts import AccountFacts, to_facts
from app.rules import run_rules

NO_PRIMARY_CONTACT = "your main contact"
NO_NEW_CONTACT = "the new contact"


def _size_band(revenue_eur: float, playbook: dict) -> dict:
    for band in playbook["size_bands"]:
        if "below_eur" in band and revenue_eur < band["below_eur"]:
            return band
        if "up_to_eur" in band and revenue_eur <= band["up_to_eur"]:
            return band
    return playbook["size_bands"][-1]


def score(signals: list[dict], revenue_eur: float, playbook: dict) -> dict:
    band = _size_band(revenue_eur, playbook)
    multiplier = Decimal(str(band["multiplier"]))
    points = [s["points"] for s in signals]
    total = sum(points)
    raw = Decimal(total) * multiplier
    listed = " + ".join(str(p) for p in points)
    return {
        "tier": next(t for t in playbook["tier_order"] if any(s["tier"] == t for s in signals)),
        "points_sum": total,
        "size_band": band["band"],
        "size_label": band["label"],
        "size_multiplier": multiplier,
        "score_raw": raw,
        "score_display": int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        "formula": f"({listed}) × {multiplier}" if len(points) > 1 else f"{listed} × {multiplier}",
    }


def effort_band(minutes: int, playbook: dict) -> str:
    for band in playbook["effort_bands"]:
        if "up_to_minutes" in band and minutes <= band["up_to_minutes"]:
            return band["band"]
    return playbook["effort_bands"][-1]["band"]


def _primary_contact(facts: AccountFacts) -> str:
    for contact in facts.contacts:
        if contact["IsPrimary"]:
            return f"{contact['Contact']['Name']} ({contact['Contact']['Title']})"
    return NO_PRIMARY_CONTACT


def _new_contact(facts: AccountFacts) -> str:
    for change in facts.job_changes:
        if change.get("replacement"):
            return change["replacement"]["name"]
    return NO_NEW_CONTACT


def pick_action(signals: list[dict], facts: AccountFacts, playbook: dict) -> dict:
    fired = {s["signal_id"] for s in signals}
    action = next(a for a in playbook["actions"] if set(a["when_all"]) <= fired)
    text = action["text"].replace("{primary_contact}", _primary_contact(facts))
    return {
        "action_id": action["action_id"],
        "action_text": text.replace("{new_contact}", _new_contact(facts)),
        "effort_minutes": action["effort_minutes"],
        "effort_band": effort_band(action["effort_minutes"], playbook),
        "prepare": action["prepare"],
    }


def rank(rows: list[dict], playbook: dict) -> list[dict]:
    tiers = {tier: i for i, tier in enumerate(playbook["tier_order"])}
    ordered = sorted(rows, key=lambda r: (tiers[r["tier"]], -r["score_raw"], r["effort_minutes"], r["account_id"]))
    return [{**row, "rank": position} for position, row in enumerate(ordered, start=1)]


def compute_run(raw: dict, now: datetime, playbook: dict) -> dict:
    rows = []
    healthy = 0
    for facts in to_facts(raw):
        signals = run_rules(facts, now, playbook)
        if not signals:
            healthy += 1
            continue
        rows.append({
            "account_id": facts.account_id,
            "name": facts.name,
            "sub_vertical": facts.sub_vertical,
            "revenue_eur": facts.revenue_eur,
            "signals": signals,
            **score(signals, facts.revenue_eur, playbook),
            **pick_action(signals, facts, playbook),
        })
    return {"accounts": rank(rows, playbook), "healthy_count": healthy}
