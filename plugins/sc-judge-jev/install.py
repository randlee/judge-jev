#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyyaml>=5.1",
#   "sc-compose>=1.7.0,<2",
# ]
# ///
"""Install judge-jev (the judge-jev skill) into a folder.

    uv run install.py --dest <folder>
        [--target claude,codex,cursor] [--overwrite] [--dry-run]
        [--allow-remote-judge | --no-remote-judge]
    uv run install.py --dest <folder> --status     # read-only: installed vs installer version

The marketplace plugin ships only the ``judge-jev-installer`` skill; it runs
this script.

The inline script metadata above lets ``uv run`` supply PyYAML and the
sc-compose wheel. judge-jev's floor is Python 3.11, with wheels for 3.11 or
newer; ``python3 install.py`` works on 3.11+ wherever both packages import.

What it reads:
  - Its package files, under this plugin directory: ``plugin.json`` (the
    version), the templates and verbatim assets under ``install/templates/``,
    the harness frontmatter and registries under ``install/harness/`` and
    ``install/legacy-owned.json``.
  - At the destination: the destination's ``.sc/judge-jev/settings.yaml``
    (``allow_remote_judge`` is read only from the destination's own file);
    the destination's ``.sc/judge-jev/install-lock.json`` (when it has none,
    ``--status`` reports the nearest one above); ``.git``, only whether it
    exists, to find the repository root (git is never run); the files already
    at the install paths and at the paths the lock records, to check
    ownership; every file under each existing ``.<target>/skills/judge-jev/``
    (read when the lock records none there, to spot a foreign directory, and
    listed to warn about stray files); and, with no lock (a migration), the
    paths earlier versions shipped (``install/legacy-owned.json``).
  - The home directory (``HOME``, else the password database; on Windows
    ``USERPROFILE`` or ``HOMEDRIVE`` + ``HOMEPATH``), to refuse global destinations and to end
    each upward walk before it (at the filesystem root when it is unknown).

What it runs: sc-compose and PyYAML are imported as Python libraries, never
run as commands. It runs no external command.

Destination. Any folder: a repository, a folder inside one, or a parent folder
holding many repositories (they inherit it: the nearest install and the
nearest settings file win). Global
harness locations are refused with ``INSTALL.DEST_GLOBAL``: the home directory
itself, anything inside ``~/.claude``, ``~/.codex``, ``~/.cursor``,
``~/.agents``, ``/etc/codex`` or Claude Code's managed-settings directory
(which covers every plugin cache), and this plugin's own directory.

Targets. The harnesses written are the union of: the targets the lock records;
every harness whose ``.<target>/skills/judge-jev/`` exists (an install,
locked or not); every harness directory (``.claude/``, ``.codex/``,
``.cursor/``) present at the destination; and any ``--target``. ``--target``
only adds; it never removes. With none of these, the target is ``claude``. So
an upgrade upgrades every harness the folder uses. ``data.target_reasons``
gives each chosen target's reasons (``locked``, ``installed``, ``present``,
``requested``, ``default``); ``--status`` lists in ``missing_targets`` the
harness directories present with no judge-jev install.

What it writes, per target:
  <dest>/.<target>/skills/judge-jev/...        the skill (and registry.yaml for the agents)
  <dest>/.<target>/agents/*.md                 the agents, when the package ships any
and once per destination:
  <dest>/.sc/judge-jev/settings.yaml           ``allow_remote_judge`` when a flag gives it;
                                               written when the value changes
  <dest>/.sc/judge-jev/install-lock.json       version, targets, sha256 per file
  <dest>/.backup/<UTC>/<path>                  files ``--overwrite`` moved aside, and
  <dest>/.backup/.gitignore                    ``*``, so the backups are not committed

Templates. Every installed Markdown file and script (SKILL.md, every
reference, every agent body and every ``scripts/*.py``) is an sc-compose
template under ``install/templates/`` (``<file>.md.j2``, ``<script>.py.j2``)
that renders strictly with the package ``version``. Other files are copied
verbatim. A ``.j2`` file is an install-time template when its frontmatter
``name`` starts with ``sc-judge-jev-``. Agent frontmatter per harness lives in
``install/harness/<target>/agents/``, the agent registry in
``install/harness/<target>/registry.yaml``.

Remote judging. ``--allow-remote-judge`` / ``--no-remote-judge`` record the
user's answer to whether record text may be sent to TypeSafe (Jev) as
``allow_remote_judge: true|false``; live Jev calls are refused until it is
``true``. Without either flag the destination's existing value (or its
absence) is kept; a parent folder's consent is never copied.

Ownership. A rerun (the upgrade path) replaces a file only when its bytes are
what the lock says this installer wrote; it removes files this version no
longer ships when they are unchanged; it fails naming a modified or foreign
file (``INSTALL.CONFLICT``) unless ``--overwrite`` moves it to
``<dest>/.backup/<UTC>/<path>``. A folder installed without the lock is
migrated once: a file is owned when its bytes match something an earlier
version shipped (``install/legacy-owned.json``) or this version renders.
Every check runs before anything is written; ``--dry-run`` stops there.

The plugin's SessionStart hook (``hooks/hooks.json``, ``hooks/check_install.py``):
Claude Code runs it; Codex and Cursor plugin hook discovery is untested.

Output: the JSON envelope ``{success, data, error}``; exit 0 when the command
ran, with negative results in ``data`` (``--status`` included, whatever state
it found); 2 with a typed ``error.code`` on any error (an unexpected exception
is ``SCRIPT.INTERNAL``); 130 on an interrupt (code ``CANCELED``).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple
from types import ModuleType

PLUGIN_DIR = Path(__file__).resolve().parent
SKILL_NAME = "judge-jev"
INSTALL_DIR = PLUGIN_DIR / "install"
TEMPLATES_DIR = INSTALL_DIR / "templates"
SKILL_SRC = TEMPLATES_DIR / "skills" / SKILL_NAME
HARNESS_DIR = INSTALL_DIR / "harness"
SCRIPTS_DIR = SKILL_SRC / "scripts"
TEMPLATE_SYNTAX = ("{{", "{%", "{#")


def template_body(text: str) -> str:
    """The text after an sc-compose template's ``---`` frontmatter (the whole text when there is none)."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated frontmatter")
    return text[end + len("\n---\n"):]


def _load_plain_script(name: str) -> ModuleType:
    """Import ``scripts/<name>.py.j2``, a script template whose body has no template syntax.

    Its rendering is its body, byte for byte (test_install.py renders it strictly and
    compares), so the installer runs the code it installs without needing sc-compose to
    import. Only result.py and judge_jev_paths.py are loaded this way.
    """
    path = SCRIPTS_DIR / f"{name}.py.j2"
    body = template_body(path.read_text(encoding="utf-8"))
    if any(token in body for token in TEMPLATE_SYNTAX):
        raise RuntimeError(f"{path.name} uses template syntax; the installer cannot import it unrendered")
    module = ModuleType(f"sc_judge_jev_install_{name}")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module  # dataclasses resolve their module through sys.modules
    exec(compile(body, str(path), "exec"), module.__dict__)
    return module


_result = _load_plain_script("result")
_paths = _load_plain_script("judge_jev_paths")
Err, Ok, Result, ToolError, err, utf8_stdio = (_result.Err, _result.Ok, _result.Result, _result.ToolError,
                                               _result.err, _result.utf8_stdio)
find_lock, find_settings, global_location = _paths.find_lock, _paths.find_settings, _paths.global_location

PACKAGE = "sc-judge-jev"
LEGACY_PATH = INSTALL_DIR / "legacy-owned.json"
LOCK_RELPATH = ".sc/judge-jev/install-lock.json"
BACKUP_DIR = ".backup"
TARGETS = ("claude", "codex", "cursor")
REGISTRY = "registry.yaml"   # per-target file installed in the skill directory
TEMPLATE_NAME_PREFIX = "name: sc-judge-jev-"
SC_COMPOSE_FLOOR = (1, 7, 0)
SC_COMPOSE_CEILING_MAJOR = 2
SC_COMPOSE_SPEC = "sc-compose>=1.7.0,<2"
IGNORED = frozenset({"__pycache__", ".DS_Store"})
ERROR_EXIT = 2


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def version_tuple(version: Optional[str]) -> Optional[Tuple[int, int, int]]:
    m = re.fullmatch(r"([0-9]+)\.([0-9]+)\.([0-9]+)", version or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


# ---------------------------------------------------------------- package data


@dataclass(frozen=True)
class Package:
    version: str
    skill: Tuple[str, ...]                    # paths under .<target>/skills/judge-jev/
    rendered: frozenset                       # skill paths rendered from <rel>.j2
    agents: Tuple[str, ...]                   # agent file names, the same for every target
    legacy_skill: Dict[str, Set[str]]
    legacy_agents: Dict[str, Dict[str, Set[str]]]


def _read_json(path: Path, code: str) -> Result[Any, ToolError]:
    try:
        return Ok(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError) as exc:
        return err(code, f"{path} could not be read: {type(exc).__name__}: {exc}",
                   "Reinstall the plugin (or restore plugins/sc-judge-jev in a source checkout).")
    except json.JSONDecodeError as exc:
        return err(code, f"{path} is not valid JSON: {exc.msg}",
                   "Reinstall the plugin, or regenerate it with scripts/gen_install_data.py in a source checkout.")


def is_install_template(path: Path) -> bool:
    """A ``.j2`` whose sc-compose frontmatter names it ``sc-judge-jev-*`` (runtime templates are copied)."""
    if path.suffix != ".j2":
        return False
    try:
        with path.open(encoding="utf-8") as handle:
            first, second = handle.readline(), handle.readline()
    except (OSError, UnicodeError):
        return False
    return first == "---\n" and second.startswith(TEMPLATE_NAME_PREFIX)


def _tree(base: Path) -> List[Path]:
    return sorted(p for p in base.rglob("*") if p.is_file() and not IGNORED & set(p.relative_to(base).parts))


def load_package(plugin_dir: Path = PLUGIN_DIR) -> Result[Package, ToolError]:
    bad = "INSTALL.PACKAGE_INVALID"
    plugin = _read_json(plugin_dir / "plugin.json", bad)
    if isinstance(plugin, Err):
        return plugin
    version = plugin.value.get("version") if isinstance(plugin.value, dict) else None
    if not isinstance(version, str) or version_tuple(version) is None:
        return err(bad, f"{plugin_dir / 'plugin.json'} declares no X.Y.Z version")
    skill_src = plugin_dir / "install" / "templates" / "skills" / SKILL_NAME
    agents_src = plugin_dir / "install" / "templates" / "agents"
    harness = plugin_dir / "install" / "harness"
    if not skill_src.is_dir():
        return err(bad, f"{plugin_dir} has no install/templates/ tree", "Reinstall the plugin.")
    skill: List[str] = []
    rendered: Set[str] = set()
    for path in _tree(skill_src):
        rel = path.relative_to(skill_src).as_posix()
        if is_install_template(path):
            rel = rel[: -len(".j2")]
            rendered.add(rel)
        skill.append(rel)
    if "SKILL.md" not in rendered:
        return err(bad, f"install/templates/skills/{SKILL_NAME}/SKILL.md.j2 is missing")
    if REGISTRY in skill:
        return err(bad, f"install/templates/skills/{SKILL_NAME}/{REGISTRY} would shadow the per-target registry")
    skill.append(REGISTRY)
    agents = []
    for path in _tree(agents_src) if agents_src.is_dir() else []:  # a package may ship no agents
        if not is_install_template(path) or path.parent != agents_src:
            return err(bad, f"{path.relative_to(plugin_dir).as_posix()} is not an agent template")
        agents.append(path.name[: -len(".j2")])
    for target in TARGETS:
        for name in [*(f"agents/{a}" for a in agents), REGISTRY]:
            if not (harness / target / name).is_file():
                return err(bad, f"install/harness/{target}/{name} is missing")
    legacy = _read_json(plugin_dir / "install" / "legacy-owned.json", bad)
    if isinstance(legacy, Err):
        return legacy
    lg = legacy.value
    try:
        legacy_skill = {rel: set(shas) for rel, shas in lg["skill"].items()}
        legacy_agents = {t: {n: set(s) for n, s in lg["agents"].get(t, {}).items()} for t in TARGETS}
    except (KeyError, TypeError, AttributeError) as exc:
        return err(bad, f"install/legacy-owned.json is malformed ({exc})", "Regenerate it with scripts/gen_install_data.py.")
    return Ok(Package(version, tuple(sorted(skill)), frozenset(rendered), tuple(agents), legacy_skill, legacy_agents))


# ---------------------------------------------------------------- dependencies


def check_sc_compose() -> Result[Any, ToolError]:
    action = (f"Run with `uv run {Path(__file__).name}` (it installs {SC_COMPOSE_SPEC} itself), or "
              f"python3 -m pip install '{SC_COMPOSE_SPEC}' (CPython 3.11 wheels).")
    try:
        module = importlib.import_module("sc_compose")
    except ImportError as exc:
        return err("DEPENDENCY.SC_COMPOSE", f"the sc-compose wheel is not importable: {exc}", action)
    try:
        from importlib import metadata
        version = metadata.version("sc-compose")
    except Exception as exc:  # metadata lookups raise several types; any means "unknown"
        return err("DEPENDENCY.SC_COMPOSE", f"the sc-compose wheel version is unknown: {type(exc).__name__}", action)
    parts = re.match(r"([0-9]+)\.([0-9]+)\.([0-9]+)", version)
    triple = tuple(int(p) for p in parts.groups()) if parts else None
    if triple is None or triple < SC_COMPOSE_FLOOR or triple[0] >= SC_COMPOSE_CEILING_MAJOR:
        return err("DEPENDENCY.SC_COMPOSE", f"the sc-compose wheel is {version}; this installer needs {SC_COMPOSE_SPEC}",
                   action, data={"version": version})
    return Ok(module)


# ---------------------------------------------------------------- rendering


def render_template(sc_compose: Any, template: Path, version: str) -> Result[str, ToolError]:
    """Strict sc-compose render of one install-time template with the package ``version``."""
    template = template.resolve()
    request = sc_compose.ComposeRequest(
        str(template.parent), sc_compose.ComposeMode.file(str(template)),
        vars_input={"version": version},
        policy=sc_compose.ComposePolicy(strict_undeclared_variables=True))
    try:
        text = sc_compose.compose_file(request).rendered_text
    except sc_compose.ScComposeError as exc:
        detail = str(exc.args[0]) if exc.args else str(exc)
        return err("RENDER.FAILED", f"sc-compose could not render {template.name}: {detail}",
                   "Fix the template; tests/sc-judge-jev/test_install.py renders every template.")
    if not text.endswith("\n"):
        text += "\n"
    return Ok(text)


class Renderer:
    """Renders and caches the installed bytes of one package and version."""

    def __init__(self, sc_compose: Any, package: Package, plugin_dir: Path = PLUGIN_DIR) -> None:
        self.sc_compose = sc_compose
        self.package = package
        self.plugin_dir = plugin_dir
        self.skill_src = plugin_dir / "install" / "templates" / "skills" / SKILL_NAME
        self.agents_src = plugin_dir / "install" / "templates" / "agents"
        self.harness = plugin_dir / "install" / "harness"
        self._cache: Dict[str, str] = {}

    def _render(self, template: Path) -> Result[str, ToolError]:
        key = str(template)
        if key not in self._cache:
            out = render_template(self.sc_compose, template, self.package.version)
            if isinstance(out, Err):
                return out
            self._cache[key] = out.value
        return Ok(self._cache[key])

    def skill_source(self, rel: str, target: str) -> Path:
        if rel == REGISTRY:
            return self.harness / target / REGISTRY
        return self.skill_src / (f"{rel}.j2" if rel in self.package.rendered else rel)

    def skill_file(self, rel: str, target: str) -> Result[bytes, ToolError]:
        src = self.skill_source(rel, target)
        if rel not in self.package.rendered:
            return Ok(src.read_bytes())
        out = self._render(src)
        return out if isinstance(out, Err) else Ok(out.value.encode("utf-8"))

    def agent_file(self, target: str, name: str) -> Result[bytes, ToolError]:
        front = (self.harness / target / "agents" / name).read_text(encoding="utf-8")
        out = self._render(self.agents_src / f"{name}.j2")
        return out if isinstance(out, Err) else Ok((front + out.value).encode("utf-8"))


# ---------------------------------------------------------------- lock file


@dataclass(frozen=True)
class Lock:
    version: str
    targets: Tuple[str, ...]
    files: Dict[str, str]


def read_lock(root: Path) -> Result[Optional[Lock], ToolError]:
    path = root.joinpath(*LOCK_RELPATH.split("/"))
    if not path.exists():
        return Ok(None)
    fix = f"Restore {LOCK_RELPATH} from git; if it is lost, delete it and rerun (files are then recognized by their bytes)."
    loaded = _read_json(path, "INSTALL.LOCK_INVALID")
    if isinstance(loaded, Err):
        return err("INSTALL.LOCK_INVALID", loaded.error.message, fix)
    d = loaded.value
    if (not isinstance(d, dict) or d.get("package") != PACKAGE or not isinstance(d.get("files"), dict)
            or not isinstance(d.get("targets"), list)
            or any(t not in TARGETS for t in d["targets"])
            or not all(isinstance(k, str) and isinstance(v, str) for k, v in d["files"].items())):
        return err("INSTALL.LOCK_INVALID", f"{LOCK_RELPATH} is not an {PACKAGE} install record", fix)
    return Ok(Lock(str(d.get("version")), tuple(d["targets"]), dict(d["files"])))


# ---------------------------------------------------------------- targets

# Why a harness is a target: "locked" (the lock records it), "installed" (its
# skills/judge-jev/ exists, locked or not), "present" (its .<target>/
# directory exists at the destination), "requested" (--target), "default"
# (none of these, so claude).
TargetReasons = Dict[str, List[str]]


def harness_present(root: Path, target: str) -> bool:
    return (root / f".{target}").is_dir()


def harness_installed(root: Path, target: str) -> bool:
    return (root / f".{target}" / "skills" / SKILL_NAME).exists()


def choose_targets(root: Path, lock: Optional[Lock], requested: List[str]) -> TargetReasons:
    """Every harness the destination uses, plus the requested ones; --target only adds."""
    reasons: TargetReasons = {}
    for target in TARGETS:
        why = [name for name, hit in (("locked", lock is not None and target in lock.targets),
                                      ("installed", harness_installed(root, target)),
                                      ("present", harness_present(root, target)),
                                      ("requested", target in requested)) if hit]
        if why:
            reasons[target] = why
    return reasons or {"claude": ["default"]}


def lock_text(version: str, targets: List[str], files: Dict[str, str]) -> str:
    body = {"package": PACKAGE, "version": version, "targets": targets,
            "files": dict(sorted(files.items()))}
    return json.dumps(body, indent=2) + "\n"


# ---------------------------------------------------------------- settings
#
# The installer reads and writes the settings file without importing the installed
# judge_jev_settings.py; test_install.py checks that the installed copy parses, and
# would write, exactly the file the installer writes.

SCHEMA_VERSION = 1
SETTINGS_RELPATH = ".sc/judge-jev/settings.yaml"
SETTINGS_KEYS = ("schema_version", "allow_remote_judge")
SETTINGS_HEADER = """\
# .sc/judge-jev/settings.yaml
# Repository settings for the sc-judge-jev plugin; commit this file, never put secrets in it.
schema_version: {schema_version}
"""
REMOTE_JUDGE_LINES = """\
# allow_remote_judge: may record text be sent to TypeSafe (Jev) for judging? Only the user decides it.
allow_remote_judge: {value}
"""


@dataclass(frozen=True)
class Settings:
    schema_version: int
    allow_remote_judge: Optional[bool] = None


def _load_yaml() -> Result[Any, ToolError]:
    try:
        return Ok(importlib.import_module("yaml"))
    except ImportError:
        return err("DEPENDENCY.PYYAML", f"PyYAML is required to read and write {SETTINGS_RELPATH} and is not installed",
                   f"Run with `uv run {Path(__file__).name}`, or install it: python3 -m pip install pyyaml")


def _strict_loader(yaml: Any) -> type:
    class StrictLoader(yaml.SafeLoader):  # type: ignore[name-defined, misc]
        def construct_mapping(self, node, deep=False):  # noqa: D401 - PyYAML hook
            seen = set()
            for key_node, _ in node.value:
                key = self.construct_object(key_node, deep=deep)
                try:
                    duplicate = key in seen
                except TypeError:
                    break  # unhashable key: PyYAML reports it below
                if duplicate:
                    raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
                seen.add(key)
            return super().construct_mapping(node, deep=deep)

    return StrictLoader


def parse_settings(text: str, yaml: Any) -> Result[Settings, ToolError]:
    path = SETTINGS_RELPATH
    fix = (f"Edit {path}: it must hold 'schema_version: {SCHEMA_VERSION}' and optionally "
           "'allow_remote_judge: true' or 'allow_remote_judge: false'.")
    try:
        data: Any = yaml.load(text, Loader=_strict_loader(yaml))  # a SafeLoader subclass
    except yaml.YAMLError as exc:
        return err("SETTINGS.MALFORMED", f"{path} is not valid YAML: {exc}", fix)
    if not isinstance(data, dict):
        return err("SETTINGS.MALFORMED", f"{path} must be a YAML mapping, got {type(data).__name__}", fix)
    unknown = sorted(str(k) for k in data if k not in SETTINGS_KEYS)
    if unknown:
        return err("SETTINGS.UNKNOWN_KEY", f"{path} has unknown key(s): {', '.join(unknown)}",
                   f"Remove them; supported keys are {', '.join(SETTINGS_KEYS)}.", data={"unknown_keys": unknown})
    version = data.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        return err("SETTINGS.SCHEMA_VERSION",
                   f"{path} schema_version is {version!r}; this plugin reads schema_version {SCHEMA_VERSION}",
                   fix, data={"schema_version": version if isinstance(version, (int, str)) else None})
    remote = data.get("allow_remote_judge")
    if "allow_remote_judge" in data and type(remote) is not bool:
        return err("SETTINGS.INVALID_REMOTE_JUDGE", f"{path} allow_remote_judge is {remote!r}; expected true or false", fix)
    return Ok(Settings(schema_version=version, allow_remote_judge=remote))


def settings_path(root: Path) -> Path:
    return root.joinpath(*SETTINGS_RELPATH.split("/"))


def read_settings(root: Path) -> Result[Optional[Settings], ToolError]:
    """The settings file exactly at ``root`` (no lookup): ``Ok(None)`` when it is absent."""
    yaml = _load_yaml()
    if isinstance(yaml, Err):
        return yaml
    path = settings_path(root)
    if not path.exists() and not path.is_symlink():
        return Ok(None)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return err("SETTINGS.UNREADABLE", f"{SETTINGS_RELPATH} could not be read: {type(exc).__name__}",
                   f"Make {SETTINGS_RELPATH} a readable UTF-8 file.")
    return parse_settings(text, yaml.value)


def render_settings(settings: Settings) -> str:
    """The committed form: header comment, purpose line, one key per line (absent keys are omitted)."""
    if settings.allow_remote_judge is not None and type(settings.allow_remote_judge) is not bool:
        raise ValueError(f"render_settings got allow_remote_judge {settings.allow_remote_judge!r}")  # caller bug
    text = SETTINGS_HEADER.format(schema_version=settings.schema_version)
    if settings.allow_remote_judge is not None:
        text += REMOTE_JUDGE_LINES.format(value="true" if settings.allow_remote_judge else "false")
    return text


def write_settings(root: Path, settings: Settings) -> Result[Path, ToolError]:
    """Write ``root``'s settings file atomically, then read it back through the strict parser."""
    yaml = _load_yaml()
    if isinstance(yaml, Err):
        return yaml
    path = settings_path(root)
    text = render_settings(settings)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".settings.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    except OSError as exc:
        return err("SETTINGS.WRITE_FAILED", f"could not write {SETTINGS_RELPATH}: {type(exc).__name__}: {exc}",
                   f"Check permissions on {path.parent}.")
    reread = parse_settings(text, yaml.value)
    if isinstance(reread, Err) or reread.value != settings:
        raise AssertionError("rendered settings do not round-trip")  # bug, not an expected failure
    return Ok(path)


def is_repository(root: Path) -> bool:
    return (root / ".git").exists()


def enclosing_repository(root: Path) -> Optional[Path]:
    """The repository ``root`` is, or sits inside: the nearest folder at or above it holding ``.git``
    (walking up and stopping before the home directory, as every lookup here does), or None."""
    for directory in _paths.ancestors(root):
        if is_repository(directory):
            return directory
    return None


# ---------------------------------------------------------------- plan


@dataclass
class Plan:
    root: Path
    version: str
    targets: List[str]
    target_reasons: TargetReasons = field(default_factory=dict)
    writes: Dict[str, Tuple[bytes, bool]] = field(default_factory=dict)  # key -> (bytes, executable)
    create: List[str] = field(default_factory=list)
    replace: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)
    remove: List[str] = field(default_factory=list)
    backup: List[str] = field(default_factory=list)
    problems: List[dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    lock_files: Dict[str, str] = field(default_factory=dict)
    remote_judge_change: Optional[dict] = None
    allow_remote_judge: Optional[bool] = None  # the value the settings file holds after the install


def _skill_prefix(target: str) -> str:
    return f".{target}/skills/{SKILL_NAME}/"


def _agents_prefix(target: str) -> str:
    return f".{target}/agents/"


def wanted_files(package: Package, renderer: Renderer, targets: List[str]) -> Result[Dict[str, Tuple[bytes, bool]], ToolError]:
    out: Dict[str, Tuple[bytes, bool]] = {}
    for target in targets:
        for rel in package.skill:
            data = renderer.skill_file(rel, target)
            if isinstance(data, Err):
                return data
            src = renderer.skill_source(rel, target)
            executable = bool(src.stat().st_mode & stat.S_IXUSR)  # a script template keeps its source's mode
            out[_skill_prefix(target) + rel] = (data.value, executable)
        for name in package.agents:
            data = renderer.agent_file(target, name)
            if isinstance(data, Err):
                return data
            out[_agents_prefix(target) + name] = (data.value, False)
    return Ok(out)


def known_bytes(key: str, package: Package, renderer: Renderer) -> Result[Set[str], ToolError]:
    """sha256 of every byte string this package (any version) shipped at ``key``."""
    shas: Set[str] = set()
    for target in TARGETS:
        if key.startswith(_skill_prefix(target)):
            rel = key[len(_skill_prefix(target)):]
            shas |= package.legacy_skill.get(rel, set())
            if rel in package.skill:
                data = renderer.skill_file(rel, target)
                if isinstance(data, Err):
                    return data
                shas.add(sha256(data.value))
        elif key.startswith(_agents_prefix(target)):
            name = key[len(_agents_prefix(target)):]
            shas |= package.legacy_agents[target].get(name, set())
            if name in package.agents:
                data = renderer.agent_file(target, name)
                if isinstance(data, Err):
                    return data
                shas.add(sha256(data.value))
    return Ok(shas)


def _legacy_keys(package: Package, target: str) -> List[str]:
    keys = [_skill_prefix(target) + rel for rel in package.legacy_skill]
    keys += [_agents_prefix(target) + name for name in package.legacy_agents[target]]
    return keys


def _problem(plan: Plan, code: str, key: str, message: str) -> None:
    plan.problems.append({"code": code, "path": key, "message": message})


def build_plan(root: Path, package: Package, renderer: Renderer, settings: Optional[Settings], lock: Optional[Lock],
               requested_targets: List[str], overwrite: bool) -> Result[Plan, ToolError]:
    """Everything the install would do. Reads the destination; writes nothing."""
    reasons = choose_targets(root, lock, requested_targets)
    targets = list(reasons)
    plan = Plan(root=root, version=package.version, targets=targets, target_reasons=reasons)
    wanted = wanted_files(package, renderer, targets)
    if isinstance(wanted, Err):
        return wanted
    wanted_map = wanted.value
    locked = dict(lock.files) if lock is not None else {}
    hint = " (or rerun with --overwrite to move it to .backup/)"

    def owned(key: str, data: bytes) -> Result[Optional[bool], ToolError]:
        """True owned and unmodified; None recorded but modified; False not ours."""
        digest = sha256(data)
        if key in locked:
            return Ok(True if locked[key] == digest else None)
        shas = known_bytes(key, package, renderer)
        return shas if isinstance(shas, Err) else Ok(digest in shas.value)

    foreign: Set[str] = set()
    for target in targets:
        skill_dir = root / f".{target}" / "skills" / SKILL_NAME
        if skill_dir.is_symlink() or (skill_dir.exists() and not skill_dir.is_dir()):
            _problem(plan, "SKILL.NOT_A_DIRECTORY", _skill_prefix(target).rstrip("/"),
                     f"{_skill_prefix(target).rstrip('/')} exists and is not a directory; move it aside and rerun")
            foreign.add(target)
            continue
        if not skill_dir.is_dir() or any(k.startswith(_skill_prefix(target)) for k in locked):
            continue
        files = [p for p in skill_dir.rglob("*") if p.is_file() and not IGNORED & set(p.relative_to(skill_dir).parts)]
        if not files:
            continue
        mine = False
        for path in files:
            state = owned(path.relative_to(root).as_posix(), path.read_bytes())
            if isinstance(state, Err):
                return state
            if state.value is not False:
                mine = True
                break
        if not mine:
            foreign.add(target)
            _problem(plan, "SKILL.FOREIGN_DIR", _skill_prefix(target).rstrip("/"),
                     f"{_skill_prefix(target).rstrip('/')} exists and holds no file {PACKAGE} shipped; "
                     "move it aside and rerun")

    for key, (data, executable) in sorted(wanted_map.items()):
        if any(key.startswith(_skill_prefix(t)) for t in foreign):
            continue
        path = root / key
        if path.is_symlink() or (path.exists() and not path.is_file()):
            _problem(plan, "FILE.NOT_REGULAR", key, f"{key} exists and is not a regular file; move it aside and rerun")
            continue
        if path.is_file():
            current = path.read_bytes()
            state = owned(key, current)
            if isinstance(state, Err):
                return state
            if state.value is not True:
                if overwrite:
                    plan.backup.append(key)
                elif state.value is None:
                    _problem(plan, "FILE.MODIFIED", key, f"{key} was modified since {PACKAGE} installed it{hint}")
                    continue
                else:
                    _problem(plan, "FILE.UNOWNED", key, f"{key} exists and is not {PACKAGE}'s{hint}")
                    continue
            if current == data and key not in plan.backup:
                plan.unchanged.append(key)
            else:
                plan.replace.append(key)
        else:
            plan.create.append(key)
        plan.writes[key] = (data, executable)
        plan.lock_files[key] = sha256(data)

    # Files an earlier install placed that this version no longer ships.
    handled: Set[str] = set(wanted_map)
    for key, recorded in sorted(locked.items()):
        if key in wanted_map:
            continue
        handled.add(key)
        path = root / key
        if not path.is_file() or path.is_symlink():
            continue
        if sha256(path.read_bytes()) == recorded:
            plan.remove.append(key)
        elif overwrite:
            plan.backup.append(key)
            plan.remove.append(key)
        else:
            _problem(plan, "FILE.MODIFIED_RETIRED", key,
                     f"{key} was modified since {PACKAGE} installed it, and this version no longer ships it{hint}")
    if lock is None:
        for target in targets:
            if target in foreign:
                continue
            for key in sorted(_legacy_keys(package, target)):
                if key in handled:
                    continue
                handled.add(key)
                path = root / key
                if not path.is_file() or path.is_symlink():
                    continue
                state = owned(key, path.read_bytes())
                if isinstance(state, Err):
                    return state
                if state.value:
                    plan.remove.append(key)
                elif overwrite:
                    plan.backup.append(key)
                    plan.remove.append(key)
                else:
                    plan.warnings.append(f"{key}: an earlier {PACKAGE} version shipped this path, but these bytes are "
                                         "not one it shipped; left in place (move it aside, or rerun with --overwrite)")
    for target in targets:
        skill_dir = root / f".{target}" / "skills" / SKILL_NAME
        if target in foreign or not skill_dir.is_dir():
            continue
        for path in sorted(skill_dir.rglob("*")):
            key = path.relative_to(root).as_posix()
            if path.is_file() and key not in handled and not IGNORED & set(path.relative_to(skill_dir).parts):
                plan.warnings.append(f"{key}: not a {PACKAGE} file; left in place")

    plan.allow_remote_judge = settings.allow_remote_judge if settings is not None else None
    plan.backup = sorted(set(plan.backup))
    plan.remove = sorted(set(plan.remove))
    return Ok(plan)


# ---------------------------------------------------------------- apply


def _prune(root: Path, start: Path, stop: Path) -> None:
    """Remove now-empty directories (ignoring __pycache__ residue) from ``start`` up to ``stop``."""
    current = start
    while current != stop and stop in current.parents and current.is_dir():
        entries = list(current.iterdir())
        if any(e.name not in IGNORED or (e.is_file() and e.name != ".DS_Store") for e in entries):
            if not all(e.is_dir() and e.name == "__pycache__" or e.name == ".DS_Store" for e in entries):
                return
        for e in entries:
            if e.is_dir():
                shutil.rmtree(e)
            else:
                e.unlink()
        current.rmdir()
        current = current.parent


def apply_plan(plan: Plan) -> Result[List[str], ToolError]:
    """Write the plan. Returns the paths to commit."""
    root = plan.root
    try:
        if plan.backup:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            base = root / BACKUP_DIR / stamp
            for key in plan.backup:
                (base / key).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(root / key), str(base / key))
            ignore = root / BACKUP_DIR / ".gitignore"
            if not ignore.exists():
                ignore.write_text("*\n", encoding="utf-8")
        for key, (data, executable) in sorted(plan.writes.items()):
            path = root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file() or path.read_bytes() != data:
                path.write_bytes(data)
            if executable and os.name != "nt":
                path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        for key in plan.remove:
            path = root / key
            if path.is_file():
                path.unlink()
            target_root = root / key.split("/", 1)[0]
            _prune(root, path.parent, target_root)
        lock_path = root.joinpath(*LOCK_RELPATH.split("/"))
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = lock_path.with_name(lock_path.name + ".tmp")
        tmp.write_text(lock_text(plan.version, plan.targets, plan.lock_files), encoding="utf-8")
        os.replace(tmp, lock_path)
    except OSError as exc:
        return err("INSTALL.WRITE_FAILED", f"writing the install failed: {type(exc).__name__}: {exc}",
                   "Fix the reported path (permissions, disk space), then rerun; the lock file is written last.")
    if plan.remote_judge_change is not None:
        saved = write_settings(root, Settings(schema_version=SCHEMA_VERSION, allow_remote_judge=plan.allow_remote_judge))
        if isinstance(saved, Err):
            return saved
    changed = plan.create + plan.replace + plan.remove
    commit = sorted({k.split("/")[0] + "/" for k in changed})
    if changed or plan.backup:
        commit.append(LOCK_RELPATH)
    if plan.remote_judge_change is not None:
        commit.append(SETTINGS_RELPATH)
    return Ok(commit)


