"""A fresh render of the judge-jev skill's scripts, so every script test runs what an install would run.

``SCRIPTS`` is a strict sc-compose CLI render of every ``scripts/*.py.j2`` and ``references/*.md.j2`` (the same
``sc-compose render --strict`` call plan-anchor's ``layout_support.render_cli`` makes),
laid out beside a copy of the skill's ``assets/`` exactly as installed. With no
``sc-compose`` on PATH importing this module fails: a script test never runs against
unrendered sources. The scripts directory is put on ``sys.path``.
"""
from __future__ import annotations

import atexit
import json
import os
from unittest import mock
from pathlib import Path
import shutil
from child_support import run_child
from layout_support import installer
import sys
import tempfile

_log_scratch = tempfile.TemporaryDirectory(prefix="judge-jev-native-logs-")
_log_environment = mock.patch.dict(os.environ, {"JUDGE_JEV_LOG_ROOT": _log_scratch.name})
_log_environment.start()
atexit.register(_log_scratch.cleanup)
atexit.register(_log_environment.stop)

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "sc-judge-jev"
SKILL_SRC = PLUGIN / "install" / "templates" / "skills" / "judge-jev"
SCRIPT_TEMPLATES = SKILL_SRC / "scripts"
RENDER_VERSION = "0.0.0-test"
_installer = installer()
_package = _installer.load_package()
if isinstance(_package, _installer.Err):
    raise RuntimeError(_package.error.message)
SC_DECIDR_VERSION = _package.value.sc_decidr_version
SITR_VERSION = _package.value.sitr_version


def _render(dest: Path) -> Path:
    binary = shutil.which("sc-compose")
    if binary is None:
        raise RuntimeError("the script tests need the sc-compose CLI on PATH to render scripts/*.py.j2")
    skill = dest / ".claude" / "skills" / "judge-jev"
    shutil.copytree(SKILL_SRC / "assets", skill / "assets")
    scripts = skill / "scripts"
    scripts.mkdir(parents=True)
    (skill / "references").mkdir()
    templates = [(t, scripts) for t in sorted(SCRIPT_TEMPLATES.glob("*.py.j2"))]
    templates += [(t, skill / "references") for t in sorted((SKILL_SRC / "references").glob("*.md.j2"))]
    for template, target in templates:
        out = target / template.name[:-len(".j2")]
        proc = run_child([binary, "render", "--root", str(template.parent), "--strict",
                               "--var", f"version={RENDER_VERSION}",
                               "--var", f"sc_decidr_version={SC_DECIDR_VERSION}",
                               "--var", f"sitr_version={SITR_VERSION}",
                               "--file", str(template), "--output", str(out)],
                              text=True, encoding="utf-8", errors="replace", check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"sc-compose render {template.name} failed: {proc.stderr[-2000:]}")
        data = out.read_bytes()
        if not data.endswith(b"\n"):
            out.write_bytes(data + b"\n")
    import importlib.resources
    template = Path(str(importlib.resources.files("sc_agent") / "templates" / "consumer.py.j2"))
    out = scripts / "decidr_client.py"
    proc = run_child([binary, "render", "--root", str(template.parent), "--strict",
                      "--var", "client_name=judge-jev", "--var", "sitr=true",
                      "--var", f"sc_decidr_version={SC_DECIDR_VERSION}",
                      "--var", f"tool_version={_package.value.version}",
                      "--file", str(template), "--output", str(out)],
                     text=True, encoding="utf-8", errors="replace", check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"sc-compose render wheel client failed: {proc.stderr[-2000:]}")
    return scripts


_scratch = Path(tempfile.mkdtemp(prefix="judge-jev-render-"))
atexit.register(shutil.rmtree, _scratch, True)
SCRIPTS = _render(_scratch)
SKILL = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def read_log(log_root, action=None):
    """Read the test's explicit native JSONL file without creating a second Logger."""
    path = Path(log_root) / "logs/judge-jev.log.jsonl"
    if not path.exists():
        return []
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return [event for event in events if event["service"] == "judge-jev" and (action is None or event["action"] == action)]


def log_lines(log_root, extra_keys=("run",)):
    """The batch result lines rebuilt from the log: each result event plus its request event's request and its answer
    event's raw response (None when there is none, as on a dry run). ``extra_keys`` are fields the log adds."""
    out, request, answer = [], None, None
    for event in read_log(log_root):
        fields = event["fields"]
        if event["action"] == "request":
            request, answer = fields, None
        elif event["action"] == "answer":
            answer = fields
        elif event["action"] == "result":
            line = {k: v for k, v in fields.items() if k not in extra_keys}
            line["request"] = request["request"]
            line["raw_response"] = answer["raw_response"] if answer is not None else None
            out.append(line)
    return out
