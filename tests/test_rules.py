from datetime import timedelta

from linter import lint, summarize
from linter.examples import bad_example, good_example


def find(issues, path, level=None):
    return [i for i in issues if i.path == path and (level is None or i.level == level)]


def test_valid_payload_has_no_issues(payload, now):
    assert lint(payload, now) == []


def test_non_object_payload(now):
    issues = lint(["not", "an", "object"], now)
    assert [i.path for i in issues] == ["$"]


# ---- structure
def test_missing_top_level_fields(now):
    issues = lint({}, now)
    paths = {i.path for i in issues}
    assert {"pnr", "flights", "passengers"} <= paths


def test_missing_flight_field(payload, now):
    del payload["flights"][0]["origin"]
    assert find(lint(payload, now), "flights[0].origin", "error")


def test_missing_callback_data_is_info_only(payload, now):
    del payload["callbackData"]
    issues = lint(payload, now)
    assert find(issues, "callbackData", "info")
    assert summarize(issues)["ok"]


def test_wrong_types_do_not_crash(now):
    bad = {"pnr": 123, "flights": "x", "passengers": [1, None], "callbackData": []}
    assert lint(bad, now)  # returns issues instead of raising


# ---- pnr
def test_pnr_with_symbols(payload, now):
    payload["pnr"] = "AB-123"
    assert find(lint(payload, now), "pnr", "error")


def test_pnr_lowercase_and_length(payload, now):
    payload["pnr"] = "abc12"
    messages = [i.message for i in find(lint(payload, now), "pnr", "warning")]
    assert any("lowercase" in m for m in messages)
    assert any("5 characters" in m for m in messages)


# ---- airline / flight number (codeshare)
def test_codeshare_prefix_mismatch(payload, now):
    payload["flights"][0]["flight_number"] = "AI101"
    issues = find(lint(payload, now), "flights[0].flight_number", "error")
    assert issues and "operating carrier" in issues[0].message


def test_bad_airline_code(payload, now):
    payload["flights"][0]["airline"] = "indigo"
    assert find(lint(payload, now), "flights[0].airline", "error")


def test_bad_flight_number_format(payload, now):
    payload["flights"][0]["flight_number"] = "6E-2341"
    assert find(lint(payload, now), "flights[0].flight_number", "error")


# ---- airports
def test_bad_airport_code(payload, now):
    payload["flights"][0]["origin"] = "Delhi"
    assert find(lint(payload, now), "flights[0].origin", "error")


def test_same_origin_and_destination(payload, now):
    payload["flights"][0]["destination"] = "DEL"
    assert find(lint(payload, now), "flights[0].destination", "error")


# ---- departure
def test_departure_not_iso(payload, now):
    payload["flights"][0]["departure_datetime"] = "tomorrow"
    assert find(lint(payload, now), "flights[0].departure_datetime", "error")


def test_departure_in_past(payload, now):
    payload["flights"][0]["departure_datetime"] = (now - timedelta(days=1)).isoformat()
    assert find(lint(payload, now), "flights[0].departure_datetime", "error")


def test_departure_under_four_hours(payload, now):
    payload["flights"][0]["departure_datetime"] = (now + timedelta(hours=2)).isoformat()
    assert find(lint(payload, now), "flights[0].departure_datetime", "warning")


def test_departure_far_in_future_is_fine(payload, now):
    payload["flights"][0]["departure_datetime"] = (now + timedelta(days=90)).isoformat()
    assert lint(payload, now) == []


def test_naive_datetime_gets_timezone_note(payload, now):
    payload["flights"][0]["departure_datetime"] = "2026-09-20T10:00:00"
    issues = find(lint(payload, now), "flights[0].departure_datetime")
    assert [i.level for i in issues] == ["info"]


def test_naive_datetime_slightly_past_is_only_a_warning(payload, now):
    payload["flights"][0]["departure_datetime"] = (now - timedelta(hours=3)).replace(tzinfo=None).isoformat()
    levels = {i.level for i in find(lint(payload, now), "flights[0].departure_datetime")}
    assert "error" not in levels and "warning" in levels


# ---- unsupported routes
def test_india_to_us_warning(payload, now):
    payload["flights"][0]["destination"] = "JFK"
    assert find(lint(payload, now), "flights[0]", "warning")


# ---- passengers
def test_name_with_digits(payload, now):
    payload["passengers"][0]["first_name"] = "Priya2"
    assert find(lint(payload, now), "passengers[0].first_name", "error")


def test_name_with_hyphen_and_apostrophe_is_ok(payload, now):
    payload["passengers"][0]["last_name"] = "O'Neil-Smith"
    assert lint(payload, now) == []


def test_invalid_email(payload, now):
    payload["passengers"][0]["email"] = "priya@example"
    assert find(lint(payload, now), "passengers[0].email", "error")


def test_phone_without_country_code(payload, now):
    payload["passengers"][0]["phone"] = "9876543210"
    assert find(lint(payload, now), "passengers[0].phone", "error")


def test_no_contact_details(payload, now):
    del payload["passengers"][0]["email"]
    del payload["passengers"][0]["phone"]
    assert find(lint(payload, now), "passengers[0]", "warning")


def test_unknown_seat_preference(payload, now):
    payload["passengers"][0]["seat_preference"]["row_preference"] = "exit"
    assert find(lint(payload, now), "passengers[0].seat_preference.row_preference", "warning")


def test_duplicate_passengers(payload, now):
    payload["passengers"].append(dict(payload["passengers"][0]))
    assert find(lint(payload, now), "passengers[1]", "warning")


# ---- callback
def test_http_callback_url(payload, now):
    payload["callbackData"]["callbackUrl"] = "http://acme.example.com/hook"
    assert find(lint(payload, now), "callbackData.callbackUrl", "error")


def test_localhost_callback_url(payload, now):
    payload["callbackData"]["callbackUrl"] = "https://localhost:8000/hook"
    assert find(lint(payload, now), "callbackData.callbackUrl", "warning")


def test_missing_auth_header(payload, now):
    del payload["callbackData"]["auth_header"]
    assert find(lint(payload, now), "callbackData.auth_header", "warning")


def test_auth_header_wrong_shape(payload, now):
    payload["callbackData"]["auth_header"] = "just-a-token"
    assert find(lint(payload, now), "callbackData.auth_header", "warning")


# ---- ordering and examples
def test_errors_sort_before_warnings(payload, now):
    payload["pnr"] = "abc12"          # warnings
    payload["flights"][0]["origin"] = "x"  # error
    levels = [i.level for i in lint(payload, now)]
    assert levels == sorted(levels, key={"error": 0, "warning": 1, "info": 2}.get)


def test_good_example_passes(now):
    assert summarize(lint(good_example(now), now))["ok"]


def test_bad_example_fails_in_many_ways(now):
    summary = summarize(lint(bad_example(now), now))
    assert not summary["ok"]
    assert summary["counts"]["error"] >= 5


# ---- flight number spacing
def test_space_in_flight_number_is_a_warning(payload, now):
    payload["flights"][0]["flight_number"] = "6E 2341"
    issues = find(lint(payload, now), "flights[0].flight_number")
    assert [i.level for i in issues] == ["warning"]


def test_space_does_not_hide_codeshare_mismatch(payload, now):
    payload["flights"][0]["flight_number"] = "AI 101"
    levels = [i.level for i in find(lint(payload, now), "flights[0].flight_number")]
    assert "error" in levels


def test_three_letter_airline_prefix_is_rejected(payload, now):
    payload["flights"][0]["flight_number"] = "IGO2341"
    assert find(lint(payload, now), "flights[0].flight_number", "error")
