"""plugins/sc-judge-jev/install.py: rendering, destinations, ownership, upgrades, envelope.

Tests that render need the sc-compose wheel (CPython 3.11 wheels on PyPI) and
PyYAML; without them they skip with the reason. CI's installer job sets
JUDGE_JEV_REQUIRE_SC_COMPOSE=1, which turns those skips into failures.
"""

import contextlib
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "sc-judge-jev"
TEMPLATES = PLUGIN / "install" / "templates"
SKILL_SRC = TEMPLATES / "skills" / "judge-jev"
INSTALLER = PLUGIN / "install.py"
GENERATOR = ROOT / "scripts" / "gen_install_data.py"
VERSION = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))["version"]
REQUIRE = os.environ.get("JUDGE_JEV_REQUIRE_SC_COMPOSE") == "1"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


inst = _load("sc_judge_jev_install", INSTALLER)
gen = _load("gen_install_data", GENERATOR)


def _missing_deps():
    missing = []
    for module in ("yaml", "sc_compose"):
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(module)
    if "sc_compose" not in missing and isinstance(inst.check_sc_compose(), inst.Err):
        missing.append("sc_compose (version outside >=1.7.0,<2)")
    return missing


MISSING = _missing_deps()
SKIP_REASON = (f"needs {', '.join(MISSING)}: pip install pyyaml 'sc-compose>=1.7.0,<2' "
               "(sc-compose publishes CPython 3.11 wheels); CI's installer job runs these")


def needs_wheel(cls):
    if MISSING and REQUIRE:
        raise RuntimeError(f"JUDGE_JEV_REQUIRE_SC_COMPOSE=1 but {SKIP_REASON}")
    return unittest.skipIf(bool(MISSING), SKIP_REASON)(cls)


def _has_commit(rev):
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
                          capture_output=True).returncode == 0


def sha(data):
    return hashlib.sha256(data).hexdigest()


class TempRepo:
    """A git repository."""

    def __init__(self, test):
        self.dir = tempfile.TemporaryDirectory()
        test.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def path(self, rel):
        return self.root / rel

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file() and ".git" not in p.relative_to(self.root).parts}


def run_install(repo, targets=("claude",), plugin_dir=PLUGIN, **kw):
    opts = inst.Options(dest=repo.root, targets=list(targets), **kw)
    return inst.install(opts, plugin_dir=plugin_dir)


AGENT_NAME = "demo-agent.md"
AGENT_BODY = ("---\nname: sc-judge-jev-demo-agent\nversion: 1.0.0\nformat: markdown\n"
              "description: test fixture\nrequired_variables:\n  - version\n---\n# demo agent {{ version }}\n")


def plugin_with_agent(dest):
    """A copy of the plugin that ships one agent: install.py supports agents; this package ships none yet."""
    shutil.copytree(PLUGIN, dest, ignore=shutil.ignore_patterns("__pycache__"))
    agents = dest / "install" / "templates" / "agents"
    agents.mkdir()
    (agents / f"{AGENT_NAME}.j2").write_text(AGENT_BODY, encoding="utf-8")
    for target in inst.TARGETS:
        front = dest / "install" / "harness" / target / "agents" / AGENT_NAME
        front.parent.mkdir(parents=True)
        front.write_text(f"---\nname: demo-agent\nversion: {VERSION}\n---\n", encoding="utf-8")
    return dest


# ---------------------------------------------------------------- rendering


