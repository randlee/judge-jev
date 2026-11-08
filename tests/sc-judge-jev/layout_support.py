"""Where the plugin keeps its sources, and fresh renders of what install.py installs.

The plugin ships only the judge-jev-installer skill. The judge-jev skill, its
references, its scripts and any agents exist only as sources under
``install/``: ``install/templates/`` (sc-compose templates, ``<file>.md.j2`` and
``<script>.py.j2``, plus verbatim data) and ``install/harness/<target>/``
(agent frontmatter and registry). Prompt tests read a fresh render made by
install.py's own renderer.

Script tests run the scripts as installed: ``SCRIPTS`` is a fresh strict render
of every ``scripts/*.py.j2``. It is made by install.py's renderer when the
sc-compose wheel imports, else by the sc-compose CLI (the same engine, which CI
installs on every job; test_install.py checks the two agree byte for byte).
With neither, importing this module fails: a script test never runs against
unrendered sources.

``rendered()`` needs the sc-compose wheel. Without it the test is skipped,
unless ``JUDGE_JEV_REQUIRE_SC_COMPOSE=1`` (the CI installer job), where a
missing wheel is a failure.
"""
from __future__ import annotations

import atexit
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "sc-judge-jev"
INSTALL = PLUGIN / "install"
TEMPLATES = INSTALL / "templates"
HARNESS = INSTALL / "harness"
SKILL_SRC = TEMPLATES / "skills" / "judge-jev"
SCRIPT_TEMPLATES = SKILL_SRC / "scripts"   # the *.py.j2 sources; SCRIPTS (below) is their render
AGENT_TEMPLATES = TEMPLATES / "agents"
TARGETS = ("claude", "codex", "cursor")
REQUIRE_SC_COMPOSE = os.environ.get("JUDGE_JEV_REQUIRE_SC_COMPOSE") == "1"

_installer = None
_renders = {}
_scratch = None


def installer():
    """install.py, imported once as a module."""
    global _installer
    if _installer is None:
        spec = importlib.util.spec_from_file_location("sc_judge_jev_install", PLUGIN / "install.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _installer = module
    return _installer


def sc_compose():
    """The sc-compose module, or SkipTest (a failure under JUDGE_JEV_REQUIRE_SC_COMPOSE=1)."""
    inst = installer()
    found = inst.check_sc_compose()
    if isinstance(found, inst.Err):
        if REQUIRE_SC_COMPOSE:
            raise AssertionError(f"JUDGE_JEV_REQUIRE_SC_COMPOSE=1 but sc-compose is unavailable: {found.error.message}")
        raise unittest.SkipTest(f"sc-compose wheel not importable here ({found.error.message})")
    return found.value


def rendered() -> Path:
    """An install root holding every target as install.py renders it (made once per test process)."""
    if "all" not in _renders:
        inst = installer()
        package = inst.load_package()
        if isinstance(package, inst.Err):
            raise AssertionError(package.error.message)
        renderer = inst.Renderer(sc_compose(), package.value)
        files = inst.wanted_files(package.value, renderer, list(TARGETS))
        if isinstance(files, inst.Err):
            raise AssertionError(files.error.message)
        root = _scratch_dir() / "all"
        for key, (data, executable) in files.value.items():
            path = root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            if executable:
                path.chmod(0o755)
        _renders["all"] = root
    return _renders["all"]


def rendered_skill(target: str = "claude") -> Path:
    return rendered() / f".{target}" / "skills" / "judge-jev"


def rendered_agent(target: str, name: str) -> Path:
    return rendered() / f".{target}" / "agents" / name


def _scratch_dir() -> Path:
    global _scratch
    if _scratch is None:
        _scratch = Path(tempfile.mkdtemp(prefix="judge-jev-render-"))
        atexit.register(shutil.rmtree, _scratch, True)
    return _scratch


def render_cli(template: Path, out: Path) -> None:
    """Render one install template into ``out`` with the sc-compose CLI.

    The same strict render and final-newline rule as install.py's render_template.
    """
    binary = shutil.which("sc-compose")
    if binary is None:
        raise RuntimeError("the script tests need a rendered install: the sc-compose wheel or the sc-compose CLI "
                           "(scripts/install_sc_compose_ci.py) must be available")
    version = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))["version"]
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([binary, "render", "--root", str(template.parent), "--strict",
                           "--var", f"version={version}", "--file", str(template), "--output", str(out)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"sc-compose render {template.name} failed: {proc.stderr[-2000:]}")
    data = out.read_bytes()
    if not data.endswith(b"\n"):
        out.write_bytes(data + b"\n")


def render_skill_cli(dest: Path) -> None:
    """The judge-jev skill as install.py lays it out, rendered with the sc-compose CLI."""
    inst = installer()
    package = inst.load_package()
    if isinstance(package, inst.Err):
        raise AssertionError(package.error.message)
    for rel in package.value.skill:
        src = HARNESS / "claude" / rel if rel == "registry.yaml" else SKILL_SRC / rel
        out = dest / rel
        if rel in package.value.rendered:
            src = SKILL_SRC / f"{rel}.j2"
            render_cli(src, out)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out)
        if src.stat().st_mode & 0o100:
            out.chmod(0o755)


def render_scripts() -> Path:
    """The scripts directory of a rendered judge-jev skill (made once per test process)."""
    if "scripts" not in _renders:
        inst = installer()
        if isinstance(inst.check_sc_compose(), inst.Ok):
            skill = rendered_skill()
        else:
            skill = _scratch_dir() / "cli" / ".claude" / "skills" / "judge-jev"
            render_skill_cli(skill)
        _renders["scripts"] = skill / "scripts"
    return _renders["scripts"]


SCRIPTS = render_scripts()


def installed_scripts(root: Path, target: str = "claude", lock: bool = True) -> Path:
    """Copy the rendered scripts into ``root`` in the installed layout; returns the scripts directory.

    Only a copy in the nearest per-folder install that the installer recorded is trusted, so a test
    that needs a trusted script runs it from such a copy: ``lock`` (default) also writes
    ``.sc/judge-jev/install-lock.json`` listing the copied files, merged with a lock already there.
    ``lock=False`` leaves a hand-copied, untrusted layout.
    """
    dest = root / f".{target}" / "skills" / "judge-jev" / "scripts"
    shutil.copytree(SCRIPTS, dest, ignore=shutil.ignore_patterns("__pycache__"))
    if lock:
        lock_path = root / ".sc" / "judge-jev" / "install-lock.json"
        record = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.is_file() else {
            "package": "sc-judge-jev", "version": "test", "targets": [], "files": {}}
        if target not in record["targets"]:
            record["targets"].append(target)
        for path in sorted(dest.rglob("*")):
            if path.is_file():
                record["files"][path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest
