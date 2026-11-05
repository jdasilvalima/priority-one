"""Group the raw source records by account, so a rule only sees one account."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class AccountFacts:
    account_id: str
    name: str
    am_id: str
    revenue_eur: float
    merchant_code: str
    sub_vertical: str
    go_live: date | None
    contacts: list[dict]
    contracts: list[dict]
    opportunities: list[dict]
    cases: list[dict]
    calls: list[dict]
    meetings: list[dict]
    surveys: list[dict]
    job_changes: list[dict]
    payments: list[dict]


def _by(records: list[dict], field: str) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for record in records:
        grouped[record[field]].append(record)
    return grouped


def _calls_by_account(calls: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for call in calls:
        for link in call["context"]:
            for item in link["objects"]:
                if item["objectType"] == "Account":
                    grouped[item["objectId"]].append(call)
    return grouped


def to_facts(raw: dict) -> list[AccountFacts]:
    salesforce = raw["salesforce"]
    records = {name: salesforce[name]["records"] for name in salesforce if name != "as_of"}
    contacts = _by(records["contact_roles"], "AccountId")
    contracts = _by(records["contracts"], "AccountId")
    opportunities = _by(records["opportunities"], "AccountId")
    cases = _by(records["cases"], "AccountId")
    meetings = _by(records["events"], "WhatId")
    surveys = _by(records["surveys"], "Account__c")
    calls = _calls_by_account(raw["gong"]["calls"])
    job_changes = _by([e for e in raw["clay"]["events"] if e["type"] == "job_change"], "account_id")
    payments = _by(raw["payments"]["rows"], "merchant_account_code")

    facts = []
    for account in records["accounts"]:
        account_id = account["Id"]
        go_live = account["Go_Live_Date__c"]
        facts.append(AccountFacts(
            account_id=account_id,
            name=account["Name"],
            am_id=account["OwnerId"],
            revenue_eur=account["Annual_Revenue_To_Us__c"],
            merchant_code=account["Merchant_Account_Code__c"],
            sub_vertical=account["Sub_Vertical__c"],
            go_live=date.fromisoformat(go_live) if go_live else None,
            contacts=contacts[account_id],
            contracts=contracts[account_id],
            opportunities=opportunities[account_id],
            cases=cases[account_id],
            calls=calls[account_id],
            meetings=meetings[account_id],
            surveys=surveys[account_id],
            job_changes=job_changes[account_id],
            payments=payments[account["Merchant_Account_Code__c"]],
        ))
    return facts
