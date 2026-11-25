#!/usr/bin/env python3
"""Split item.text's statement into literal lexical terms, preserving code names."""
import json
from pathlib import Path
import re
import sys


def terms(item):
    payload = json.loads(item["text"])
    if "statement" not in payload:
        # ADRs are judged per record: localize to an actual section, not a word
        # from an arbitrarily selected sentence.
        return [key for key in ("context", "decision", "rationale", "alternatives", "consequences")
                if key in payload] + ["none"]
    statement = payload["statement"]["text"]
    tokens = re.findall(r"`([^`]+)`|([\w]+(?:[-'][\w]+)*)", statement)
    # Keep the original case: Cancel (the type) differs from cancel (the verb).
    return list(dict.fromkeys(code or word for code, word in tokens)) + ["none"]


if __name__ == "__main__":
    print(json.dumps(terms(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))), ensure_ascii=False))
