#!/usr/bin/env python3
"""Version discipline for the sc-judge-jev plugin: VERSION is the single source of truth.

Consistency:
  VERSION holds X.Y.Z. Every version declared in shipped metadata equals it
  exactly: plugin manifests, marketplace manifests, the installer skill's
  SKILL.md, every harness agent header and registry.yaml entry under
  install/harness/, and any other `version:` in a shipped .md frontmatter,
  .yaml/.yml or .json manifest. The installed skill and references take their
  version from plugin.json when install.py renders them, so every install-time
  template must declare `{{ version }}` instead of a literal.
  Files are discovered by globbing (see version_declarations), so a new agent
  or reference cannot escape. CHANGELOG.md has a "## Unreleased" section or a
  "## X.Y.Z" entry. Registry
  paths, manifest identities and marketplace sources are checked too, and the
  plugin must expose only the judge-jev-installer skill.

There is no pull-request bump rule: nothing is published, VERSION stays 0.1.0, and
no PR raises it. Changes accumulate under "## Unreleased" in CHANGELOG.md.

Every other version number is locked too, with no exclusions: each template's
own header `version:` (every *.j2) equals VERSION, and every integer version
(a question set's or tree's `version` / `jj:version`, every `schema_version`)
equals 1 until the first publish.

Exit 0 in sync; 2 when the check fails: drift (each on its own line on stdout)
or missing files and bad input (on stderr): a manifest that is not valid JSON,
a file that cannot be read. A check script's job is to fail
CI, so drift is nonzero; like every judge-jev CLI it never exits 1.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "sc-judge-jev"
INSTALLER_SKILL = "judge-jev-installer"
SKILL_NAME = "judge-jev"
HARNESS = PLUGIN / "install" / "harness"
TEMPLATES = PLUGIN / "install" / "templates"
HARNESSES = ("claude", "codex", "cursor")
AGENT_DIRS = {h: HARNESS / h / "agents" for h in HARNESSES}
FRONT_RE = re.compile(r"^---\n(.*?)\n---", re.S)
VER_RE = re.compile(r'^\s*version:\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)["\']?\s*$', re.M)
SEMVER_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")

# Every file matching these must declare a version.
REQUIRED_GLOBS = (
    "plugins/*/plugin.json",
    "plugins/*/.claude-plugin/plugin.json",
    "plugins/*/.codex-plugin/plugin.json",
    "plugins/*/.cursor-plugin/plugin.json",
    "plugins/*/skills/*/SKILL.md",
    "plugins/*/install/harness/claude/registry.yaml",
    "plugins/*/install/harness/codex/registry.yaml",
    "plugins/*/install/harness/cursor/registry.yaml",
)
# Every file matching these must declare a version; the package may ship none (no agents yet).
OPTIONAL_GLOBS = (
    "plugins/*/install/harness/claude/agents/*.md",
    "plugins/*/install/harness/codex/agents/*.md",
    "plugins/*/install/harness/cursor/agents/*.md",
)
# Any version these declare must equal VERSION (catch-all for new metadata).
SCANNED_GLOBS = (
    "plugins/**/*.md",
    "plugins/**/*.json",
    "plugins/**/*.yaml",
    "plugins/**/*.yml",
    ".claude-plugin/*.json",
    ".agents/plugins/*.json",
    ".cursor-plugin/*.json",
)


def _rel(path: pathlib.Path) -> str:
    """``path`` relative to the repository in POSIX form, so a message reads the same on every OS."""
    return path.relative_to(ROOT).as_posix()


def _declared(path: pathlib.Path) -> list:
    """Semver versions a metadata file declares (frontmatter, YAML, or JSON manifest keys)."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        m = FRONT_RE.match(text)
        return VER_RE.findall(m.group(1)) if m else []
    if path.suffix in (".yaml", ".yml"):
        return VER_RE.findall(text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return ["<invalid JSON>"]
    if not isinstance(data, dict):
        return []
    values = [data.get("version")] + [p.get("version") for p in data.get("plugins", []) if isinstance(p, dict)]
    return [v for v in values if isinstance(v, str) and SEMVER_RE.fullmatch(v)]


def version_declarations(root: pathlib.Path) -> list:
    """[(relative path, [versions])] for every shipped metadata file; [] means a required file declares none."""
    found = {}
    for pattern in SCANNED_GLOBS:
        for f in root.glob(pattern):
            if f.is_file():
                versions = _declared(f)
                if versions:
                    found[f.relative_to(root).as_posix()] = versions
    for pattern in REQUIRED_GLOBS + OPTIONAL_GLOBS:
        for f in root.glob(pattern):
            found.setdefault(f.relative_to(root).as_posix(), _declared(f))
    return sorted(found.items())


def template_drift(root: pathlib.Path) -> list:
    """Install-time templates whose rendered frontmatter pins a literal version instead of {{ version }}."""
    drift = []
    for template in sorted((root / "plugins" / "sc-judge-jev" / "install" / "templates").rglob("*.j2")):
        text = template.read_text(encoding="utf-8")
        lines = text.split("\n", 2)
        if len(lines) < 2 or not lines[1].startswith("name: sc-judge-jev-"):
            continue  # a runtime template, copied verbatim
        body = text.split("\n---\n", 1)[1] if "\n---\n" in text else ""
        inner = FRONT_RE.match(body)
        if inner and VER_RE.search(inner.group(1)):
            drift.append(f"{template.relative_to(root).as_posix()}: rendered version must be {{{{ version }}}}, not a literal")
    return drift


INT_VERSION_RES = (
    re.compile(r'"(?:schema_)?version":\s*([0-9]+)\s*[,}]'),
    re.compile(r"^\s*schema_version:\s*([0-9]+)\s*$", re.M),
    re.compile(r"\bjj:version\s+([0-9]+)\b"),
)
LOCKED_INT_VERSION = "1"


def locked_drift(root: pathlib.Path, want: str) -> list:
    """Template header versions that are not VERSION, and integer versions that are not 1."""
    drift = []
    for template in sorted(root.glob("plugins/**/*.j2")):
        head = FRONT_RE.match(template.read_text(encoding="utf-8"))
        for v in VER_RE.findall(head.group(1)) if head else []:
            if v != want:
                drift.append(f"{_rel(template)}: template version {v} != VERSION {want}")
    for f in sorted(root.glob("plugins/**/*")):
        if not f.is_file() or f.suffix not in (".json", ".ttl", ".yaml", ".yml", ".j2"):
            continue
        text = f.read_text(encoding="utf-8")
        for pattern in INT_VERSION_RES:
            for v in pattern.findall(text):
                if v != LOCKED_INT_VERSION:
                    drift.append(f"{_rel(f)}: integer version {v} != {LOCKED_INT_VERSION} (locked until the first publish)")
    return drift


def ssot_drift(root: pathlib.Path, want: str) -> list:
    """Every version declaration that does not equal VERSION, plus a missing CHANGELOG section."""
    drift = []
    for pattern in REQUIRED_GLOBS:
        if not any(root.glob(pattern)):
            drift.append(f"{pattern}: no file matches (layout changed?)")
    for rel, versions in version_declarations(root):
        if not versions:
            drift.append(f"{rel}: declares no version (must be {want})")
        for v in versions:
            if v != want:
                drift.append(f"{rel}: {v} != VERSION {want}")
    drift.extend(template_drift(root))
    drift.extend(locked_drift(root, want))
    changelog = root / "CHANGELOG.md"
    if not changelog.exists() or not re.search(rf"^## (Unreleased\b|{re.escape(want)}\b)", changelog.read_text(encoding="utf-8"), re.M):
        drift.append(f"CHANGELOG.md has neither a '## Unreleased' section nor a '## {want}' entry")
    return drift


def registry_source(harness: str, path: str):
    """The plugin source of an installed path a registry names (relative to the install root), or None."""
    prefix = f".{harness}/"
    if not path.startswith(prefix):
        return None
    rel = path[len(prefix):]
    if rel.startswith("agents/") and rel.count("/") == 1:
        return AGENT_DIRS[harness] / rel.split("/", 1)[1]
    if rel.startswith("skills/judge-jev/"):
        source = TEMPLATES / rel
        return source if source.exists() else source.with_name(source.name + ".j2")
    return None


class CheckError(Exception):
    """The check could not run (bad input, an unreadable or malformed file): main prints it and exits 2."""


def load_manifest(path: pathlib.Path) -> dict:
    """A JSON manifest or catalog as an object; CheckError when it cannot be read or is not a JSON object."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"{_rel(path)} could not be read: {type(exc).__name__}: {exc}") from None
    except json.JSONDecodeError as exc:
        raise CheckError(f"{_rel(path)} is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise CheckError(f"{_rel(path)} must be a JSON object, got {type(data).__name__}")
    return data


def release_checks(want: str, drift: list) -> int:
    declarations = version_declarations(ROOT)
    drift.extend(ssot_drift(ROOT, want))
    expected_agents = {f.stem for f in AGENT_DIRS["claude"].glob("*.md")}
    for harness, agent_dir in AGENT_DIRS.items():
        actual_agents = {f.stem for f in agent_dir.glob("*.md")}
        if actual_agents != expected_agents:
            drift.append(f"{_rel(agent_dir)}: agent files {sorted(actual_agents)} != {sorted(expected_agents)}")
        reg = HARNESS / harness / "registry.yaml"
        if not reg.exists():
            drift.append(f"{_rel(reg)}: missing")
            continue
        text = reg.read_text(encoding="utf-8")
        registered = set()
        for m in re.finditer(r"^  ([a-z0-9-]+):\n    version:\s*([0-9.]+)\n    path:\s*(\S+)", text, re.M):
            name, _, path = m.groups()
            if name != SKILL_NAME:
                registered.add(name)
            source = registry_source(harness, path)
            if source is None or not source.exists():
                drift.append(f"{_rel(reg)} {name}: path {path} is not an installed .{harness}/ path "
                             "this plugin ships")
        if registered != expected_agents:
            drift.append(f"{_rel(reg)}: agents {sorted(registered)} != {sorted(expected_agents)}")
    plugin_manifests = [
        PLUGIN / "plugin.json",
        PLUGIN / ".claude-plugin" / "plugin.json",
        PLUGIN / ".codex-plugin" / "plugin.json",
        PLUGIN / ".cursor-plugin" / "plugin.json",
    ]
    for manifest in plugin_manifests:
        if not manifest.exists():
            drift.append(f"{_rel(manifest)}: missing")
            continue
        data = load_manifest(manifest)
        if data.get("name") != "sc-judge-jev":
            drift.append(f"{_rel(manifest)}: name must be sc-judge-jev")
    for manifest in plugin_manifests[1:]:
        data = load_manifest(manifest) if manifest.exists() else {}
        if "agents" in data:
            drift.append(f"{_rel(manifest)}: must not register agents (they are installed per folder)")
        if data and data.get("skills") != "./skills/":
            drift.append(f"{_rel(manifest)}: skills must be ./skills/")
    exposed = sorted(p.name for p in (PLUGIN / "skills").iterdir() if p.is_dir()) if (PLUGIN / "skills").is_dir() else []
    if exposed != [INSTALLER_SKILL]:
        drift.append(f"plugins/sc-judge-jev/skills: exposes {exposed}; must be exactly [{INSTALLER_SKILL!r}]")
    catalogs = [
        ROOT / ".claude-plugin" / "marketplace.json",
        ROOT / ".agents" / "plugins" / "marketplace.json",
        ROOT / ".cursor-plugin" / "marketplace.json",
    ]
    for catalog in catalogs:
        if not catalog.exists():
            drift.append(f"{_rel(catalog)}: missing")
            continue
        data = load_manifest(catalog)
        plugins = data.get("plugins", [])
        entries = [p for p in plugins if isinstance(p, dict) and p.get("name") == "sc-judge-jev"] if isinstance(plugins, list) else []
        if len(entries) != 1:
            drift.append(f"{_rel(catalog)}: expected one sc-judge-jev entry")
            continue
        source = entries[0].get("source")
        source_path = source.get("path") if isinstance(source, dict) else source
        if source_path != "./plugins/sc-judge-jev":
            drift.append(f"{_rel(catalog)}: source must be ./plugins/sc-judge-jev")
        elif not (ROOT / source_path[2:]).is_dir():
            drift.append(f"{_rel(catalog)}: source path does not exist")
    return sum(len(v) or 1 for _, v in declarations)


def main() -> int:
    if len(sys.argv) > 1:
        print(__doc__)
        return 0 if sys.argv[1] in ("-h", "--help") else 2
    vfile = ROOT / "VERSION"
    if not vfile.exists():
        print("check-version-sync: VERSION file missing", file=sys.stderr)
        return 2
    want = vfile.read_text().strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", want):
        print(f"check-version-sync: VERSION is not X.Y.Z: {want!r}", file=sys.stderr)
        return 2
    drift: list = []
    try:
        checked = release_checks(want, drift)
        mode = "consistency"
    except CheckError as exc:
        print(f"check-version-sync: {exc}", file=sys.stderr)
        return 2
    if drift:
        print(f"check-version-sync [{mode}]: {len(drift)} drift(s) from VERSION {want}:")
        for d in drift:
            print(f"  {d}")
        return 2
    print(f"check-version-sync [{mode}]: {checked} version declarations equal {want}, CHANGELOG section present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
