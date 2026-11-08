"""A fresh render of the judge-jev skill's scripts, so every script test runs what an install would run.

``SCRIPTS`` is a strict sc-compose CLI render of every ``scripts/*.py.j2`` and ``references/*.md.j2`` (the same
``sc-compose render --strict`` call plan-anchor's ``layout_support.render_cli`` makes),
laid out beside a copy of the skill's ``assets/`` exactly as installed. With no
``sc-compose`` on PATH importing this module fails: a script test never runs against
unrendered sources. The scripts directory is put on ``sys.path``.
"""
from __future__ import annotations

import atexit
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "sc-judge-jev"
SKILL_SRC = PLUGIN / "install" / "templates" / "skills" / "judge-jev"
SCRIPT_TEMPLATES = SKILL_SRC / "scripts"
RENDER_VERSION = "0.0.0-test"


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
        proc = subprocess.run([binary, "render", "--root", str(template.parent), "--strict",
                               "--var", f"version={RENDER_VERSION}", "--file", str(template), "--output", str(out)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"sc-compose render {template.name} failed: {proc.stderr[-2000:]}")
        data = out.read_bytes()
        if not data.endswith(b"\n"):
            out.write_bytes(data + b"\n")
    return scripts


_scratch = Path(tempfile.mkdtemp(prefix="judge-jev-render-"))
atexit.register(shutil.rmtree, _scratch, True)
SCRIPTS = _render(_scratch)
SKILL = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _plain(value):
    """An sc-observability stored value as plain JSON data; the binding's own ``sc_observability.*`` fields dropped."""
    if hasattr(value, "items"):
        return {k: _plain(v) for k, v in value.items() if not k.startswith("sc_observability.")}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if getattr(value, "kind", None) == "null":
        return None
    if hasattr(value, "kind") and hasattr(value, "value"):
        return _plain(value.value)
    return value


def read_log(log_root, action=None):
    """The run log's events, oldest first, read back through sc-observability's own query API (never by parsing the
    file): [{"action", "correlation_id", "fields"}]."""
    import sc_observability as sco
    created = sco.create_logger(sco.LoggerConfig(service="judge-jev", log_root=str(log_root)))
    if isinstance(created, sco.Err):
        raise AssertionError(f"could not open the log under {log_root}: {created.error}")
    logger = created.value
    try:
        got = logger.query(sco.LogQuery(service="judge-jev", action=action, limit=1000))
    finally:
        logger.shutdown()
    if isinstance(got, sco.Err):
        raise AssertionError(f"log query failed: {got.error}")
    return [{"action": e.action, "correlation_id": e.correlation_id, "fields": _plain(e.fields)} for e in got.value.events]


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