# ---------------------------------------------------------------- orchestration


@dataclass(frozen=True)
class Options:
    dest: Path
    targets: List[str]  # --target: added to the harnesses the folder uses; may be empty
    overwrite: bool = False
    dry_run: bool = False
    allow_remote_judge: Optional[bool] = None  # None: keep what the settings file holds


def check_dest(dest: Path, plugin_dir: Path = PLUGIN_DIR) -> Result[Path, ToolError]:
    """The destination folder, resolved; a global harness location or the plugin itself is refused."""
    try:
        dest = dest.expanduser()
    except (KeyError, RuntimeError):  # "~" with no determinable home directory
        return err("INSTALL.DEST", f"--dest {str(dest)!r} starts with '~' but the home directory cannot be determined",
                   "Pass the folder as an absolute path.")
    if not dest.is_dir():
        return err("INSTALL.DEST", f"--dest {str(dest)!r} is not a directory",
                   "Pass an existing folder: a repository, or a parent folder holding repositories.")
    root = dest.resolve()
    why = global_location(root)
    plugin = plugin_dir.resolve()
    if why is None and (root == plugin or plugin in root.parents):
        why = f"{root} is inside the plugin directory {plugin}"
    if why is not None:
        return err("INSTALL.DEST_GLOBAL", f"--dest refused: {why}",
                   "judge-jev installs per folder, never globally: pass a repository or a parent folder of "
                   "repositories (not the home directory, ~/.claude, ~/.codex, ~/.cursor, ~/.agents or a plugin cache).",
                   data={"dest": str(root)})
    return Ok(root)