@needs_wheel
class RenderingTests(unittest.TestCase):
    def setUp(self):
        import sc_compose
        self.sc = sc_compose
        package = inst.load_package()
        self.assertIsInstance(package, inst.Ok, getattr(package, "error", None))
        self.package = package.value
        self.renderer = inst.Renderer(sc_compose, self.package)

    def render(self, template):
        out = inst.render_template(self.sc, template, VERSION)
        self.assertIsInstance(out, inst.Ok, getattr(out, "error", None))
        return out.value

    def test_plugin_ships_only_the_installer_skill_and_no_rendered_tree(self):
        self.assertEqual(sorted(p.name for p in (PLUGIN / "skills").iterdir()), ["judge-jev-installer"])
        for gone in (".claude", ".codex", ".cursor", "skills/judge-jev", "install/manifest.json"):
            self.assertFalse((PLUGIN / gone).exists(), gone)

    def test_every_prompt_source_is_a_template(self):
        """Every .md and .py the skill installs is rendered; none is copied verbatim."""
        copied = [rel for rel in self.package.skill if rel.endswith((".md", ".py")) and rel not in self.package.rendered]
        self.assertEqual(copied, [])
        expected = {"SKILL.md"}
        expected |= {f"references/{p.name[:-len('.j2')]}" for p in (SKILL_SRC / "references").iterdir()}
        expected |= {f"scripts/{p.name[:-len('.j2')]}" for p in (SKILL_SRC / "scripts").iterdir()
                     if p.name.endswith(".j2")}
        self.assertTrue({"scripts/result.py", "scripts/judge_jev_paths.py", "scripts/judge_jev_settings.py"} <= expected)
        self.assertEqual(set(self.package.rendered), expected)
        self.assertEqual(self.package.agents, ())

    def test_every_template_renders_strictly(self):
        templates = [t for t in sorted(TEMPLATES.rglob("*.j2")) if inst.is_install_template(t)]
        self.assertGreaterEqual(len(templates), 5)  # SKILL.md, the guide, three scripts
        for template in templates:
            with self.subTest(template=template.name):
                rendered = self.render(template)
                self.assertNotIn("{{", rendered)

    def test_installer_imports_the_plain_scripts_exactly_as_installed(self):
        """install.py loads result.py and judge_jev_paths.py from their templates' bodies: the same bytes it installs."""
        for name in ("result", "judge_jev_paths"):
            template = SKILL_SRC / "scripts" / f"{name}.py.j2"
            body = inst.template_body(template.read_text(encoding="utf-8"))
            for token in inst.TEMPLATE_SYNTAX:
                self.assertNotIn(token, body)
            with self.subTest(script=name):
                self.assertEqual(self.render(template), body)

    def test_cli_render_matches_the_wheel(self):
        """The script tests fall back to the sc-compose CLI where the wheel is missing; both render the same bytes."""
        from layout_support import render_cli
        if shutil.which("sc-compose") is None:
            self.skipTest("the sc-compose CLI is not on PATH (scripts/install_sc_compose_ci.py installs it)")
        templates = [t for t in sorted(TEMPLATES.rglob("*.j2")) if inst.is_install_template(t)]
        with tempfile.TemporaryDirectory() as tmp:
            for template in templates:
                with self.subTest(template=template.name):
                    out = Path(tmp) / template.name[:-len(".j2")]
                    render_cli(template, out)
                    self.assertEqual(out.read_text(encoding="utf-8"), self.render(template))

    def test_installer_settings_match_the_installed_settings_script(self):
        """install.py writes and reads settings with its own copy; the installed script agrees."""
        import yaml
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("result", "judge_jev_paths", "judge_jev_settings"):
                source = SKILL_SRC / "scripts" / f"{name}.py.j2"
                (Path(tmp) / f"{name}.py").write_text(self.render(source), encoding="utf-8")
            code = ("import json, sys\n"
                    f"sys.path.insert(0, {tmp!r})\n"
                    "import yaml, judge_jev_settings as s\n"
                    "out = {}\n"
                    "for remote in (None, True, False):\n"
                    "    out[str(remote)] = s.render_settings(s.Settings(1, remote))\n"
                    "print(json.dumps(out))\n")
            proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            installed = json.loads(proc.stdout)
        for remote in (None, True, False):
            with self.subTest(remote=remote):
                text = inst.render_settings(inst.Settings(1, remote))
                self.assertEqual(installed[str(remote)], text)
                self.assertEqual(inst.parse_settings(text, yaml).value.allow_remote_judge, remote)

    def test_strict_rendering_refuses_an_undeclared_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.md.j2"
            bad.write_text("---\nname: bad\nversion: 1.0.0\nformat: markdown\nrequired_variables:\n  - version\n---\n"
                           "{{ version }} {{ tracker }}\n", encoding="utf-8")
            out = inst.render_template(self.sc, bad, VERSION)
            self.assertIsInstance(out, inst.Err)
            self.assertEqual(out.error.code, "RENDER.FAILED")


# ---------------------------------------------------------------- generated data


