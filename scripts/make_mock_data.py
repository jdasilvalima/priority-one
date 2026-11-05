"""Write the 4 mock source files in data/. All names and numbers are fictional.

Run: python scripts/make_mock_data.py
The output is the same on every run: 8 hand-written stories and 34 healthy accounts.
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
JADE = "005_jade"
FIRST_DAY = date(2026, 8, 31)
LAST_DAY = date(2026, 11, 1)
WEEKDAY_SHAPE = [1.0, 0.98, 0.97, 0.99, 1.05, 1.12, 0.89]  # Monday to Sunday, mean 1
TICKET_EUR = 4.5


def soql(records: list[dict]) -> dict:
    return {"totalSize": len(records), "done": True, "records": records}


def account(key, name, revenue, code, vertical, go_live) -> dict:
    return {
        "Id": f"001_{key}", "Name": name, "OwnerId": JADE, "Annual_Revenue_To_Us__c": revenue,
        "Merchant_Account_Code__c": code, "Sub_Vertical__c": vertical, "Go_Live_Date__c": go_live,
    }


def role(key, slug, name, title, role_name="Decision Maker", primary=True) -> dict:
    return {
        "AccountId": f"001_{key}", "ContactId": f"003_{slug}", "Role": role_name, "IsPrimary": primary,
        "Contact": {"Name": name, "Title": title},
    }


def contract(key, end, commitment) -> dict:
    return {"Id": f"800_{key}", "AccountId": f"001_{key}", "StartDate": "2024-01-01", "EndDate": end,
            "Committed_Monthly_Volume__c": commitment}


def opportunity(key, kind, closed, close_date) -> dict:
    return {"Id": f"006_{key}_{kind.lower()}", "AccountId": f"001_{key}", "Type": kind,
            "StageName": "Closed Won" if closed else "Negotiation", "CloseDate": close_date, "IsClosed": closed}


def case(key, number, subject, kind, priority, created, closed=False, escalated=False, milestone=None) -> dict:
    return {
        "Id": f"500_{number}", "CaseNumber": number, "AccountId": f"001_{key}", "Subject": subject, "Type": kind,
        "Status": "Closed" if closed else ("Escalated" if escalated else "Working"), "Priority": priority,
        "IsEscalated": escalated, "IsClosed": closed, "CreatedDate": created,
        "CaseMilestones": soql([milestone] if milestone else []),
    }


def milestone(target, violated) -> dict:
    return {"Id": f"5pt_{target[:10]}", "TargetDate": target, "CompletionDate": None,
            "IsCompleted": False, "IsViolated": violated}


def call(call_id, key, title, started, competitors=0) -> dict:
    return {
        "metaData": {"id": call_id, "title": title, "started": started, "duration": 2700,
                     "system": "Google Meet", "scope": "External"},
        "context": [{"system": "Salesforce", "objects": [{"objectType": "Account", "objectId": f"001_{key}"}]}],
        "content": {"trackers": [{"name": "Competitors", "count": competitors}]},
    }


def event(key, event_id, start) -> dict:
    return {"Id": f"00U_{event_id}", "WhatId": f"001_{key}", "StartDateTime": start, "Subject": "Account review"}


def survey(key, survey_id, score, responded) -> dict:
    return {"Id": f"a0S_{survey_id}", "Account__c": f"001_{key}", "Score__c": score, "Responded_At__c": responded}


# The 8 stories. Each date is chosen so the rule fires, or stays quiet, on purpose.
STORIES = [
    account("northwind", "Northwind Apparel", 2400000, "NWAPP_ECOM", "Fashion e-commerce", "2024-03-12"),
    account("kestrel", "Kestrel Travel Group", 3100000, "KTG_ECOM", "Online travel", "2023-11-06"),
    account("halcyon", "Halcyon Hotels", 420000, "HALCY_ECOM", "Hospitality", "2024-06-03"),
    account("pico", "Pico Subscriptions", 310000, "PICO_ECOM", "Subscription boxes", "2024-09-16"),
    account("vantor", "Vantor Gaming", 1600000, "VANTR_ECOM", "Online gaming", "2026-08-19"),
    account("lumen", "Lumen Mobility", 540000, "LUMEN_ECOM", "Urban mobility", "2024-02-05"),
    account("bloom", "Bloom & Co Grocers", 85000, "BLOOM_ECOM", "Grocery", "2025-01-20"),
    account("orbit", "Orbit Ticketing", 260000, "ORBIT_ECOM", "Event ticketing", "2024-10-14"),
]
STORY_ROLES = [
    role("northwind", "jana_weber", "Jana Weber", "Head of Payments Ops"),
    role("kestrel", "marc_dubois", "Marc Dubois", "CFO"),
    role("halcyon", "siobhan_kelly", "Siobhan Kelly", "Finance Director"),
    role("pico", "ana_ruiz", "Ana Ruiz", "Head of Payments", role_name="Champion"),
    role("vantor", "erik_lund", "Erik Lund", "COO"),
    role("lumen", "nadia_haddad", "Nadia Haddad", "Operations Director"),
    role("bloom", "pieter_vos", "Pieter Vos", "Owner"),
    role("orbit", "lea_martin", "Lea Martin", "Head of Partnerships"),
]
STORY_CONTRACTS = [
    contract("northwind", "2027-09-30", 200000),
    contract("kestrel", "2026-12-11", 260000),
    contract("halcyon", "2027-06-30", 30000),
    contract("pico", "2027-01-05", 22000),
    contract("vantor", "2028-08-18", 300000),
    contract("lumen", "2027-08-31", 40000),
    contract("bloom", "2027-05-31", 6000),
    contract("orbit", "2027-10-31", 18000),
]
STORY_OPPORTUNITIES = [
    opportunity("kestrel", "Renewal", True, "2025-12-11"),  # last year's renewal, closed: must not hide this one
    opportunity("kestrel", "Upsell", False, "2027-02-28"),  # open, but not a renewal
]
STORY_CASES = [
    case("northwind", "00481523", "Card declines since 28 Oct checkout release", "Technical", "Urgent",
         "2026-10-29T09:12:00Z", escalated=True, milestone=milestone("2026-10-31T09:12:00Z", True)),
    case("northwind", "00481577", "Refunds failing for one card brand", "Technical", "Urgent",
         "2026-10-31T16:40:00Z", milestone=milestone("2026-11-03T16:40:00Z", False)),
    case("halcyon", "00479902", "October payout not received", "Payout", "High",
         "2026-10-27T10:00:00Z", milestone=milestone("2026-10-29T10:00:00Z", True)),
    case("lumen", "00480101", "Webhook retries delayed", "Technical", "Medium", "2026-10-06T08:30:00Z", closed=True),
    case("lumen", "00480244", "Report export is slow", "Technical", "Low", "2026-10-13T11:05:00Z", closed=True),
    case("lumen", "00480590", "Question on settlement file", "Finance", "Medium", "2026-10-21T14:20:00Z"),
    case("lumen", "00481012", "New user access request", "Access", "Low", "2026-10-28T09:45:00Z"),
]
STORY_CALLS = [
    call("7782001", "kestrel", "Kestrel Q4 QBR", "2026-10-30T14:00:00Z", competitors=2),
    call("7781410", "northwind", "Northwind monthly check-in", "2026-10-20T10:00:00Z"),
    call("7775120", "halcyon", "Halcyon Q3 review", "2026-08-31T09:00:00Z"),
    call("7781633", "pico", "Pico roadmap call", "2026-10-21T15:00:00Z"),
    call("7781244", "vantor", "Vantor go-live follow-up", "2026-10-19T13:00:00Z"),
    call("7780921", "lumen", "Lumen check-in", "2026-10-15T09:30:00Z"),
    call("7780412", "bloom", "Bloom check-in", "2026-10-08T11:00:00Z"),
    call("7773002", "orbit", "Orbit Q3 review", "2026-08-10T10:00:00Z"),
]
STORY_EVENTS = [
    event("orbit", "orbit_q3", "2026-08-24T09:00:00Z"),
]
STORY_SURVEYS = [
    survey("lumen", "lumen_q2", 8, "2026-06-18T10:00:00Z"),
    survey("lumen", "lumen_q3", 5, "2026-10-20T10:00:00Z"),
    survey("bloom", "bloom_q3", 6, "2026-10-12T10:00:00Z"),
]

HEALTHY = [
    ("alder", "Alder & Finch Home", "Home goods"), ("amberline", "Amberline Pet Supply", "Pet supplies"),
    ("arcadia", "Arcadia Bike Works", "Sporting goods"), ("bluefen", "Bluefen Outdoor", "Outdoor gear"),
    ("brightwell", "Brightwell Pharmacy", "Health retail"), ("cedarlane", "Cedar Lane Books", "Books"),
    ("copperleaf", "Copperleaf Coffee", "Food and drink"), ("driftwood", "Driftwood Surf Co", "Sporting goods"),
    ("elmhurst", "Elmhurst Furniture", "Home goods"), ("fernhill", "Fernhill Garden", "Home goods"),
    ("foxglove", "Foxglove Beauty", "Beauty"), ("glasswing", "Glasswing Optics", "Health retail"),
    ("goldcrest", "Goldcrest Jewelers", "Luxury"), ("harbourlight", "Harbourlight Ferries", "Travel"),
    ("hazelwood", "Hazelwood Toys", "Toys"), ("ironbridge", "Ironbridge Tools", "Hardware"),
    ("juniper", "Juniper Wellness", "Health retail"), ("kingfisher", "Kingfisher Sports", "Sporting goods"),
    ("larkspur", "Larkspur Flowers", "Gifts"), ("marlowe", "Marlowe Stationery", "Office supplies"),
    ("meadowbank", "Meadowbank Dairy", "Grocery"), ("nettlefield", "Nettlefield Tea", "Food and drink"),
    ("oakhaven", "Oakhaven Camping", "Outdoor gear"), ("pebblecreek", "Pebblecreek Shoes", "Fashion e-commerce"),
    ("quillon", "Quillon Audio", "Electronics"), ("redwing", "Redwing Cycles", "Sporting goods"),
    ("saltmarsh", "Saltmarsh Seafood", "Grocery"), ("silverbirch", "Silverbirch Kitchens", "Home goods"),
    ("thistledown", "Thistledown Yarn", "Crafts"), ("tidewater", "Tidewater Cruises", "Travel"),
    ("umberline", "Umberline Paints", "Hardware"), ("wrenfield", "Wrenfield Electronics", "Electronics"),
    ("yarrow", "Yarrow Organics", "Grocery"), ("zephyr", "Zephyr Scooters", "Urban mobility"),
]
FIRST_NAMES = ["Mila", "Jonas", "Priya", "Tomas", "Elena", "Noah", "Ines", "Lars", "Amara", "Felix"]
LAST_NAMES = ["Keller", "Novak", "Rao", "Lindqvist", "Moreau", "Bakker", "Costa", "Hansen", "Okafor", "Weiss"]
TITLES = ["CFO", "Head of Payments", "Finance Director", "COO", "Head of E-commerce"]


def healthy_book(rng: random.Random) -> dict:
    """34 accounts that fire nothing, including near misses that test each rule."""
    book = {k: [] for k in ("accounts", "roles", "contracts", "opportunities", "cases", "calls", "events", "surveys")}
    for i, (key, name, vertical) in enumerate(HEALTHY):
        revenue = rng.randrange(60000, 1900000, 5000)
        volume = revenue / 300
        code = f"{key[:5].upper()}_ECOM"
        go_live = date(2023, 1, 9) + timedelta(days=rng.randrange(0, 900))
        book["accounts"].append(account(key, name, revenue, code, vertical, go_live.isoformat()))

        first, last = FIRST_NAMES[i % 10], LAST_NAMES[(i * 3) % 10]
        title = TITLES[i % 5]
        book["roles"].append(role(key, f"{first}_{last}_{i}".lower(), f"{first} {last}", title))
        if i % 3 == 0:
            book["roles"].append(role(key, f"champion_{i}", f"{first} {LAST_NAMES[(i * 7 + 1) % 10]}", "Payments Lead",
                                      role_name="Champion", primary=False))

        # Contract far away, except 3 near misses: renewal soon, but the renewal is already open.
        if i in (2, 13, 27):
            end = date(2026, 11, 20) + timedelta(days=i)
            book["opportunities"].append(opportunity(key, "Renewal", False, end.isoformat()))
        else:
            end = date(2027, 3, 1) + timedelta(days=rng.randrange(0, 480))
        book["contracts"].append(contract(key, end.isoformat(), round(volume * 30 * 0.9, -2)))

        # Last contact 4 to 55 days ago. A competitor mentioned, but over 14 days ago, on 3 accounts.
        old_mention = i in (5, 19, 30)
        age = 21 if old_mention else rng.randrange(4, 56)
        started = f"{date(2026, 11, 2) - timedelta(days=age)}T10:00:00Z"
        book["calls"].append(call(f"77{60000 + i}", key, f"{name} check-in", started, int(old_mention)))

        # A future meeting on some accounts: it is booked, not yet held.
        if i % 4 == 0:
            book["events"].append(event(key, f"next_{i}", "2026-11-18T09:00:00Z"))

        # An older low score, followed by a better one: only the latest counts.
        if i % 5 == 0:
            book["surveys"].append(survey(key, f"old_{i}", 4, "2026-05-10T10:00:00Z"))
        book["surveys"].append(survey(key, f"new_{i}", rng.randint(7, 10), "2026-09-22T10:00:00Z"))

        # Up to 2 ordinary cases in 30 days, and closed serious ones.
        for n in range(i % 3):
            book["cases"].append(case(key, f"0047{i:02d}{n}0", "Routine question", "General", "Low",
                                      f"2026-10-{10 + n:02d}T10:00:00Z"))
        if i % 7 == 0:
            book["cases"].append(case(key, f"0046{i:02d}99", "Resolved incident", "Technical", "Urgent",
                                      "2026-09-03T10:00:00Z", closed=True, escalated=True))
    return book


def payment_rows(accounts: list[dict], rng: random.Random) -> list[dict]:
    rows = []
    days = [FIRST_DAY + timedelta(days=n) for n in range((LAST_DAY - FIRST_DAY).days + 1)]
    for acc in accounts:
        code = acc["Merchant_Account_Code__c"]
        volume = acc["Annual_Revenue_To_Us__c"] / 300
        auth_rate = rng.uniform(0.87, 0.93)
        for day in days:
            shape = WEEKDAY_SHAPE[day.weekday()]
            noise = rng.uniform(0.98, 1.02)
            rate = auth_rate + rng.uniform(-0.003, 0.003)
            if code == "NWAPP_ECOM":  # approvals fall in the last 7 days: 88.3% to 82.1%
                noise = 1.0
                rate = 0.821 if day >= date(2026, 10, 26) else 0.883
            elif code == "VANTR_ECOM":  # flat at 38% below the 300,000 monthly commitment
                shape, noise = 1.0, 1.0
                volume = 6200.0
            amount = round(volume * shape * noise, 2)
            attempts = round(amount / TICKET_EUR)
            rows.append({"merchant_account_code": code, "date": day.isoformat(), "volume_eur": amount,
                         "auth_attempts": attempts, "auth_approved": round(attempts * rate)})
    return rows


def clay_events() -> list[dict]:
    return [
        {"event_id": "clay_9012", "type": "job_change", "account_id": "001_pico", "contact_id": "003_ana_ruiz",
         "contact_name": "Ana Ruiz", "change_type": "left_company", "effective_date": "2026-10-12",
         "detected_at": "2026-10-14T06:00:00Z", "replacement": {"name": "Tom Hughes", "title": "Head of Payments"}},
        # Near miss: a champion, but the departure is over 90 days old.
        {"event_id": "clay_8120", "type": "job_change", "account_id": "001_alder", "contact_id": "003_champion_0",
         "contact_name": "Mila Novak", "change_type": "left_company", "effective_date": "2026-07-05",
         "detected_at": "2026-07-07T06:00:00Z", "replacement": None},
        # Near miss: recent, but this contact stayed.
        {"event_id": "clay_9044", "type": "job_change", "account_id": "001_bluefen", "contact_id": "003_champion_3",
         "contact_name": "Tomas Rao", "change_type": "promoted", "effective_date": "2026-10-20",
         "detected_at": "2026-10-22T06:00:00Z", "replacement": None},
        {"event_id": "clay_hb_20261101", "type": "heartbeat", "detected_at": "2026-11-01T21:00:00Z"},
    ]


def write(name: str, payload: dict) -> None:
    (DATA / name).write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    rng = random.Random(45)
    healthy = healthy_book(rng)
    accounts = STORIES + healthy["accounts"]

    write("salesforce.json", {
        "as_of": "2026-11-02T07:00:00Z",
        "accounts": soql(accounts),
        "users": soql([{"Id": JADE, "Name": "Jade D.", "Title": "Account Manager"}]),
        "contact_roles": soql(STORY_ROLES + healthy["roles"]),
        "contracts": soql(STORY_CONTRACTS + healthy["contracts"]),
        "opportunities": soql(STORY_OPPORTUNITIES + healthy["opportunities"]),
        "cases": soql(STORY_CASES + healthy["cases"]),
        "events": soql(STORY_EVENTS + healthy["events"]),
        "surveys": soql(STORY_SURVEYS + healthy["surveys"]),
    })
    calls = STORY_CALLS + healthy["calls"]
    write("gong.json", {
        "as_of": "2026-11-02T05:00:00Z",
        "records": {"totalRecords": len(calls), "currentPageSize": len(calls), "currentPageNumber": 0},
        "calls": calls,
    })
    write("clay.json", {"events": clay_events()})

    rows = payment_rows(accounts, rng)
    lines = ",\n".join("  " + json.dumps(r) for r in rows)
    (DATA / "payments.json").write_text(
        '{\n "exported_at": "2026-11-02T05:00:00Z",\n "rows": [\n' + lines + "\n ]\n}\n", encoding="utf-8")
    print(f"{len(accounts)} accounts, {len(rows)} payment rows, {len(calls)} calls")


if __name__ == "__main__":
    main()
