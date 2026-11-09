"""Which moment the scoring uses, and how a week is named."""

import os
from datetime import datetime, timezone


def scoring_now() -> datetime:
    """The mock sources stop on 1 November 2026, so the stack fixes SCORING_CLOCK. Real sources leave it empty."""
    fixed = os.environ.get("SCORING_CLOCK")
    return datetime.fromisoformat(fixed) if fixed else datetime.now(timezone.utc)


def week_key(moment: datetime) -> str:
    year, week, _ = moment.isocalendar()
    return f"{year}-W{week:02d}"
