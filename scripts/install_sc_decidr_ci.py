#!/usr/bin/env python3
"""Install the exact published sc-decidr runtime pins from PyPI on a GitHub runner."""
from pathlib import Path
import re
import subprocess
import sys

TIMEOUT_SECONDS = 300


def run_child(argv):
    try:
        return subprocess.run(argv, check=True, stdin=subprocess.DEVNULL, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        print(f"install_sc_decidr_ci: subprocess timed out after {exc.timeout}s: {exc.cmd!r}", file=sys.stderr)
        raise SystemExit(2) from None


source = (Path(__file__).resolve().parent.parent / "plugins/sc-judge-jev/install/templates/skills/judge-jev/scripts/jev_judge.py.j2").read_text()
pins = {}
for package in ("sc-decidr", "sitr"):
    matches = re.findall(r'^\s*#\s*"' + re.escape(package) + r'==([0-9]+\.[0-9]+\.[0-9]+)",\s*$', source, re.M)
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {package} runtime pin")
    pins[package] = matches[0]
for package, version in pins.items():
    run_child([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
               "--index-url", "https://pypi.org/simple", f"{package}=={version}"])