def status(dest: Path, plugin_dir: Path = PLUGIN_DIR) -> Result[dict, ToolError]:
    """Read-only: the installer's version against the destination's lock (or the nearest lock above it)."""
    root = check_dest(dest, plugin_dir)
    if isinstance(root, Err):
        return root
    plugin = _read_json(plugin_dir / "plugin.json", "INSTALL.PACKAGE_INVALID")
    if isinstance(plugin, Err):
        return plugin
    mine = plugin.value.get("version") if isinstance(plugin.value, dict) else None
    lock = read_lock(root.value)
    if isinstance(lock, Err):
        return lock
    covering = None
    if lock.value is None:
        above = find_lock(root.value.parent) if root.value.parent != root.value else None
        if above is not None:
            parent_root = above.parent.parent.parent
            found = read_lock(parent_root)
            covering = {"root": str(parent_root), "version": found.value.version if isinstance(found, Ok) and found.value else None,
                        "valid": isinstance(found, Ok)}
    installed = lock.value.version if lock.value is not None else None
    missing = [t for t in TARGETS if harness_present(root.value, t) and not harness_installed(root.value, t)]
    have, want = version_tuple(installed), version_tuple(mine)
    if installed is None:
        state, message = "not_installed", f"not installed in {root.value}, installer {mine}"
        if covering is not None:
            message += f" (an install at {covering['root']} covers it: {covering['version']})"
    elif have is None or want is None or have < want:
        state, message = "older", f"installed {installed}, installer {mine}"
    elif have == want:
        state, message = "current", f"installed {installed}, installer {mine}"
    else:
        state, message = "newer", f"installed {installed} is newer than installer {mine}"
    if missing:
        message += ("; no judge-jev in " + ", ".join(f".{t}/" for t in missing)
                    + " (rerun the installer without --target to install every harness)")
    return Ok({
        "package": PACKAGE,
        "dest": str(root.value),
        "installer_version": mine,
        "installed_version": installed,
        "installed_targets": list(lock.value.targets) if lock.value is not None else [],
        "missing_targets": missing,
        "covering_install": covering,
        "state": state,
        "message": message,
    })


