#!/usr/bin/env python3
"""Install the runtime-pinned sc-decidr prerelease on a GitHub runner."""
import os
from pathlib import Path
import re
import subprocess
import sys

source = (Path(__file__).resolve().parent.parent / "plugins/sc-judge-jev/install/templates/skills/judge-jev/scripts/jev_judge.py.j2").read_text()
match = re.search(r'^\s*#\s*"sc-decidr==([0-9]+\.[0-9]+\.[0-9]+)",\s*$', source, re.M)
if match is None:
    raise SystemExit("Missing exact sc-decidr runtime pin")
platforms = {("Linux", "X64"): "manylinux_2_28_x86_64", ("Linux", "ARM64"): "manylinux_2_28_aarch64",
             ("macOS", "X64"): "macosx_11_0_x86_64", ("macOS", "ARM64"): "macosx_11_0_arm64",
             ("Windows", "X64"): "win_amd64", ("Windows", "ARM64"): "win_arm64"}
runner = (os.environ.get("RUNNER_OS"), os.environ.get("RUNNER_ARCH"))
if runner not in platforms:
    raise SystemExit(f"No sc-decidr wheel for {runner}")
version = match.group(1)
asset = f"sc_decidr-{version}-cp311-abi3-{platforms[runner]}.whl"
subprocess.run(["gh", "release", "download", f"prerelease/v{version}", "--repo", "randlee/sc-agent", "--pattern", asset], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", asset], check=True)
