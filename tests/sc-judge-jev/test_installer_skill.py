"""The judge-jev-installer plugin: destinations, parent-folder installs, the hook, --status.

The marketplace plugin ships one skill, ``judge-jev-installer``, which runs
install.py into any folder except a global harness location. The trusted
jev_judge.py is the one in the nearest per-folder install walking up from the
working directory (stopping before the home directory), and the nearest
settings file applies. A SessionStart hook prints one line when the nearest
install is older than the plugin.

Tests that render need the sc-compose wheel and skip without it, unless
JUDGE_JEV_REQUIRE_SC_COMPOSE=1 (CI's installer job). No test calls Jev;
TYPESAFE_API_KEY is removed from every child environment.
"""

import contextlib
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

from layout_support import PLUGIN, SCRIPTS, TARGETS
from test_install import VERSION, inst, needs_wheel

sys.path.insert(0, str(SCRIPTS))
import judge_jev_paths as paths  # noqa: E402

HOOK = PLUGIN / "hooks" / "check_install.py"
INSTALLER_SKILL = PLUGIN / "skills" / "judge-jev-installer" / "SKILL.md"
ERROR_KEYS = {"code", "message", "recoverable", "suggested_action"}
PLANTED_JUDGE = ("---\nname: sc-judge-jev-script-jev_judge\nversion: 1.0.0\nformat: python\n"
                 "description: test fixture\nrequired_variables:\n  - version\n---\n"
                 "#!/usr/bin/env python3\nVERSION = \"{{ version }}\"\n")


def child_env(home=None):
    environment = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
    if home is not None:
        environment["HOME"] = environment["USERPROFILE"] = str(home)
    return environment


@contextlib.contextmanager
def fake_home(home):
    """os.path.expanduser('~') answers ``home`` in this process (HOME on POSIX, USERPROFILE on Windows)."""
    with mock.patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}):
        yield


def call_main(argv, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = inst.main(argv, **kw)
    return code, json.loads(out.getvalue())


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in Path(root).rglob("*") if p.is_file()}


def git_repo(path, settings=None):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    if settings is not None:
        (path / ".sc" / "judge-jev").mkdir(parents=True)
        (path / ".sc" / "judge-jev" / "settings.yaml").write_text(settings, encoding="utf-8")
    return path


def write_lock(folder, version, targets=("claude",)):
    lock = Path(folder) / ".sc" / "judge-jev" / "install-lock.json"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"package": "sc-judge-jev", "version": version, "targets": list(targets), "files": {}}),
                    encoding="utf-8")
    return lock


def plugin_with_judge(dest):
    """A copy of the plugin whose skill ships a jev_judge.py, the script the trust rule selects."""
    shutil.copytree(PLUGIN, dest, ignore=shutil.ignore_patterns("__pycache__"))
    template = dest / "install" / "templates" / "skills" / "judge-jev" / "scripts" / "jev_judge.py.j2"
    if not template.exists():
        template.write_text(PLANTED_JUDGE, encoding="utf-8")
    return dest