def install(opts: Options, *, plugin_dir: Path = PLUGIN_DIR) -> Result[dict, ToolError]:
    checked = check_dest(opts.dest, plugin_dir)
    if isinstance(checked, Err):
        return checked
    root = Ok(checked.value)
    package = load_package(plugin_dir)
    if isinstance(package, Err):
        return package
    settings = read_settings(root.value)  # the destination's own file: the one this install writes
    if isinstance(settings, Err):
        return settings
    lock = read_lock(root.value)
    if isinstance(lock, Err):
        return lock
    sc_compose = check_sc_compose()
    if isinstance(sc_compose, Err):
        return sc_compose
    renderer = Renderer(sc_compose.value, package.value, plugin_dir)
    planned = build_plan(root.value, package.value, renderer, settings.value, lock.value, opts.targets, opts.overwrite)
    if isinstance(planned, Err):
        return planned
    plan = planned.value
    if opts.allow_remote_judge is not None and opts.allow_remote_judge != plan.allow_remote_judge:
        plan.remote_judge_change = {"path": SETTINGS_RELPATH, "from": plan.allow_remote_judge, "to": opts.allow_remote_judge}
        plan.allow_remote_judge = opts.allow_remote_judge
    if plan.problems:
        return err("INSTALL.CONFLICT",
                   f"{len(plan.problems)} file(s) are in the way; nothing was written: "
                   + "; ".join(p["message"] for p in plan.problems),
                   "Restore or move each listed file and rerun, or rerun with --overwrite to move them to .backup/.",
                   data={"problems": plan.problems})
    repository = enclosing_repository(root.value)
    notes = []
    if plan.allow_remote_judge is None:
        notes.append(f"{SETTINGS_RELPATH} does not set allow_remote_judge, so live Jev calls are refused. Ask the user "
                     "once whether record text may be sent to TypeSafe (Jev), then rerun with --allow-remote-judge or "
                     "--no-remote-judge (or run 'judge_jev_settings.py set allow_remote_judge true|false') and commit it.")
    if repository is None:
        notes.append(f"{root.value} is not a repository: repositories below it inherit this install and its "
                     f"{SETTINGS_RELPATH} (the nearest settings file wins, so a repository can override it with its own).")
    data: Dict[str, Any] = {
        "package": PACKAGE,
        "version": plan.version,
        "previous_version": lock.value.version if lock.value is not None else None,
        "install_root": str(root.value),
        "repository": is_repository(root.value),
        "repository_root": str(repository) if repository else None,
        "allow_remote_judge": plan.allow_remote_judge,
        "targets": plan.targets,
        "target_reasons": plan.target_reasons,
        "dry_run": opts.dry_run,
        "migration": lock.value is None,
        "plan": {
            "create": plan.create,
            "replace": plan.replace,
            "unchanged": plan.unchanged,
            "remove": plan.remove,
            "backup": plan.backup,
            "allow_remote_judge": plan.remote_judge_change,
            "lock": LOCK_RELPATH,
        },
        "warnings": plan.warnings,
        "notes": notes,
    }
    if opts.dry_run:
        data["commit_paths"] = []
        return Ok(data)
    applied = apply_plan(plan)
    if isinstance(applied, Err):
        return applied
    data["commit_paths"] = applied.value
    return Ok(data)


