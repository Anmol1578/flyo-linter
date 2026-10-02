"""Example payloads. Dates are relative to now so they never go stale."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

_FMT = "%Y-%m-%dT%H:%M:%S"


def _now(now):
    return now or datetime.now(timezone.utc)


def good_example(now: datetime | None = None) -> dict:
    departure = (_now(now) + timedelta(days=5)).replace(hour=10, minute=0, second=0, microsecond=0)
    return {
        "pnr": "ABC123",
        "flights": [
            {
                "airline": "6E",
                "flight_number": "6E2341",
                "origin": "DEL",
                "destination": "BOM",
                "departure_datetime": departure.strftime(_FMT),
            }
        ],
        "passengers": [
            {
                "first_name": "Priya",
                "last_name": "Sharma",
                "email": "priya@example.com",
                "phone": "+919876543210",
                "seat_preference": {"row_preference": "front", "column_preference": "window"},
            }
        ],
        "callbackData": {
            "clientId": "acme",
            "clientName": "Acme Travel",
            "callbackUrl": "https://acme.example.com/webhooks/flyo",
            "auth_header": "X-API-Key: A1B2C3D4E5F6G7H8",
        },
    }


def bad_example(now: datetime | None = None) -> dict:
    soon = (_now(now) + timedelta(hours=2)).strftime(_FMT)
    return {
        "pnr": "abc12",
        "flights": [
            {
                "airline": "6E",
                "flight_number": "AI101",
                "origin": "DEL",
                "destination": "JFK",
                "departure_datetime": soon,
            },
            {
                "airline": "SG",
                "flight_number": "SG8",
                "origin": "BOM",
                "destination": "BOM",
                "departure_datetime": "tomorrow",
            },
        ],
        "passengers": [
            {
                "first_name": "Priya2",
                "last_name": "Sharma",
                "email": "priya@example",
                "phone": "9876543210",
                "seat_preference": {"row_preference": "aisle"},
            }
        ],
        "callbackData": {
            "callbackUrl": "http://localhost:8000/hook",
            "auth_header": "flyo-key-123",
        },
    }
