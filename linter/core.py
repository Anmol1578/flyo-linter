from __future__ import annotations

from datetime import datetime, timezone

from .models import ERROR, INFO, WARNING, Issue
from . import rules

RULES = [
    rules.check_structure,
    rules.check_pnr,
    rules.check_airline_and_flight_number,
    rules.check_airports,
    rules.check_departure,
    rules.check_unsupported_routes,
    rules.check_passenger_names,
    rules.check_contact,
    rules.check_seat_preferences,
    rules.check_callback,
    rules.check_duplicate_passengers,
]

_ORDER = {ERROR: 0, WARNING: 1, INFO: 2}


def lint(payload, now: datetime | None = None) -> list[Issue]:
    """Return all issues for a subscribe payload, errors first."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if not isinstance(payload, dict):
        return [Issue(ERROR, "$", "Payload must be a JSON object.")]

    issues: list[Issue] = []
    for rule in RULES:
        issues.extend(rule(payload, now))
    return sorted(issues, key=lambda issue: _ORDER[issue.level])


def summarize(issues: list[Issue]) -> dict:
    counts = {ERROR: 0, WARNING: 0, INFO: 0}
    for issue in issues:
        counts[issue.level] += 1
    return {"ok": counts[ERROR] == 0, "counts": counts}
