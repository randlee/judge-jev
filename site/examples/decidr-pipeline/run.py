#!/usr/bin/env python3
"""Replay recorded results, or run the decidr/jq pipeline live. See README.md."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from decision_examples import main
if __name__ == '__main__':
    raise SystemExit(main('decidr-pipeline'))