class Scratch(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp = Path(td.name).resolve()
        self.home = self.tmp / "home"
        self.home.mkdir()


# ---------------------------------------------------------------- destinations


class GlobalDestinationTests(Scratch):
    """--dest refuses only global locations, with a typed error and exit 2; nothing is written."""

    def global_dests(self):
        for rel in ("", ".claude", ".codex", ".cursor", ".agents", ".claude/skills",
                    ".claude/plugins/cache/judge-jev/sc-judge-jev/0.1.0", ".codex/plugins/cache/x"):
            dest = self.home / rel
            dest.mkdir(parents=True, exist_ok=True)
            yield rel or "~", dest

    def test_global_destinations_are_refused_with_exit_two(self):
        for label, dest in self.global_dests():
            before = tree(self.home)
            with self.subTest(dest=label), fake_home(self.home):
                code, out = call_main(["--dest", str(dest), "--no-remote-judge", "--target", "claude,codex,cursor"])
                self.assertEqual((code, out["success"]), (2, False), out)
                self.assertEqual(set(out["error"]), ERROR_KEYS)
                self.assertEqual(out["error"]["code"], "INSTALL.DEST_GLOBAL")
                self.assertEqual(out["data"], {"dest": str(dest.resolve())})
                self.assertEqual(tree(self.home), before)  # nothing written
                code, out = call_main(["--dest", str(dest), "--status"])
                self.assertEqual((code, out["error"]["code"]), (2, "INSTALL.DEST_GLOBAL"))

    def test_the_plugin_directory_is_refused(self):
        code, out = call_main(["--dest", str(PLUGIN), "--dry-run"])
        self.assertEqual((code, out["error"]["code"]), (2, "INSTALL.DEST_GLOBAL"))
        self.assertIn("inside the plugin directory", out["error"]["message"])

    def test_refusal_through_the_real_process(self):
        dest = self.home / ".claude"
        dest.mkdir()
        proc = subprocess.run([sys.executable, str(PLUGIN / "install.py"), "--dest", str(dest)],
                              env=child_env(self.home), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        envelope = json.loads(proc.stdout)
        self.assertEqual((envelope["success"], envelope["error"]["code"]), (False, "INSTALL.DEST_GLOBAL"))
        self.assertEqual(list(dest.iterdir()), [])

    def test_a_folder_under_home_is_not_global(self):
        with fake_home(self.home):
            for rel in ("work", "work/repo", "src/.claude-notes"):
                with self.subTest(rel=rel):
                    self.assertIsNone(paths.global_location(self.home / rel))
            for rel in (".claude", ".codex/skills", ".cursor/plugins", ".agents/skills/x"):
                with self.subTest(rel=rel):
                    self.assertIsNotNone(paths.global_location(self.home / rel))
            self.assertIsNotNone(paths.global_location(self.home))


# ---------------------------------------------------------------- parent folder


@needs_wheel
class ParentFolderInstallTests(Scratch):
    """One install in a non-git parent folder serves child repositories."""

    def setUp(self):
        super().setUp()
        self.plugin = plugin_with_judge(self.tmp / "plugin")
        self.parent = self.home / "work"            # not a repository
        self.parent.mkdir()
        self.child = git_repo(self.parent / "svc")
        self.own = git_repo(self.parent / "svc-own", settings="schema_version: 1\n")
        (self.child / "src").mkdir()
        with fake_home(self.home):
            code, out = call_main(["--dest", str(self.parent), "--no-remote-judge", "--target", "claude,codex,cursor"],
                                  plugin_dir=self.plugin)
        self.assertEqual(code, 0, out)
        self.data = out["data"]

    def test_install_writes_the_parent_and_no_child(self):
        self.assertFalse(self.data["repository"])
        self.assertEqual(self.data["targets"], list(TARGETS))
        self.assertTrue(any("is not a repository" in n for n in self.data["notes"]), self.data["notes"])
        for target in TARGETS:
            self.assertTrue((self.parent / f".{target}" / "skills" / "judge-jev" / "SKILL.md").is_file())
        for child in (self.child, self.own):
            self.assertFalse((child / ".claude").exists())
        self.assertFalse((self.child / ".sc").exists())

    def test_trust_lookup_finds_the_parent_copy_from_each_child(self):
        with fake_home(self.home):
            for start in (self.child / "src", self.own):
                with self.subTest(child=start.name):
                    root, copies = paths.find_installs(start)
                    self.assertEqual(root, self.parent)
                    self.assertEqual(sorted(c.parent.parent.parent.parent.name for c in copies),
                                     [".claude", ".codex", ".cursor"])
                    for copy in copies:
                        self.assertEqual(paths.trusted_script(copy, start), (True, f"nearest install {self.parent}"))

    def test_a_hand_copied_script_is_not_trusted(self):
        rogue = self.child / ".claude" / "skills" / "judge-jev" / "scripts" / "jev_judge.py"
        rogue.parent.mkdir(parents=True)
        shutil.copyfile(self.parent / ".claude" / "skills" / "judge-jev" / "scripts" / "jev_judge.py", rogue)
        with fake_home(self.home):
            ok, why = paths.trusted_script(rogue, self.child / "src")
            parent_copy = self.parent / ".claude" / "skills" / "judge-jev" / "scripts" / "jev_judge.py"
            ok_parent, why_parent = paths.trusted_script(parent_copy, self.child / "src")
        self.assertFalse(ok, why)  # nearest install is the child, but its lock (absent) does not list it
        self.assertFalse(ok_parent, why_parent)  # the parent copy is no longer the nearest
        self.assertIn(f"the nearest install is {self.child}", why_parent)

    def test_settings_lookup_picks_the_nearest_file(self):
        import judge_jev_settings as settings_mod
        if settings_mod.load_yaml().ok is False:
            self.skipTest("the settings lookup reads settings.yaml with PyYAML")
        with fake_home(self.home):
            inherited = settings_mod.effective_settings(self.child / "src")
            own = settings_mod.effective_settings(self.own)
        parent_settings = self.parent / ".sc" / "judge-jev" / "settings.yaml"
        self.assertEqual(inherited.value.path, parent_settings)
        self.assertIs(inherited.value.settings.allow_remote_judge, False)  # the parent's answer applies
        self.assertEqual(own.value.path, self.own / ".sc" / "judge-jev" / "settings.yaml")
        self.assertIsNone(own.value.settings.allow_remote_judge)  # files are not merged: nearest wins whole

    def test_a_child_install_overrides_the_parent(self):
        with fake_home(self.home):
            code, out = call_main(["--dest", str(self.own), "--no-remote-judge"], plugin_dir=self.plugin)
            self.assertEqual(code, 0, out)
            self.assertEqual(paths.find_installs(self.own)[0], self.own)
            self.assertEqual(paths.find_installs(self.child)[0], self.parent)


# ---------------------------------------------------------------- hook


class SessionStartHookTests(Scratch):
    def run_hook(self, cwd):
        proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"cwd": str(cwd), "hook_event_name": "SessionStart"}),
                              env=child_env(self.home), capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        return proc.stdout

    def folder(self):
        repo = self.home / "work" / "repo"
        (repo / "src").mkdir(parents=True)
        return repo

    def test_silent_without_a_lock(self):
        repo = self.folder()
        before = tree(self.tmp)
        self.assertEqual(self.run_hook(repo / "src"), "")
        self.assertEqual(tree(self.tmp), before)

    def test_silent_when_current_or_newer(self):
        repo = self.folder()
        for version in (VERSION, "99.0.0"):
            with self.subTest(version=version):
                write_lock(repo, version)
                before = tree(self.tmp)
                self.assertEqual(self.run_hook(repo / "src"), "")
                self.assertEqual(tree(self.tmp), before)

    def test_one_line_when_older(self):
        repo = self.folder()
        write_lock(repo.parent, "0.0.1")  # a parent-folder install covers the repository
        before = tree(self.tmp)
        out = self.run_hook(repo / "src")
        self.assertEqual(out, f"judge-jev 0.0.1 installed, {VERSION} available: run judge-jev-installer ({repo.parent})\n")
        self.assertEqual(tree(self.tmp), before)

    def test_nearest_lock_wins_and_the_walk_stops_before_home(self):
        repo = self.folder()
        write_lock(repo.parent, "0.0.1")
        write_lock(repo, VERSION)
        self.assertEqual(self.run_hook(repo / "src"), "")
        stray = self.home / "elsewhere"
        stray.mkdir()
        write_lock(self.home, "0.0.1")  # a lock in the home directory itself is never visited
        self.assertEqual(self.run_hook(stray), "")

    def test_unreadable_lock_or_input_is_silent(self):
        repo = self.folder()
        lock = write_lock(repo, "0.0.1")
        lock.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.run_hook(repo), "")
        proc = subprocess.run([sys.executable, str(HOOK)], input="not json", cwd=str(repo), env=child_env(self.home),
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual((proc.returncode, proc.stdout), (0, ""))

    def test_registered_for_session_start_and_offline(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        [entry] = hooks["hooks"]["SessionStart"]
        [command] = entry["hooks"]
        self.assertEqual(command["type"], "command")
        self.assertEqual(command["command"], 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/check_install.py"')
        source = HOOK.read_text(encoding="utf-8")
        for forbidden in ("urllib", "socket", "http", "write_text", "write_bytes", "open("):
            self.assertNotIn(forbidden, source)


# ---------------------------------------------------------------- --status


class StatusTests(Scratch):
    def status(self, dest):
        with fake_home(self.home):
            code, out = call_main(["--dest", str(dest), "--status"])
        self.assertEqual(code, 0, out)
        return out["data"]

    def test_states_and_message(self):
        repo = self.home / "work" / "repo"
        repo.mkdir(parents=True)
        data = self.status(repo)
        self.assertEqual((data["state"], data["installed_version"], data["installer_version"]),
                         ("not_installed", None, VERSION))
        write_lock(repo.parent, "0.0.1")
        data = self.status(repo)
        self.assertEqual(data["state"], "not_installed")
        self.assertEqual(data["covering_install"], {"root": str(repo.parent), "version": "0.0.1", "valid": True})
        write_lock(repo, "0.0.1")
        data = self.status(repo)
        self.assertEqual((data["state"], data["message"]), ("older", f"installed 0.0.1, installer {VERSION}"))
        write_lock(repo, VERSION)
        self.assertEqual(self.status(repo)["state"], "current")
        write_lock(repo, "99.0.0")
        self.assertEqual(self.status(repo)["state"], "newer")
        before = tree(self.tmp)
        self.status(repo)
        self.assertEqual(tree(self.tmp), before)

    def test_status_takes_only_dest(self):
        with fake_home(self.home):
            code, out = call_main(["--dest", str(self.home / "x"), "--status", "--target", "claude"])
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))


# ---------------------------------------------------------------- the installer skill


class InstallerSkillTextTests(unittest.TestCase):
    def setUp(self):
        self.text = INSTALLER_SKILL.read_text(encoding="utf-8")

    def test_frontmatter(self):
        front = self.text.split("---\n")[1]
        self.assertIn("name: judge-jev-installer\n", front)
        self.assertIn(f'version: "{VERSION}"', front)

    def test_runs_the_installer_from_the_plugin_directory(self):
        self.assertIn('uv run "${CLAUDE_PLUGIN_ROOT}/install.py" --dest <folder> \\', self.text)
        self.assertIn("--allow-remote-judge|--no-remote-judge", self.text)
        self.assertIn('uv run "${CLAUDE_PLUGIN_ROOT}/install.py" --dest <folder> --status', self.text)
        self.assertNotIn("../", self.text)
        self.assertNotIn("--tracker", self.text)

    def test_compares_versions_first_and_upgrades_by_rerunning(self):
        flat = " ".join(self.text.split())
        self.assertLess(self.text.index("--status"), self.text.index("## 2. Settings"))
        self.assertIn('"installed 0.1.0, installer 0.2.0"', flat)
        self.assertIn("An upgrade is the same command rerun", flat)

    def test_asks_once_and_never_infers_consent(self):
        flat = " ".join(self.text.split())
        self.assertEqual(flat.count("ask the user once"), 1)  # remote-judge consent
        self.assertIn("Never infer consent from earlier runs", flat)


@needs_wheel
class SelfContainedPluginTests(Scratch):
    """Every package file install.py reads is inside the plugin directory: a lone copy of it installs the same bytes."""

    def test_a_copy_of_the_plugin_alone_installs(self):
        copy = self.tmp / "cache" / "sc-judge-jev"
        shutil.copytree(PLUGIN, copy, ignore=shutil.ignore_patterns("__pycache__"))
        repo = git_repo(self.tmp / "repo")
        proc = subprocess.run([sys.executable, "-I", str(copy / "install.py"), "--dest", str(repo),
                               "--no-remote-judge", "--target", "claude,codex,cursor"], cwd=str(self.tmp),
                              env=child_env(self.home), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        mirror = git_repo(self.tmp / "mirror")
        code, out = call_main(["--dest", str(mirror), "--no-remote-judge", "--target", "claude,codex,cursor"])
        self.assertEqual(code, 0, out)
        installed = {k: v for k, v in tree(repo).items() if not k.startswith(".git/")}
        expected = {k: v for k, v in tree(mirror).items() if not k.startswith(".git/")}
        self.assertEqual(sorted(installed), sorted(expected))
        self.assertEqual(installed, expected)


if __name__ == "__main__":
    unittest.main()
