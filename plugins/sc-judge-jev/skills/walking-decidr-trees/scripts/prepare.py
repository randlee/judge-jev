#!/usr/bin/env python3
"""Build the REQ-SAG-0104.s3 example from a supplied record, without git/network calls."""
import argparse
import json
from pathlib import Path
import re

QUESTIONS = {
    "obligations": {
        "type": "choice",
        "instructions": "`item.text` is JSON: `statement` is one MUST or MUST NOT statement of the requirement record in `record`. Judge only `statement`; use `record` as context. How many independent obligations does this statement impose?",
        "criteria": {
            "1": "One obligation.",
            "2": "Two independent obligations.",
            "3": "Three independent obligations.",
            "4+": "Four or more independent obligations."
        }
    },
    "term": {
        "type": "choice",
        "instructions": "`item.text` is JSON: `statement` is one MUST or MUST NOT statement of the requirement record in `record`. Judge only `statement`; use `record` as context. Is every term in this statement common usage, defined in this record, or defined in a linked record?",
        "criteria": {
            "yes": "Every term is common usage, defined in this record, or defined in a linked record.",
            "no": "At least one term is none of these."
        }
    },
    "checkable": {
        "type": "choice",
        "instructions": "`item.text` is JSON: `statement` is one MUST or MUST NOT statement of the requirement record in `record`. Judge only `statement`; use `record` as context. Can a tester decide whether this statement holds?",
        "criteria": {
            "yes": "Yes, by a test, a command run, or reading files.",
            "needs a measure": "A check exists only once a measure is stated.",
            "no": "Nothing could check it."
        }
    }
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="REQ-SAG-0104 Markdown from sc-agent plan/phase-j")
    parser.add_argument("output", type=Path, help="new output directory; refuses to overwrite")
    args = parser.parse_args()
    record = args.record.read_text(encoding="utf-8")
    statements = re.findall(r"^- (.+ MUST(?: NOT)? .+)$", record, re.MULTILINE)
    if "## REQ-SAG-0104:" not in record or len(statements) != 4:
        parser.error("expected REQ-SAG-0104 with four MUST statements")
    statement = {"index": 3, "text": statements[2]}
    item = {"id": "REQ-SAG-0104.s3", "title": "Cancel token",
            "text": json.dumps({"statement": statement, "record": record}, ensure_ascii=False)}
    request = {"state": {"item": item}, "questions": QUESTIONS}
    args.output.mkdir(parents=True, exist_ok=False)
    for name, value in (("item.json", item), ("request.json", request)):
        (args.output / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"item": str(args.output / "item.json"), "request": str(args.output / "request.json")}))


if __name__ == "__main__":
    main()
