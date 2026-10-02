# Flyo payload linter

A small tool that checks a [Flyo](https://www.flyo.ai) web check-in **subscribe** payload before you send it, so mistakes show up immediately instead of as a `REJECTED` response or a failed check-in on departure day.

Flyo's own docs call sending marketing-carrier details on codeshare bookings the most common integration mistake. This catches that and a set of other common payload problems.

> Unofficial. Built only from Flyo's public documentation and not affiliated with Flyo. The rules are heuristics, not Flyo's real validation logic.

## What it checks

| Check | Level |
| --- | --- |
| Required fields missing or wrong type | error |
| Flight number prefix does not match airline code (likely codeshare mix-up) | error |
| Invalid airline code, flight number, or airport code; origin equals destination | error |
| `departure_datetime` not ISO 8601, or already in the past | error |
| Departure under 4 hours away | warning |
| No timezone on `departure_datetime` | note |
| India to US sector (listed as excluded in Flyo's fine print; airport lists are partial) | warning |
| Passenger name with digits or symbols | error |
| Email invalid, phone not in E.164 format | error |
| No email or phone (boarding pass delivery needs one) | warning |
| Unexpected seat preference values | warning |
| `callbackUrl` not https, or local/private host | error / warning |
| Missing or malformed `auth_header` | warning |
| Duplicate passenger names | warning |

## Run it

```bash
pip install -r requirements.txt
uvicorn app:app --reload        # web UI at http://127.0.0.1:8000
```

Command line:

```bash
python cli.py --example bad > booking.json
python cli.py booking.json            # exit code 1 if there are errors
cat booking.json | python cli.py -
python cli.py booking.json --json     # machine-readable output
```

API:

```bash
curl -X POST http://127.0.0.1:8000/lint \
  -H "Content-Type: application/json" \
  -d @booking.json
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Add a rule

Each rule is a function in `linter/rules.py` that takes `(payload, now)` and returns a list of `Issue`s. Write one, add it to `RULES` in `linter/core.py`, and add a test in `tests/test_rules.py`.

## Deploy

On Render (or any host that runs Python):

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

## Limitations

- Codeshare detection only catches a flight number whose prefix differs from the airline code. It cannot look up the real operating carrier.
- Airport and route checks use format rules and a small partial list, not live airline data.
- Seat preference values and the 4-hour short-notice threshold are assumptions based on Flyo's examples and typical airline behaviour.
- Use fake or test passenger data. Do not paste real passport details into any hosted copy.