class GeneratedDataTests(unittest.TestCase):
    def setUp(self):
        if not _has_commit(gen.BASE):
            self.skipTest(f"history commit {gen.BASE} absent (shallow clone); CI checks out with fetch-depth 0")

    def test_legacy_is_in_sync(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(gen.main(["--check"]), 0, err.getvalue())

    def test_legacy_with_an_extra_entry_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "legacy.json"
            data = json.loads(gen.LEGACY.read_text(encoding="utf-8"))
            data["skill"]["scripts/retired.py"] = [sha(b"x")]
            stale.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            with mock.patch.object(gen, "LEGACY", stale), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(gen.main(["--check"]), 2)  # stale fails CI, and like every CLI here never exits 1


# ---------------------------------------------------------------- harness targets


class HarnessTargetTests(unittest.TestCase):
    """Target selection and --status need no sc-compose."""

    def test_status_flags_present_harnesses_with_no_install(self):
        repo = TempRepo(self)
        repo.path(".claude/skills/judge-jev").mkdir(parents=True)
        repo.path(".codex").mkdir()
        repo.path(".cursor").mkdir()
        result = inst.status(repo.root)
        self.assertIsInstance(result, inst.Ok, getattr(result, "error", None))
        self.assertEqual(result.value["missing_targets"], ["codex", "cursor"])
        self.assertIn("no judge-jev in .codex/, .cursor/", result.value["message"])

    def test_status_reports_nothing_missing_when_every_harness_is_installed(self):
        repo = TempRepo(self)
        repo.path(".claude/skills/judge-jev").mkdir(parents=True)
        result = inst.status(repo.root)
        self.assertIsInstance(result, inst.Ok, getattr(result, "error", None))
        self.assertEqual(result.value["missing_targets"], [])
        self.assertNotIn("no judge-jev", result.value["message"])

    def test_status_states(self):
        repo = TempRepo(self)
        self.assertEqual(inst.status(repo.root).value["state"], "not_installed")
        lock = repo.path(inst.LOCK_RELPATH)
        lock.parent.mkdir(parents=True)
        for version, state in (("0.0.1", "older"), (VERSION, "current"), ("99.0.0", "newer")):
            with self.subTest(version=version):
                lock.write_text(json.dumps({"package": "sc-judge-jev", "version": version, "targets": ["claude"],
                                            "files": {}}), encoding="utf-8")
                self.assertEqual(inst.status(repo.root).value["state"], state)

    def test_status_reports_a_covering_install_above(self):
        repo = TempRepo(self)
        lock = repo.path(inst.LOCK_RELPATH)
        lock.parent.mkdir(parents=True)
        lock.write_text(json.dumps({"package": "sc-judge-jev", "version": "0.0.1", "targets": ["claude"], "files": {}}),
                        encoding="utf-8")
        sub = repo.path("child")
        sub.mkdir()
        data = inst.status(sub).value
        self.assertEqual((data["state"], data["covering_install"]["root"], data["covering_install"]["version"]),
                         ("not_installed", str(repo.root), "0.0.1"))

    def test_choose_targets_unions_lock_installs_present_and_requested(self):
        repo = TempRepo(self)
        repo.path(".codex/skills/judge-jev").mkdir(parents=True)
        lock = inst.Lock("0.0.9", ("claude",), {})
        self.assertEqual(inst.choose_targets(repo.root, lock, ["cursor"]),
                         {"claude": ["locked"], "codex": ["installed", "present"], "cursor": ["requested"]})

    def test_cli_without_target_requests_nothing(self):
        seen = []
        with mock.patch.object(inst, "install", side_effect=lambda opts, **kw: seen.append(opts) or inst.Ok({})), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(inst.main(["--dest", "."]), 0)
        self.assertEqual(seen[0].targets, [])

    def test_status_takes_only_dest(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = inst.main(["--dest", ".", "--status", "--dry-run"])
        self.assertEqual((code, json.loads(out.getvalue())["error"]["code"]), (2, "VALIDATION.INPUT"))


# ---------------------------------------------------------------- install


class InstallCase(unittest.TestCase):
    """Assertion helpers shared by the install tests (no tests of its own)."""

    def ok(self, result):
        self.assertIsInstance(result, inst.Ok, getattr(result, "error", None) and result.error.to_json())
        return result.value

    def refused(self, result, code):
        self.assertIsInstance(result, inst.Err, result)
        self.assertEqual(result.error.code, code, result.error.to_json())
        return result.error

    def lock(self, repo):
        return json.loads(repo.path(inst.LOCK_RELPATH).read_text(encoding="utf-8"))

    def remote_setting(self, repo):
        path = repo.path(".sc/judge-jev/settings.yaml")
        if not path.exists():
            return []
        return [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("allow_remote_judge:")]

    def assert_installed(self, repo, targets, plugin_dir=PLUGIN):
        lock = self.lock(repo)
        self.assertEqual((lock["package"], lock["version"], lock["targets"]), ("sc-judge-jev", VERSION, list(targets)))
        self.assertNotIn("tracker", lock)
        for key, digest in lock["files"].items():
            self.assertEqual(sha(repo.path(key).read_bytes()), digest, key)
        package = inst.load_package(plugin_dir).value
        for target in targets:
            for rel in package.skill:
                self.assertIn(f".{target}/skills/judge-jev/{rel}", lock["files"])
            for name in package.agents:
                self.assertIn(f".{target}/agents/{name}", lock["files"])
        expected = {f".{t}/skills/judge-jev/{rel}" for t in targets for rel in package.skill}
        expected |= {f".{t}/agents/{n}" for t in targets for n in package.agents}
        self.assertEqual(set(lock["files"]), expected)



@needs_wheel
class InstallTests(InstallCase):
    def test_fresh_install(self):
        repo = TempRepo(self)
        data = self.ok(run_install(repo))
        self.assert_installed(repo, ["claude"])
        self.assertEqual((data["package"], data["version"], data["previous_version"], data["migration"]),
                         ("sc-judge-jev", VERSION, None, True))
        self.assertIn(".claude/", data["commit_paths"])
        self.assertIn(inst.LOCK_RELPATH, data["commit_paths"])
        skill = repo.path(".claude/skills/judge-jev/SKILL.md").read_text(encoding="utf-8")
        self.assertIn(f'version: "{VERSION}"', skill)
        registry = repo.path(".claude/skills/judge-jev/registry.yaml").read_text(encoding="utf-8")
        self.assertIn("path: .claude/skills/judge-jev/SKILL.md", registry)
        self.assertFalse(repo.path(".claude/agents").exists())

    def test_fresh_install_all_targets(self):
        repo = TempRepo(self)
        self.ok(run_install(repo, targets=("claude", "codex", "cursor")))
        self.assert_installed(repo, ["claude", "codex", "cursor"])
        for target in ("claude", "codex", "cursor"):
            registry = repo.path(f".{target}/skills/judge-jev/registry.yaml").read_text(encoding="utf-8")
            self.assertIn(f"path: .{target}/skills/judge-jev/SKILL.md", registry)

    def test_unlocked_claude_install_upgrades_every_present_harness(self):
        repo = TempRepo(self)
        self.ok(run_install(repo))
        repo.path(inst.LOCK_RELPATH).unlink()  # an install without its lock
        repo.path(".codex").mkdir()
        repo.path(".cursor").mkdir()
        data = self.ok(run_install(repo, targets=()))
        self.assertEqual(data["targets"], ["claude", "codex", "cursor"])
        self.assertEqual(data["target_reasons"], {"claude": ["installed", "present"], "codex": ["present"],
                                                  "cursor": ["present"]})
        self.assert_installed(repo, ["claude", "codex", "cursor"])

    def test_locked_targets_are_kept(self):
        repo = TempRepo(self)
        self.ok(run_install(repo, targets=("claude", "codex")))
        data = self.ok(run_install(repo, targets=()))
        self.assertEqual(data["target_reasons"], {"claude": ["locked", "installed", "present"],
                                                  "codex": ["locked", "installed", "present"]})
        self.assert_installed(repo, ["claude", "codex"])

    def test_claude_only_repo_installs_claude_only(self):
        repo = TempRepo(self)
        repo.path(".claude").mkdir()
        data = self.ok(run_install(repo, targets=()))
        self.assertEqual(data["target_reasons"], {"claude": ["present"]})
        self.assert_installed(repo, ["claude"])
        self.assertFalse(repo.path(".codex").exists() or repo.path(".cursor").exists())

    def test_no_harness_and_no_target_defaults_to_claude(self):
        repo = TempRepo(self)
        data = self.ok(run_install(repo, targets=()))
        self.assertEqual(data["target_reasons"], {"claude": ["default"]})
        self.assert_installed(repo, ["claude"])

    def test_explicit_target_adds_to_the_set(self):
        repo = TempRepo(self)
        repo.path(".codex").mkdir()
        data = self.ok(run_install(repo, targets=("cursor",)))
        self.assertEqual(data["target_reasons"], {"codex": ["present"], "cursor": ["requested"]})
        self.assertEqual(self.lock(repo)["targets"], ["codex", "cursor"])

    def test_rerun_is_idempotent(self):
        repo = TempRepo(self)
        self.ok(run_install(repo))
        before = repo.snapshot()
        data = self.ok(run_install(repo))
        plan = data["plan"]
        self.assertEqual((plan["create"], plan["replace"], plan["remove"], plan["backup"]), ([], [], [], []))
        self.assertIsNone(plan["allow_remote_judge"])
        self.assertEqual(data["commit_paths"], [])
        self.assertEqual(data["previous_version"], VERSION)
        self.assertFalse(data["migration"])
        self.assertEqual(repo.snapshot(), before)

    def test_upgrade_replaces_owned_files_and_removes_retired_ones(self):
        repo = TempRepo(self)
        self.ok(run_install(repo))
        lock = self.lock(repo)
        retired = {".claude/skills/judge-jev/scripts/retired.py": b"old script\n",
                   ".claude/skills/judge-jev/tests/test_old.py": b"old test\n"}
        for key, data in retired.items():
            repo.path(key).parent.mkdir(parents=True, exist_ok=True)
            repo.path(key).write_bytes(data)
            lock["files"][key] = sha(data)
        (repo.path(".claude/skills/judge-jev/tests/__pycache__")).mkdir()
        repo.path(".claude/skills/judge-jev/tests/__pycache__/x.pyc").write_bytes(b"\0")
        # an older version's SKILL.md, recorded as written by the installer
        skill = ".claude/skills/judge-jev/SKILL.md"
        repo.path(skill).write_bytes(b"older SKILL.md\n")
        lock["files"][skill] = sha(b"older SKILL.md\n")
        lock["version"] = "0.0.9"
        repo.path(inst.LOCK_RELPATH).write_text(json.dumps(lock), encoding="utf-8")
        repo.path(".claude/agents").mkdir()
        repo.path(".claude/agents/mine.md").write_text("consumer agent\n", encoding="utf-8")
        data = self.ok(run_install(repo))
        self.assertEqual(data["previous_version"], "0.0.9")
        self.assertEqual(data["plan"]["replace"], [skill])
        self.assertEqual(sorted(data["plan"]["remove"]), sorted(retired))
        for key in retired:
            self.assertFalse(repo.path(key).exists(), key)
        self.assertFalse(repo.path(".claude/skills/judge-jev/tests").exists())
        self.assertEqual(repo.path(".claude/agents/mine.md").read_text(encoding="utf-8"), "consumer agent\n")
        self.assert_installed(repo, ["claude"])

    def test_modified_file_is_refused_then_backed_up_with_overwrite(self):
        repo = TempRepo(self)
        self.ok(run_install(repo))
        key = ".claude/skills/judge-jev/SKILL.md"
        repo.path(key).write_text("local edit\n", encoding="utf-8")
        before = repo.snapshot()
        error = self.refused(run_install(repo), "INSTALL.CONFLICT")
        self.assertEqual([(p["code"], p["path"]) for p in error.data["problems"]], [("FILE.MODIFIED", key)])
        self.assertIn(key, error.message)
        self.assertEqual(repo.snapshot(), before)
        data = self.ok(run_install(repo, overwrite=True))
        self.assertEqual(data["plan"]["backup"], [key])
        backups = list(repo.path(".backup").glob(f"*/{key}"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "local edit\n")
        self.assertEqual(repo.path(".backup/.gitignore").read_text(encoding="utf-8"), "*\n")
        self.assertEqual(sha(repo.path(key).read_bytes()), self.lock(repo)["files"][key])

    def test_modified_retired_file_is_refused(self):
        repo = TempRepo(self)
        self.ok(run_install(repo))
        lock = self.lock(repo)
        key = ".claude/skills/judge-jev/scripts/retired.py"
        lock["files"][key] = sha(b"shipped\n")
        repo.path(inst.LOCK_RELPATH).write_text(json.dumps(lock), encoding="utf-8")
        repo.path(key).write_text("edited\n", encoding="utf-8")
        error = self.refused(run_install(repo), "INSTALL.CONFLICT")
        self.assertEqual(error.data["problems"][0]["code"], "FILE.MODIFIED_RETIRED")
        self.assertTrue(repo.path(key).exists())

    def test_unowned_file_is_never_overwritten(self):
        repo = TempRepo(self)
        self.ok(run_install(repo))
        repo.path(inst.LOCK_RELPATH).unlink()
        key = ".claude/skills/judge-jev/SKILL.md"
        repo.path(key).write_text("someone else's skill text\n", encoding="utf-8")
        error = self.refused(run_install(repo), "INSTALL.CONFLICT")
        self.assertEqual([(p["code"], p["path"]) for p in error.data["problems"]], [("FILE.UNOWNED", key)])
        self.assertEqual(repo.path(key).read_text(encoding="utf-8"), "someone else's skill text\n")

    def test_foreign_skill_directory_is_refused(self):
        repo = TempRepo(self)
        repo.path(".claude/skills/judge-jev").mkdir(parents=True)
        repo.path(".claude/skills/judge-jev/SKILL.md").write_text("another skill\n", encoding="utf-8")
        error = self.refused(run_install(repo), "INSTALL.CONFLICT")
        self.assertEqual(error.data["problems"][0]["code"], "SKILL.FOREIGN_DIR")
        self.assertEqual(sorted(repo.snapshot()), [".claude/skills/judge-jev/SKILL.md"])

    def test_stray_file_in_the_skill_directory_is_a_warning(self):
        repo = TempRepo(self)
        self.ok(run_install(repo))
        repo.path(".claude/skills/judge-jev/notes.txt").write_text("mine\n", encoding="utf-8")
        data = self.ok(run_install(repo))
        self.assertEqual(data["warnings"], [".claude/skills/judge-jev/notes.txt: not a sc-judge-jev file; left in place"])
        self.assertTrue(repo.path(".claude/skills/judge-jev/notes.txt").exists())

    def test_dry_run_writes_nothing(self):
        repo = TempRepo(self)
        data = self.ok(run_install(repo, dry_run=True, allow_remote_judge=True))
        self.assertTrue(data["dry_run"])
        self.assertTrue(data["plan"]["create"])
        self.assertEqual(data["plan"]["allow_remote_judge"]["to"], True)
        self.assertEqual(data["commit_paths"], [])
        self.assertEqual(repo.snapshot(), {})

    def test_dest_may_be_a_folder_inside_a_repository(self):
        repo = TempRepo(self)
        repo.path("sub").mkdir()
        data = self.ok(inst.install(inst.Options(dest=repo.path("sub"), targets=["claude"])))
        self.assertEqual((data["install_root"], data["repository"], data["repository_root"]),
                         (str(repo.path("sub")), False, str(repo.root)))
        self.assertTrue(repo.path("sub/.claude/skills/judge-jev/SKILL.md").is_file())

    def test_a_parent_folder_gets_the_inheritance_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp).resolve()
            data = self.ok(inst.install(inst.Options(dest=parent, targets=["claude"])))
        self.assertEqual((data["repository"], data["repository_root"]), (False, None))
        self.assertTrue(any("is not a repository: repositories below it inherit this install" in n for n in data["notes"]))

    def test_dest_must_be_an_existing_directory(self):
        repo = TempRepo(self)
        self.refused(inst.install(inst.Options(dest=repo.path("nope"), targets=["claude"])), "INSTALL.DEST")

    def test_invalid_lock_is_typed_error(self):
        repo = TempRepo(self)
        repo.path(".sc/judge-jev").mkdir(parents=True)
        for text in ("{not json", json.dumps({"package": "sc-plan-anchor", "targets": [], "files": {}})):
            with self.subTest(text=text):
                repo.path(inst.LOCK_RELPATH).write_text(text, encoding="utf-8")
                self.refused(run_install(repo), "INSTALL.LOCK_INVALID")

    def test_missing_sc_compose_is_typed_error(self):
        repo = TempRepo(self)
        real = importlib.import_module

        def fake(name, *a, **k):
            if name == "sc_compose":
                raise ImportError("No module named 'sc_compose'")
            return real(name, *a, **k)

        with mock.patch.object(inst.importlib, "import_module", side_effect=fake):
            error = self.refused(run_install(repo), "DEPENDENCY.SC_COMPOSE")
        self.assertIn("uv run", error.action)
        self.assertEqual(repo.snapshot(), {})

    def test_cli_envelope_and_exit_codes(self):
        repo = TempRepo(self)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = inst.main(["--dest", str(repo.root), "--dry-run"])
        envelope = json.loads(out.getvalue())
        self.assertEqual((code, envelope["success"], envelope["error"]), (0, True, None))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = inst.main(["--dest", str(repo.root), "--target", "vim"])
        envelope = json.loads(out.getvalue())
        self.assertEqual((code, envelope["error"]["code"]), (2, "VALIDATION.INPUT"))
        out = io.StringIO()
        with mock.patch.object(inst, "install", side_effect=RuntimeError("boom")), contextlib.redirect_stdout(out):
            code = inst.main(["--dest", str(repo.root)])
        envelope = json.loads(out.getvalue())
        self.assertEqual((code, envelope["success"], envelope["error"]["code"]), (2, False, "SCRIPT.INTERNAL"))

    def test_remote_judge_flags_write_the_setting_and_reruns_keep_it(self):
        repo = TempRepo(self)
        data = self.ok(run_install(repo))
        self.assertEqual((data["allow_remote_judge"], data["plan"]["allow_remote_judge"]), (None, None))
        self.assertFalse(repo.path(".sc/judge-jev/settings.yaml").exists())
        self.assertTrue(any("does not set allow_remote_judge" in n for n in data["notes"]))
        data = self.ok(run_install(repo, allow_remote_judge=True))
        self.assertEqual(data["plan"]["allow_remote_judge"],
                         {"path": ".sc/judge-jev/settings.yaml", "from": None, "to": True})
        self.assertIn(".sc/judge-jev/settings.yaml", data["commit_paths"])
        self.assertEqual(self.remote_setting(repo), ["allow_remote_judge: true"])
        self.assertFalse(any("does not set allow_remote_judge" in n for n in data["notes"]))
        before = repo.snapshot()
        data = self.ok(run_install(repo))  # no flag: the recorded answer is kept, nothing is rewritten
        self.assertEqual((data["allow_remote_judge"], data["plan"]["allow_remote_judge"], data["commit_paths"]), (True, None, []))
        self.assertEqual(repo.snapshot(), before)
        data = self.ok(run_install(repo, allow_remote_judge=False))
        self.assertEqual(data["plan"]["allow_remote_judge"]["to"], False)
        self.assertEqual(self.remote_setting(repo), ["allow_remote_judge: false"])
        self.ok(run_install(repo))  # a rerun that rewrites nothing else still keeps it
        self.assertEqual(self.remote_setting(repo), ["allow_remote_judge: false"])

    def test_a_parent_folders_consent_is_never_copied(self):
        repo = TempRepo(self)
        settings = repo.path(".sc/judge-jev/settings.yaml")
        settings.parent.mkdir(parents=True)
        settings.write_text("schema_version: 1\nallow_remote_judge: true\n", encoding="utf-8")
        repo.path("sub").mkdir()
        data = self.ok(inst.install(inst.Options(dest=repo.path("sub"), targets=["claude"])))
        self.assertIsNone(data["allow_remote_judge"])
        self.assertFalse(repo.path("sub/.sc/judge-jev/settings.yaml").exists())

    def test_a_hand_written_yaml_yes_reads_as_true_and_writes_back_as_bools(self):
        """Operator decision 2026-10-19: ``yes`` counts as true; the installer only ever writes true or false."""
        repo = TempRepo(self)
        self.ok(run_install(repo, allow_remote_judge=True))
        settings = repo.path(".sc/judge-jev/settings.yaml")
        settings.write_text(settings.read_text(encoding="utf-8").replace("allow_remote_judge: true\n",
                                                                         "allow_remote_judge: yes\n"), encoding="utf-8")
        before = repo.snapshot()
        data = self.ok(run_install(repo, allow_remote_judge=True))  # same answer: nothing to change or rewrite
        self.assertEqual((data["allow_remote_judge"], data["plan"]["allow_remote_judge"], data["commit_paths"]), (True, None, []))
        self.assertEqual(repo.snapshot(), before)
        data = self.ok(run_install(repo, allow_remote_judge=False))
        self.assertEqual(data["plan"]["allow_remote_judge"],
                         {"path": ".sc/judge-jev/settings.yaml", "from": True, "to": False})
        self.assertEqual(self.remote_setting(repo), ["allow_remote_judge: false"])

    def test_a_malformed_settings_file_is_refused(self):
        repo = TempRepo(self)
        settings = repo.path(".sc/judge-jev/settings.yaml")
        settings.parent.mkdir(parents=True)
        for text, code in (("schema_version: 1\nanchor_tracker: br\n", "SETTINGS.UNKNOWN_KEY"),
                           ("schema_version: 2\n", "SETTINGS.SCHEMA_VERSION"),
                           ("schema_version: 1\nallow_remote_judge: 'yes'\n", "SETTINGS.INVALID_REMOTE_JUDGE"),
                           ("schema_version: [1\n", "SETTINGS.MALFORMED")):
            with self.subTest(text=text):
                settings.write_text(text, encoding="utf-8")
                self.refused(run_install(repo, allow_remote_judge=True), code)
                self.assertEqual(settings.read_text(encoding="utf-8"), text)

    def test_remote_judge_cli_flags(self):
        repo = TempRepo(self)
        for argv, expected in ((["--allow-remote-judge"], ["allow_remote_judge: true"]),
                               (["--no-remote-judge"], ["allow_remote_judge: false"]),
                               ([], ["allow_remote_judge: false"])):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = inst.main(["--dest", str(repo.root), *argv])
            self.assertEqual(code, 0, out.getvalue())
            self.assertEqual(self.remote_setting(repo), expected)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = inst.main(["--dest", str(repo.root), "--allow-remote-judge", "--no-remote-judge"])
        self.assertEqual((code, json.loads(out.getvalue())["error"]["code"]), (2, "VALIDATION.INPUT"))
        self.assertEqual(self.remote_setting(repo), ["allow_remote_judge: false"])

    def test_target_dot_form_is_accepted(self):
        self.assertEqual(inst._targets(".claude,codex"), ["claude", "codex"])


# ---------------------------------------------------------------- agents and legacy migration (planted packages)


@needs_wheel
class PlantedPackageTests(InstallCase):
    """install.py's agent and legacy-migration paths, exercised with a plugin copy that ships an agent and history.

    This package ships no agent and no earlier version yet; the copies prove the code paths a later release uses.
    """

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.plugin = plugin_with_agent(Path(td.name) / "plugin")

    def test_planted_agent_is_rendered_for_every_target(self):
        repo = TempRepo(self)
        data = self.ok(run_install(repo, targets=("claude", "codex", "cursor"), plugin_dir=self.plugin))
        self.assert_installed(repo, ["claude", "codex", "cursor"], plugin_dir=self.plugin)
        for target in inst.TARGETS:
            text = repo.path(f".{target}/agents/{AGENT_NAME}").read_text(encoding="utf-8")
            self.assertEqual(text, f"---\nname: demo-agent\nversion: {VERSION}\n---\n# demo agent {VERSION}\n")
            self.assertIn(f".{target}/agents/{AGENT_NAME}", data["plan"]["create"])

    def test_planted_agent_edit_is_refused(self):
        repo = TempRepo(self)
        self.ok(run_install(repo, plugin_dir=self.plugin))
        key = f".claude/agents/{AGENT_NAME}"
        repo.path(key).write_text("edited\n", encoding="utf-8")
        error = self.refused(run_install(repo, plugin_dir=self.plugin), "INSTALL.CONFLICT")
        self.assertEqual([(p["code"], p["path"]) for p in error.data["problems"]], [("FILE.MODIFIED", key)])

    def test_missing_harness_frontmatter_is_a_package_error(self):
        (self.plugin / "install" / "harness" / "cursor" / "agents" / AGENT_NAME).unlink()
        loaded = inst.load_package(self.plugin)
        self.assertEqual(loaded.error.code, "INSTALL.PACKAGE_INVALID")
        self.assertIn(f"install/harness/cursor/agents/{AGENT_NAME}", loaded.error.message)

    def test_unlocked_folder_migrates_legacy_files(self):
        old_skill, old_agent = b"0.0.1 SKILL.md\n", b"0.0.1 retired agent\n"
        legacy = {"_comment": "planted", "skill": {"SKILL.md": [sha(old_skill)], "scripts/retired.py": [sha(b"old\n")]},
                  "agents": {"claude": {"retired-agent.md": [sha(old_agent)]}, "codex": {}, "cursor": {}}}
        (self.plugin / "install" / "legacy-owned.json").write_text(json.dumps(legacy), encoding="utf-8")
        repo = TempRepo(self)
        placed = {".claude/skills/judge-jev/SKILL.md": old_skill,
                  ".claude/skills/judge-jev/scripts/retired.py": b"old\n",
                  ".claude/agents/retired-agent.md": old_agent}
        for key, data in placed.items():
            repo.path(key).parent.mkdir(parents=True, exist_ok=True)
            repo.path(key).write_bytes(data)
        data = self.ok(run_install(repo, targets=(), plugin_dir=self.plugin))
        self.assertTrue(data["migration"])
        self.assertIn(".claude/skills/judge-jev/SKILL.md", data["plan"]["replace"])
        self.assertEqual(sorted(data["plan"]["remove"]),
                         [".claude/agents/retired-agent.md", ".claude/skills/judge-jev/scripts/retired.py"])
        self.assertEqual(data["warnings"], [])
        self.assert_installed(repo, ["claude"], plugin_dir=self.plugin)
        rerun = self.ok(run_install(repo, plugin_dir=self.plugin))
        self.assertEqual((rerun["plan"]["create"], rerun["plan"]["replace"], rerun["plan"]["remove"]), ([], [], []))

    def test_edited_legacy_file_is_left_with_a_warning(self):
        legacy = {"_comment": "planted", "skill": {"scripts/retired.py": [sha(b"old\n")]},
                  "agents": {"claude": {}, "codex": {}, "cursor": {}}}
        (self.plugin / "install" / "legacy-owned.json").write_text(json.dumps(legacy), encoding="utf-8")
        repo = TempRepo(self)
        key = ".claude/skills/judge-jev/scripts/retired.py"
        repo.path(key).parent.mkdir(parents=True)
        repo.path(key).write_bytes(b"old, edited\n")
        repo.path(".claude/skills/judge-jev/SKILL.md").write_bytes(b"unknown\n")
        # an unknown SKILL.md plus an edited legacy file: nothing in the folder is ours
        error = self.refused(run_install(repo, plugin_dir=self.plugin), "INSTALL.CONFLICT")
        self.assertEqual(error.data["problems"][0]["code"], "SKILL.FOREIGN_DIR")
        repo.path(".claude/skills/judge-jev/SKILL.md").unlink()
        repo.path(".claude/skills/judge-jev/scripts/kept.py").write_bytes(b"x\n")
        legacy["skill"]["scripts/kept.py"] = [sha(b"x\n")]
        (self.plugin / "install" / "legacy-owned.json").write_text(json.dumps(legacy), encoding="utf-8")
        data = self.ok(run_install(repo, plugin_dir=self.plugin))
        self.assertTrue(repo.path(key).exists())
        self.assertTrue(any(w.startswith(f"{key}: an earlier sc-judge-jev version shipped this path") for w in data["warnings"]))


# ---------------------------------------------------------------- real installs


@needs_wheel
class RealInstallTests(unittest.TestCase):
    """install.py run as a process into scratch repositories, every target; the files on disk are checked."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp = Path(td.name).resolve()

    def repo(self, name):
        root = self.tmp / name
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        return root

    def install(self, root, plugin=PLUGIN, extra=("--no-remote-judge",)):
        env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
        proc = subprocess.run([sys.executable, str(Path(plugin) / "install.py"), "--dest", str(root),
                               "--target", ",".join(inst.TARGETS), *extra],
                              env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["success"], proc.stdout)
        return root

    def test_every_installed_md_and_py_is_rendered_from_a_template(self):
        root = self.install(self.repo("j2"))
        checked = 0
        for top in [f".{t}" for t in inst.TARGETS]:
            for path in sorted((root / top).rglob("*")):
                rel = path.relative_to(root).as_posix()
                if not path.is_file() or not rel.endswith((".md", ".py")):
                    continue
                with self.subTest(path=rel):
                    rest = rel.split("/skills/judge-jev/", 1)[1]
                    source = SKILL_SRC / f"{rest}.j2"
                    self.assertTrue(source.is_file(), source)
                    self.assertTrue(inst.is_install_template(source), source)
                    checked += 1
        package = inst.load_package().value
        self.assertEqual(checked, 3 * len([r for r in package.skill if r.endswith((".md", ".py"))]))
        settings = (root / ".sc" / "judge-jev" / "settings.yaml").read_text(encoding="utf-8")
        self.assertTrue(settings.endswith("allow_remote_judge: false\n"), settings)

    def test_installed_scripts_run(self):
        root = self.install(self.repo("run"))
        proc = subprocess.run([sys.executable, str(root / ".codex/skills/judge-jev/scripts/judge_jev_settings.py"),
                               "show", "--repository-root", str(root)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIs(json.loads(proc.stdout)["data"]["allow_remote_judge"], False)

    def test_a_second_install_folder_upgrades_on_its_own(self):
        parent = self.tmp / "parent"
        parent.mkdir()
        self.install(parent)
        child = self.repo("parent/child")
        self.install(child)
        for root in (parent, child):
            lock = json.loads((root / ".sc" / "judge-jev" / "install-lock.json").read_text(encoding="utf-8"))
            self.assertEqual(lock["targets"], list(inst.TARGETS))


if __name__ == "__main__":
    unittest.main()
