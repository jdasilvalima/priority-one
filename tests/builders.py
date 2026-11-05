"""Small record builders. Field names copy the JSON sources."""

from datetime import datetime, timedelta, timezone

from app.facts import AccountFacts

NOW = datetime(2026, 11, 2, 7, 12, tzinfo=timezone.utc)
TODAY = NOW.date()


def days_ago(days: int) -> str:
    return (NOW - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def date_ago(days: int) -> str:
    return (TODAY - timedelta(days=days)).isoformat()


def call(age_days: int = 5, competitors: int = 0, tracker: str = "Competitors", title: str = "Check-in") -> dict:
    return {
        "metaData": {"id": f"call_{age_days}", "title": title, "started": days_ago(age_days)},
        "content": {"trackers": [{"name": tracker, "count": competitors}]},
    }


def meeting(age_days: int) -> dict:
    return {"Id": f"00U_{age_days}", "StartDateTime": days_ago(age_days)}


def case(age_days: int = 5, closed: bool = False, escalated: bool = False, priority: str = "Medium",
         violated: bool = False, late_days: int = 1, number: str = "00000001", kind: str = "Technical") -> dict:
    milestones = []
    if violated:
        milestones = [{"TargetDate": days_ago(late_days), "IsViolated": True}]
    return {
        "Id": f"500_{number}",
        "CaseNumber": number,
        "Type": kind,
        "Priority": priority,
        "IsEscalated": escalated,
        "IsClosed": closed,
        "CreatedDate": days_ago(age_days),
        "CaseMilestones": {"records": milestones},
    }


def contract(ends_in_days: int = 400, commitment: float | None = None) -> dict:
    return {
        "Id": "800_test",
        "EndDate": (TODAY + timedelta(days=ends_in_days)).isoformat(),
        "Committed_Monthly_Volume__c": commitment,
    }


def opportunity(kind: str = "Renewal", closed: bool = False) -> dict:
    return {"Id": "006_test", "Type": kind, "IsClosed": closed}


def champion(contact_id: str = "003_ana") -> dict:
    return {"ContactId": contact_id, "Role": "Champion", "IsPrimary": False,
            "Contact": {"Name": "Ana Ruiz", "Title": "Head of Payments"}}


def primary(name: str = "Marc Dubois", title: str = "CFO") -> dict:
    return {"ContactId": "003_primary", "Role": "Decision Maker", "IsPrimary": True,
            "Contact": {"Name": name, "Title": title}}


def job_change(age_days: int = 10, contact_id: str = "003_ana", change_type: str = "left_company",
               replacement: dict | None = None) -> dict:
    return {
        "event_id": "clay_test",
        "contact_id": contact_id,
        "change_type": change_type,
        "effective_date": date_ago(age_days),
        "replacement": replacement,
    }


def survey(score: int, age_days: int = 5) -> dict:
    return {"Id": f"a0S_{age_days}", "Score__c": score, "Responded_At__c": days_ago(age_days)}


def payment(age_days: int, volume: float = 1000.0, attempts: int = 10000, approved: int = 9000) -> dict:
    return {"date": date_ago(age_days), "volume_eur": volume, "auth_attempts": attempts, "auth_approved": approved}


def payments(recent_days=7, baseline_days=28, recent=None, baseline=None) -> list[dict]:
    """One row per day: the recent window, then the baseline window before it."""
    recent = recent or {}
    baseline = baseline or {}
    rows = [payment(age, **recent) for age in range(1, recent_days + 1)]
    rows += [payment(age, **baseline) for age in range(recent_days + 1, recent_days + baseline_days + 1)]
    return rows


def make_facts(**overrides) -> AccountFacts:
    """An account that fires nothing, unless a test overrides a field."""
    defaults = dict(
        account_id="001_test", name="Test Co", am_id="005_rosa", revenue_eur=500000,
        merchant_code="TEST_ECOM", sub_vertical="Retail", go_live=None,
        contacts=[], contracts=[], opportunities=[], cases=[], calls=[call()],
        meetings=[], surveys=[], job_changes=[], payments=[],
    )
    return AccountFacts(**{**defaults, **overrides})
