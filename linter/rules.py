"""Lint rules for a Flyo web check-in subscribe payload.

Every rule is a function ``rule(payload, now) -> list[Issue]``.
To add a check, write a new function and append it to RULES in core.py.

All rules are based on Flyo's public documentation. They are heuristics,
not the official validation logic, so the levels mean:
  error   - almost certainly rejected or will fail
  warning - likely to cause a problem, worth a look
  info    - something to confirm
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Iterator
from urllib.parse import urlparse

from .models import ERROR, INFO, WARNING, Issue

PNR_RE = re.compile(r"^[A-Za-z0-9]{5,8}$")
AIRLINE_RE = re.compile(r"^[A-Z0-9]{2}$")
FLIGHT_NO_RE = re.compile(r"^([A-Z0-9]{2})(\d{1,4})([A-Z]?)$")
AIRPORT_RE = re.compile(r"^[A-Z]{3}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]*$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
HEADER_RE = re.compile(r"^[A-Za-z0-9\-]+:\s*\S+")

FLIGHT_FIELDS = ("airline", "flight_number", "origin", "destination", "departure_datetime")

ROW_PREFERENCES = {"front", "middle", "back"}
COLUMN_PREFERENCES = {"window", "middle", "aisle"}

SHORT_NOTICE = timedelta(hours=4)
NAIVE_SLACK = timedelta(hours=14)  # a timezone-less time can be off by up to ~14h

# Partial lists, only used for the India -> US heuristic.
INDIA_AIRPORTS = {
    "DEL", "BOM", "BLR", "MAA", "CCU", "HYD", "AMD", "PNQ", "GOI", "COK",
    "JAI", "LKO", "TRV", "ATQ", "IXC", "GAU", "PAT", "BBI", "IDR", "NAG",
}
US_AIRPORTS = {
    "JFK", "EWR", "LAX", "SFO", "ORD", "IAD", "ATL", "DFW", "SEA", "BOS",
    "IAH", "MIA", "DTW", "PHL", "DEN", "LAS", "MCO", "SJC", "CLT", "MSP",
}

LOCAL_HOSTS = {"localhost", "0.0.0.0", "::1"}


# ---------------------------------------------------------------- helpers
def _items(payload: dict, key: str) -> Iterator[tuple[int, dict]]:
    value = payload.get(key)
    if not isinstance(value, list):
        return
    for i, item in enumerate(value):
        if isinstance(item, dict):
            yield i, item


def _str(obj: dict, key: str) -> str:
    value = obj.get(key)
    return value.strip() if isinstance(value, str) else ""


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ------------------------------------------------------------------ rules
def check_structure(payload: dict, now: datetime) -> list[Issue]:
    issues: list[Issue] = []

    if not _str(payload, "pnr"):
        issues.append(Issue(ERROR, "pnr", "pnr is required and must be a non-empty string."))

    flights = payload.get("flights")
    if not isinstance(flights, list) or not flights:
        issues.append(Issue(ERROR, "flights", "flights must be a non-empty list."))
    else:
        for i, flight in enumerate(flights):
            if not isinstance(flight, dict):
                issues.append(Issue(ERROR, f"flights[{i}]", "Each flight must be an object."))
                continue
            for field in FLIGHT_FIELDS:
                if not _str(flight, field):
                    issues.append(Issue(ERROR, f"flights[{i}].{field}", f"{field} is required."))

    passengers = payload.get("passengers")
    if not isinstance(passengers, list) or not passengers:
        issues.append(Issue(ERROR, "passengers", "passengers must be a non-empty list."))
    else:
        for i, passenger in enumerate(passengers):
            if not isinstance(passenger, dict):
                issues.append(Issue(ERROR, f"passengers[{i}]", "Each passenger must be an object."))
                continue
            for field in ("first_name", "last_name"):
                if not _str(passenger, field):
                    issues.append(Issue(ERROR, f"passengers[{i}].{field}", f"{field} is required."))

    callback = payload.get("callbackData")
    if callback is None:
        issues.append(Issue(
            INFO, "callbackData",
            "No callbackData. You will need to poll the status endpoint to learn the result.",
        ))
    elif not isinstance(callback, dict):
        issues.append(Issue(ERROR, "callbackData", "callbackData must be an object."))

    return issues


def check_pnr(payload: dict, now: datetime) -> list[Issue]:
    pnr = _str(payload, "pnr")
    if not pnr:
        return []
    if not PNR_RE.match(pnr):
        return [Issue(ERROR, "pnr", "PNR should be 5-8 letters or digits with no spaces or symbols.")]
    issues = []
    if pnr != pnr.upper():
        issues.append(Issue(WARNING, "pnr", "PNR is lowercase. Airlines show it in uppercase; send it that way."))
    if len(pnr) != 6:
        issues.append(Issue(WARNING, "pnr", f"PNR has {len(pnr)} characters. Most airline PNRs have 6. Check for a typo."))
    return issues


def check_airline_and_flight_number(payload: dict, now: datetime) -> list[Issue]:
    issues: list[Issue] = []
    for i, flight in _items(payload, "flights"):
        airline = _str(flight, "airline")
        number = _str(flight, "flight_number")
        base = f"flights[{i}]"

        airline_ok = bool(airline) and AIRLINE_RE.match(airline) is not None
        if airline and not airline_ok:
            issues.append(Issue(
                ERROR, f"{base}.airline",
                "airline must be a 2-character uppercase IATA code, e.g. 6E.",
            ))

        compact = number.replace(" ", "")
        number_ok = bool(compact) and FLIGHT_NO_RE.match(compact) is not None
        if number_ok and compact != number:
            issues.append(Issue(
                WARNING, f"{base}.flight_number",
                f"Remove the space: send {compact}.",
            ))
        if number and not number_ok:
            issues.append(Issue(
                ERROR, f"{base}.flight_number",
                "flight_number should be the airline code plus digits, e.g. 6E2341.",
            ))

        if airline_ok and number_ok and not compact.startswith(airline):
            issues.append(Issue(
                ERROR, f"{base}.flight_number",
                f"{number} does not start with the airline code {airline}. This is the usual "
                "codeshare mix-up. Send the operating carrier's code and flight number, "
                "not the marketing carrier's.",
            ))
    return issues


def check_airports(payload: dict, now: datetime) -> list[Issue]:
    issues: list[Issue] = []
    for i, flight in _items(payload, "flights"):
        origin = _str(flight, "origin")
        destination = _str(flight, "destination")
        base = f"flights[{i}]"

        for field, value in (("origin", origin), ("destination", destination)):
            if value and not AIRPORT_RE.match(value):
                issues.append(Issue(
                    ERROR, f"{base}.{field}",
                    f"{field} must be a 3-letter uppercase IATA airport code, e.g. DEL.",
                ))

        if origin and origin == destination:
            issues.append(Issue(ERROR, f"{base}.destination", "origin and destination are the same airport."))
    return issues


def check_departure(payload: dict, now: datetime) -> list[Issue]:
    issues: list[Issue] = []
    for i, flight in _items(payload, "flights"):
        raw = _str(flight, "departure_datetime")
        if not raw:
            continue
        path = f"flights[{i}].departure_datetime"

        dt = _parse_dt(raw)
        if dt is None:
            issues.append(Issue(
                ERROR, path,
                "departure_datetime must be ISO 8601, e.g. 2026-09-20T10:00:00.",
            ))
            continue

        naive = dt.tzinfo is None
        if naive:
            dt = dt.replace(tzinfo=timezone.utc)
            issues.append(Issue(
                INFO, path,
                "No timezone given. Confirm which timezone Flyo expects (the docs example has none).",
            ))

        delta = dt - now
        floor = -NAIVE_SLACK if naive else timedelta(0)
        if delta < floor:
            issues.append(Issue(ERROR, path, "This flight has already departed."))
        elif delta < timedelta(0):
            issues.append(Issue(
                WARNING, path,
                "This flight may have already departed (no timezone given).",
            ))
        elif delta < SHORT_NOTICE:
            issues.append(Issue(
                WARNING, path,
                "Departure is under 4 hours away. Many airlines close web check-in "
                "before then, so check-in may not be possible.",
            ))
    return issues


def check_unsupported_routes(payload: dict, now: datetime) -> list[Issue]:
    issues: list[Issue] = []
    for i, flight in _items(payload, "flights"):
        origin = _str(flight, "origin")
        destination = _str(flight, "destination")
        if origin in INDIA_AIRPORTS and destination in US_AIRPORTS:
            issues.append(Issue(
                WARNING, f"flights[{i}]",
                "India to US sectors are listed as excluded in Flyo's public fine print "
                "(in-person document verification). Expect REJECTED unless Flyo confirms "
                "otherwise. The airport lists used here are partial.",
            ))
    return issues


def check_passenger_names(payload: dict, now: datetime) -> list[Issue]:
    issues: list[Issue] = []
    for i, passenger in _items(payload, "passengers"):
        for field in ("first_name", "last_name"):
            value = _str(passenger, field)
            if value and not NAME_RE.match(value):
                issues.append(Issue(
                    ERROR, f"passengers[{i}].{field}",
                    "Names should contain letters only (spaces, hyphens and apostrophes are fine). "
                    "Use the name exactly as on the passport.",
                ))
    return issues


def check_contact(payload: dict, now: datetime) -> list[Issue]:
    issues: list[Issue] = []
    for i, passenger in _items(payload, "passengers"):
        base = f"passengers[{i}]"
        email = _str(passenger, "email")
        phone = _str(passenger, "phone")

        if not email and not phone:
            issues.append(Issue(
                WARNING, base,
                "No email or phone. Boarding passes are delivered over WhatsApp and email.",
            ))
        if email and not EMAIL_RE.match(email):
            issues.append(Issue(ERROR, f"{base}.email", "email does not look valid."))
        if phone and not PHONE_RE.match(phone):
            issues.append(Issue(
                ERROR, f"{base}.phone",
                "phone must be in E.164 format: + then country code and number, e.g. +919876543210.",
            ))
    return issues


def check_seat_preferences(payload: dict, now: datetime) -> list[Issue]:
    issues: list[Issue] = []
    for i, passenger in _items(payload, "passengers"):
        seat = passenger.get("seat_preference")
        if seat is None:
            continue
        base = f"passengers[{i}].seat_preference"
        if not isinstance(seat, dict):
            issues.append(Issue(ERROR, base, "seat_preference must be an object."))
            continue

        row = seat.get("row_preference")
        if row is not None and row not in ROW_PREFERENCES:
            issues.append(Issue(
                WARNING, f"{base}.row_preference",
                "Flyo's docs list front, middle or back for row_preference.",
            ))
        column = seat.get("column_preference")
        if column is not None and column not in COLUMN_PREFERENCES:
            issues.append(Issue(
                WARNING, f"{base}.column_preference",
                "Expected window, middle or aisle. Flyo's example uses window.",
            ))
    return issues


def check_callback(payload: dict, now: datetime) -> list[Issue]:
    callback = payload.get("callbackData")
    if not isinstance(callback, dict):
        return []

    issues: list[Issue] = []
    url = _str(callback, "callbackUrl")
    if not url:
        issues.append(Issue(
            WARNING, "callbackData.callbackUrl",
            "No callbackUrl. You will not receive webhook updates.",
        ))
    else:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme == "http":
            issues.append(Issue(ERROR, "callbackData.callbackUrl", "Use https, not http."))
        elif parsed.scheme != "https" or not host:
            issues.append(Issue(ERROR, "callbackData.callbackUrl", "callbackUrl must be a full https:// URL."))

        if host and (host in LOCAL_HOSTS or host.startswith(("127.", "192.168.", "10."))):
            issues.append(Issue(
                WARNING, "callbackData.callbackUrl",
                "This host is local or private, so Flyo cannot reach it. Use a public URL or a tunnel.",
            ))

    header = _str(callback, "auth_header")
    if not header:
        issues.append(Issue(
            WARNING, "callbackData.auth_header",
            "No auth_header. Without it you cannot verify that webhook calls come from Flyo.",
        ))
    elif not HEADER_RE.match(header):
        issues.append(Issue(
            WARNING, "callbackData.auth_header",
            'Expected "Header-Name: value", e.g. "X-API-Key: abc123".',
        ))
    return issues


def check_duplicate_passengers(payload: dict, now: datetime) -> list[Issue]:
    seen: dict[tuple[str, str], int] = {}
    issues: list[Issue] = []
    for i, passenger in _items(payload, "passengers"):
        key = (_str(passenger, "first_name").lower(), _str(passenger, "last_name").lower())
        if not all(key):
            continue
        if key in seen:
            issues.append(Issue(
                WARNING, f"passengers[{i}]",
                f"Same name as passengers[{seen[key]}]. Duplicate passenger?",
            ))
        else:
            seen[key] = i
    return issues
