#!/usr/bin/env python3
"""Offer phrases between stopwords, preserving whole backticked names."""
import json
from pathlib import Path
import re
import sys

STOPWORDS = frozenset('''a against an and are as at be been being by can could for from
    if in into is it its must of on or shall should that the their then there
    these this those through to was were when which will with would'''.split())


def terms(item):
    payload = json.loads(item["text"])
    if "statement" not in payload:
        # ADRs are judged per record: localize to an actual section, not a word
        # from an arbitrarily selected sentence.
        return [key for key in ("context", "decision", "rationale", "alternatives", "consequences")
                if key in payload] + ["none"]
    statement = payload["statement"]["text"]
    phrases, words = [], []

    def flush():
        if words:
            phrases.append(" ".join(words))
            words.clear()

    end = 0
    for token in re.finditer(r"`([^`]+)`|([\w]+(?:[-'’][\w]+)*)", statement):
        # Punctuation ends a run, but punctuation inside a code span does not.
        if statement[end:token.start()].strip():
            flush()
        code, word = token.groups()
        if code:
            words.append(code)
        elif word.casefold() in STOPWORDS:
            flush()
        else:
            words.append(word)
        end = token.end()
    flush()
    return [phrase for phrase in dict.fromkeys(phrases) if phrase != "none"] + ["none"]


if __name__ == "__main__":
    print(json.dumps(terms(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))), ensure_ascii=False))
