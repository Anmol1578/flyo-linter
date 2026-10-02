import copy
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

VALID = {
    "pnr": "ABC123",
    "flights": [
        {
            "airline": "6E",
            "flight_number": "6E2341",
            "origin": "DEL",
            "destination": "BOM",
            "departure_datetime": "2026-09-20T10:00:00+05:30",
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


@pytest.fixture
def now():
    return NOW


@pytest.fixture
def payload():
    """A fresh, valid payload. Mutate it in a test to break one thing."""
    return copy.deepcopy(VALID)
