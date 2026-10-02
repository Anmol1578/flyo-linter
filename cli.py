#!/usr/bin/env python3
"""Lint a Flyo subscribe payload from the command line.

    python cli.py booking.json
    cat booking.json | python cli.py -
    python cli.py --example bad
"""
import argparse
import json
import sys

from linter import lint, summarize
from linter.examples import bad_example, good_example


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint a Flyo web check-in subscribe payload.")
    parser.add_argument("file", nargs="?", help="JSON file to check, or - for stdin")
    parser.add_argument("--example", choices=["good", "bad"], help="print an example payload and exit")
    parser.add_argument("--json", action="store_true", help="print results as JSON")
    args = parser.parse_args()

    if args.example:
        example = good_example() if args.example == "good" else bad_example()
        print(json.dumps(example, indent=2))
        return 0

    if not args.file:
        parser.error("provide a file path, - for stdin, or --example")

    try:
        raw = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
        payload = json.loads(raw)
    except (OSError, ValueError) as exc:
        print(f"Could not read JSON: {exc}", file=sys.stderr)
        return 2

    issues = lint(payload)
    summary = summarize(issues)

    if args.json:
        print(json.dumps({**summary, "issues": [i.to_dict() for i in issues]}, indent=2))
    else:
        for issue in issues:
            print(f"{issue.level.upper():8}{issue.path}\n        {issue.message}\n")
        c = summary["counts"]
        print(f"{c['error']} errors, {c['warning']} warnings, {c['info']} notes")

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
