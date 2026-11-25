#!/usr/bin/env python3
"""Split item.text's statement into literal lexical terms, preserving code names."""
import json
from pathlib import Path
import re
import sys

STOPWORDS = frozenset('''a an and are as at be been being by can could for from
    if in into is it its must of on or shall should that the their then there
    these this those to was were when which will with would'''.split())


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
    # Keep code identifiers and negation, even when they look like prose stopwords.
    selected = (code or word for code, word in tokens
                if code or word.casefold() not in STOPWORDS)
    return [term for term in dict.fromkeys(selected) if term != "none"] + ["none"]


if __name__ == "__main__":
    print(json.dumps(terms(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))), ensure_ascii=False))
