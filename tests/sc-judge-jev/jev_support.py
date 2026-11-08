"""A fresh render of the judge-jev skill's scripts, so every script test runs what an install would run.

``SCRIPTS`` is a strict sc-compose CLI render of every ``scripts/*.py.j2`` (the same
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
    for template in sorted(SCRIPT_TEMPLATES.glob("*.py.j2")):
        out = scripts / template.name[:-len(".j2")]
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
