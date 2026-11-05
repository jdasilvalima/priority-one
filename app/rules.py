"""The 9 playbook rules. Thresholds live in config/playbook.json.

Each check returns None, or a Hit: the evidence line, the proving record and the headline clause.
"""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from app.facts import AccountFacts

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")


class Hit(NamedTuple):
    evidence: str
    record_id: str | None
    clause: str


def _day(value: str) -> date:
    return datetime.fromisoformat(value).date()


def short_date(day: date) -> str:
    return f"{day.day} {MONTHS[day.month - 1][:3]}"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _one_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def _whole(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _late_milestones(case: dict) -> list[dict]:
    return [m for m in case["CaseMilestones"]["records"] if m["IsViolated"]]


def _is_serious(case: dict) -> bool:
    return case["IsEscalated"] or case["Priority"] == "Urgent" or bool(_late_milestones(case))


def escalated_case(facts: AccountFacts, today: date, params: dict) -> Hit | None:
    serious = [c for c in facts.cases if not c["IsClosed"] and _is_serious(c)]
    if not serious:
        return None
    late = [c for c in serious if _late_milestones(c)]
    lead = (late or serious)[0]
    if len(serious) == 1 and late:
        days = (today - _day(_late_milestones(lead)[0]["TargetDate"])).days
        late_text = f"{_plural(days, 'day')} past SLA"
        return Hit(f"{lead['Type']} case {late_text}", lead["Id"], f"a {lead['Type'].lower()} case is {late_text}")
    past_sla = f", {len(late)} past SLA" if late else ""
    count = _plural(len(serious), "urgent case")
    verb = "is" if len(serious) == 1 else "are"
    return Hit(f"{count}{past_sla} (case {lead['CaseNumber']})", lead["Id"], f"{count} {verb} open")


def _rows_between(rows: list[dict], first: date, last: date) -> list[dict]:
    return [r for r in rows if first <= date.fromisoformat(r["date"]) <= last]


def _auth_rate(rows: list[dict]) -> Decimal | None:
    attempts = sum(r["auth_attempts"] for r in rows)
    if attempts == 0:
        return None
    return Decimal(sum(r["auth_approved"] for r in rows)) / Decimal(attempts)


def _daily_volume(rows: list[dict]) -> Decimal:
    return sum(Decimal(str(r["volume_eur"])) for r in rows) / len(rows)


def auth_or_volume_drop(facts: AccountFacts, today: date, params: dict) -> Hit | None:
    current_days, baseline_days = params["current_days"], params["baseline_days"]
    yesterday = today - timedelta(days=1)
    split = today - timedelta(days=current_days)
    current = _rows_between(facts.payments, split, yesterday)
    baseline = _rows_between(facts.payments, split - timedelta(days=baseline_days), split - timedelta(days=1))
    if not current or not baseline:
        return None

    auth_now, auth_before = _auth_rate(current), _auth_rate(baseline)
    if auth_now is not None and auth_before is not None:
        drop = (auth_before - auth_now) * 100
        if drop >= params["auth_drop_pts"]:
            points = _one_decimal(drop)
            evidence = f"Auth rate {_one_decimal(auth_now * 100)}%, down {points} pts vs baseline"
            return Hit(evidence, facts.merchant_code, f"approvals fell {points} pts")

    volume_before = _daily_volume(baseline)
    if volume_before > 0:
        fall = (volume_before - _daily_volume(current)) / volume_before * 100
        if fall >= params["volume_drop_pct"]:
            return Hit(f"Volume down {_whole(fall)}% vs baseline", facts.merchant_code, f"volume fell {_whole(fall)}%")
    return None


def _competitor_count(call: dict) -> int:
    return sum(t["count"] for t in call["content"]["trackers"] if t["name"] == "Competitors")


def competitor_named(facts: AccountFacts, today: date, params: dict) -> Hit | None:
    named = [
        c for c in facts.calls
        if _competitor_count(c) > 0 and 0 <= (today - _day(c["metaData"]["started"])).days <= params["lookback_days"]
    ]
    if not named:
        return None
    latest = max(named, key=lambda c: c["metaData"]["started"])
    kind = "QBR" if "QBR" in latest["metaData"]["title"] else "call"
    evidence = f"Competitor named on {short_date(_day(latest['metaData']['started']))} {kind}"
    return Hit(evidence, latest["metaData"]["id"], "a competitor was named on the last call")


def renewal_no_opp(facts: AccountFacts, today: date, params: dict) -> Hit | None:
    if any(o["Type"] == "Renewal" and not o["IsClosed"] for o in facts.opportunities):
        return None
    ending = [
        c for c in facts.contracts
        if 0 <= (date.fromisoformat(c["EndDate"]) - today).days <= params["window_days"]
    ]
    if not ending:
        return None
    soonest = min(ending, key=lambda c: c["EndDate"])
    end = date.fromisoformat(soonest["EndDate"])
    return Hit(f"Renews {short_date(end)}, no renewal opportunity open", soonest["Id"],
               f"the renewal is in {(end - today).days} days")


def champion_left(facts: AccountFacts, today: date, params: dict) -> Hit | None:
    champions = {c["ContactId"]: c for c in facts.contacts if c["Role"] == "Champion"}
    for change in facts.job_changes:
        age = (today - date.fromisoformat(change["effective_date"])).days
        if change["contact_id"] in champions and change["change_type"] == "left_company" and 0 <= age <= params["lookback_days"]:
            title = champions[change["contact_id"]]["Contact"]["Title"]
            replacement = change.get("replacement")
            taken_over = f", {replacement['name']} took over" if replacement else ""
            left_on = date.fromisoformat(change["effective_date"])
            return Hit(f"{title} left{taken_over}", change["event_id"],
                       f"your champion left in {MONTHS[left_on.month - 1]}")
    return None


def ramp_below_commit(facts: AccountFacts, today: date, params: dict) -> Hit | None:
    if facts.go_live is None or (today - facts.go_live).days < params["min_days_live"]:
        return None
    committed = [c for c in facts.contracts if c["Committed_Monthly_Volume__c"]]
    rows = _rows_between(facts.payments, today - timedelta(days=params["volume_days"]), today - timedelta(days=1))
    if not committed or not rows:
        return None
    contract = max(committed, key=lambda c: c["EndDate"])
    commitment = Decimal(str(contract["Committed_Monthly_Volume__c"]))
    volume = sum(Decimal(str(r["volume_eur"])) for r in rows)
    below = (commitment - volume) / commitment * 100
    if below < params["below_pct"]:
        return None
    days_live = (today - facts.go_live).days
    return Hit(f"Processed volume {_whole(below)}% below commitment", contract["Id"],
               f"{days_live} days after go-live, volume is {_whole(below)}% below what they committed")


def cases_piling_up(facts: AccountFacts, today: date, params: dict) -> Hit | None:
    window = params["window_days"]
    recent = [c for c in facts.cases if 0 <= (today - _day(c["CreatedDate"])).days <= window]
    if len(recent) < params["min_cases"]:
        return None
    latest = max(recent, key=lambda c: c["CreatedDate"])
    return Hit(f"{len(recent)} cases in {window} days", latest["Id"], f"{len(recent)} cases were opened in {window} days")


def low_satisfaction(facts: AccountFacts, today: date, params: dict) -> Hit | None:
    if not facts.surveys:
        return None
    latest = max(facts.surveys, key=lambda s: s["Responded_At__c"])
    if latest["Score__c"] > params["max_score"]:
        return None
    return Hit(f"Survey score {latest['Score__c']}", latest["Id"], f"the last survey score was {latest['Score__c']}")


def no_contact(facts: AccountFacts, today: date, params: dict) -> Hit | None:
    past = [(_day(c["metaData"]["started"]), c["metaData"]["id"]) for c in facts.calls]
    past += [(_day(m["StartDateTime"]), m["Id"]) for m in facts.meetings]
    past = [item for item in past if item[0] <= today]
    if not past:
        return Hit("No call or meeting on record", None, "nobody has spoken to them yet")
    last_day, record_id = max(past)
    days = (today - last_day).days
    if days < params["min_days"]:
        return None
    return Hit(f"No call or meeting in {days} days", record_id, f"nobody has spoken to them in {days} days")


CHECKS = {
    "sig_escalated_case": escalated_case,
    "sig_auth_or_volume_drop": auth_or_volume_drop,
    "sig_competitor_named": competitor_named,
    "sig_renewal_no_opp": renewal_no_opp,
    "sig_champion_left": champion_left,
    "sig_ramp_below_commit": ramp_below_commit,
    "sig_cases_piling_up": cases_piling_up,
    "sig_low_satisfaction": low_satisfaction,
    "sig_no_contact_60d": no_contact,
}


def run_rules(facts: AccountFacts, now: datetime, playbook: dict) -> list[dict]:
    today = now.date()
    fired = []
    for signal in playbook["signals"]:
        hit = CHECKS[signal["signal_id"]](facts, today, signal.get("params", {}))
        if hit is None:
            continue
        fired.append({
            "signal_id": signal["signal_id"],
            "label": signal["label"],
            "tier": signal["tier"],
            "points": playbook["tier_points"][signal["tier"]],
            "sources": signal["sources"],
            "evidence_text": hit.evidence,
            "source_record_id": hit.record_id,
            "headline_clause": hit.clause,
        })
    return fired