# ---------------------------------------------------------------- CLI


class _UsageError(Exception):
    pass


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):  # argparse hook; never returns
        raise _UsageError(f"{self.prog}: {message}")


def _targets(value: str) -> List[str]:
    out = []
    for part in value.split(","):
        name = part.strip().lstrip(".")
        if name not in TARGETS:
            raise argparse.ArgumentTypeError(f"unknown target {part.strip()!r}; choose from {', '.join(TARGETS)}")
        out.append(name)
    return out


def _parser() -> argparse.ArgumentParser:
    p = _JsonArgumentParser(prog="install.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dest", required=True,
                   help="the folder to install into: a repository, or a parent folder holding repositories")
    p.add_argument("--status", action="store_true",
                   help="read-only: compare this installer's version with the destination's install lock")
    p.add_argument("--target", type=_targets, action="append", default=None, metavar="claude,codex,cursor",
                   help="harness directories to add (repeatable or comma-separated); every harness the folder "
                        "uses is always included: locked, installed or present (default claude when none)")
    p.add_argument("--overwrite", action="store_true",
                   help=f"move modified or foreign files in the way to {BACKUP_DIR}/<UTC>/ and install over them")
    p.add_argument("--dry-run", action="store_true", help="print the plan and write nothing")
    remote = p.add_mutually_exclusive_group()
    remote.add_argument("--allow-remote-judge", dest="allow_remote_judge", action="store_const", const=True, default=None,
                        help="record allow_remote_judge: true (the user agreed record text may be sent to TypeSafe)")
    remote.add_argument("--no-remote-judge", dest="allow_remote_judge", action="store_const", const=False,
                        help="record allow_remote_judge: false (live Jev calls stay refused)")
    return p


def _envelope(result: Result[Any, ToolError]) -> Tuple[dict, int]:
    if isinstance(result, Ok):
        return {"success": True, "data": result.value, "error": None}, 0
    e = result.error
    return {"success": False, "data": dict(e.data) if e.data is not None else None, "error": e.to_json()}, ERROR_EXIT


def main(argv: Optional[List[str]] = None, *, plugin_dir: Path = PLUGIN_DIR) -> int:
    try:
        args = _parser().parse_args(argv)
        targets = [t for group in (args.target or []) for t in group]
        opts = Options(dest=Path(args.dest), targets=list(dict.fromkeys(targets)),
                       overwrite=args.overwrite, dry_run=args.dry_run,
                       allow_remote_judge=args.allow_remote_judge)
        if args.status and (args.target or args.overwrite or args.dry_run
                            or args.allow_remote_judge is not None):
            raise _UsageError("install.py: --status takes only --dest")
    except _UsageError as exc:
        envelope = {"success": False, "data": None,
                    "error": ToolError("VALIDATION.INPUT", str(exc), "Run 'install.py --help'.").to_json()}
        print(json.dumps(envelope, indent=2, sort_keys=True))
        return ERROR_EXIT
    try:
        if args.status:
            envelope, code = _envelope(status(opts.dest, plugin_dir))
        else:
            envelope, code = _envelope(install(opts, plugin_dir=plugin_dir))
    except Exception as exc:  # a bug, not an expected failure
        envelope = {"success": False, "data": None, "error": ToolError(
            "SCRIPT.INTERNAL", f"{type(exc).__name__}: {exc}", "Report this with the command line.").to_json()}
        code = ERROR_EXIT
    print(json.dumps(envelope, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(_result.run_main(main))  # UTF-8 streams; an interrupt is the CANCELED envelope and exit 130
