"""allow_remote_judge: the committed answer that gates every live Jev call.

The repository's .sc/judge-jev/settings.yaml records whether record text may be
sent to TypeSafe. judge_jev_settings.py reads it (``show``,
``remote_judge_consent``) and records it (``set``). Tests that parse a present
settings file need PyYAML and skip with the reason when it is missing. Every
result is checked with ``.ok``, never isinstance.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from layout_support import PLUGIN, SCRIPTS  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import judge_jev_settings as settings_mod  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_SCRIPT = SCRIPTS / "judge_jev_settings.py"
HAS_YAML = importlib.util.find_spec("yaml") is not None
NO_YAML = "PyYAML is not installed (python3 -m pip install pyyaml); parsing a present settings file needs it"
HEADER = ("# .sc/judge-jev/settings.yaml\n"
          "# Repository settings for the sc-judge-jev plugin; commit this file, never put secrets in it.\n"
          "schema_version: 1\n")
REMOTE_COMMENT = "# allow_remote_judge: may record text be sent to TypeSafe (Jev) for judging? Only the user decides it.\n"


class Repo:
    """A repository root (``.git`` marker) with an optional settings file."""

    def __init__(self, test, text=None):
        td = tempfile.TemporaryDirectory()
        test.addCleanup(td.cleanup)
        self.root = Path(td.name).resolve()
        (self.root / ".git").mkdir()
        if text is not None:
            self.write(text)

    @property
    def settings(self):
        return self.root / ".sc" / "judge-jev" / "settings.yaml"

    def write(self, text):
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text(text, encoding="utf-8")

    def answer(self, value):
        self.write(f"schema_version: 1\nallow_remote_judge: {value}\n")
        return self


def yaml_test(fn):
    return unittest.skipUnless(HAS_YAML, NO_YAML)(fn)


class ConsentTests(unittest.TestCase):
    @yaml_test
    def test_true_and_false(self):
        self.assertIs(settings_mod.remote_judge_consent(Repo(self).answer("true").root).value, True)
        self.assertIs(settings_mod.remote_judge_consent(Repo(self).answer("false").root).value, False)

    @yaml_test
    def test_true_is_found_from_a_subdirectory(self):
        repo = Repo(self).answer("true")
        sub = repo.root / "doc" / "plan"
        sub.mkdir(parents=True)
        with mock.patch.object(settings_mod, "_git_toplevel", lambda start: None):
            self.assertTrue(settings_mod.remote_judge_consent(settings_mod.find_repo_root(sub).value).value)

    def test_absent_file_is_unset(self):
        outcome = settings_mod.remote_judge_consent(Repo(self).root)
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.error.code, "SETTINGS.REMOTE_JUDGE_UNSET")

    def test_absent_answer_needs_no_pyyaml(self):
        repo = Repo(self)
        with mock.patch.dict(sys.modules, {"yaml": None}):
            outcome = settings_mod.remote_judge_consent(repo.root)
        self.assertEqual(outcome.error.code, "SETTINGS.REMOTE_JUDGE_UNSET")

    @yaml_test
    def test_file_without_the_key_is_unset(self):
        outcome = settings_mod.remote_judge_consent(Repo(self, "schema_version: 1\n").root)
        self.assertEqual(outcome.error.code, "SETTINGS.REMOTE_JUDGE_UNSET")

    @yaml_test
    def test_invalid_value_is_a_typed_error(self):
        for value in ("'true'", "1", "null", "maybe", "[true]"):
            with self.subTest(value=value):
                outcome = settings_mod.remote_judge_consent(Repo(self).answer(value).root)
                self.assertEqual(outcome.error.code, "SETTINGS.INVALID_REMOTE_JUDGE")

    @yaml_test
    def test_yaml_yes_and_no_are_bools(self):
        """Operator decision 2026-10-19: YAML 1.1 ``yes``/``no`` are bools."""
        self.assertIs(settings_mod.remote_judge_consent(Repo(self).answer("yes").root).value, True)
        self.assertIs(settings_mod.remote_judge_consent(Repo(self).answer("no").root).value, False)

    @yaml_test
    def test_quoted_yes_and_no_are_strings_not_answers(self):
        """Planted negative: quoted, the same words are strings, so the bare-word test above passes only as YAML bools."""
        for value in ("'yes'", '"yes"', "'no'", '"no"'):
            with self.subTest(value=value):
                outcome = settings_mod.remote_judge_consent(Repo(self).answer(value).root)
                self.assertEqual(outcome.error.code, "SETTINGS.INVALID_REMOTE_JUDGE")

    @yaml_test
    def test_show_through_the_script_reads_yes_and_no_as_bools(self):
        cases = (("yes", 0, True, None), ("no", 0, False, None), ("'yes'", 2, None, "SETTINGS.INVALID_REMOTE_JUDGE"))
        for value, code, shown, error in cases:
            with self.subTest(value=value):
                repo = Repo(self).answer(value)
                proc = subprocess.run([sys.executable, str(SETTINGS_SCRIPT), "show", "--repository-root", str(repo.root)],
                                      capture_output=True, text=True, encoding="utf-8",
                                      env={k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"})
                self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
                out = json.loads(proc.stdout)
                if error is None:
                    self.assertIs(out["data"]["allow_remote_judge"], shown)
                else:
                    self.assertEqual(out["error"]["code"], error)

    @yaml_test
    def test_unknown_key_is_rejected(self):
        outcome = settings_mod.remote_judge_consent(Repo(self, "schema_version: 1\nallow_remote_judge: true\nallow_remote: true\n").root)
        self.assertEqual(outcome.error.code, "SETTINGS.UNKNOWN_KEY")

    def test_missing_pyyaml_with_a_settings_file_is_dependency_error(self):
        repo = Repo(self, "schema_version: 1\nallow_remote_judge: true\n")
        with mock.patch.dict(sys.modules, {"yaml": None}):
            outcome = settings_mod.remote_judge_consent(repo.root)
        self.assertEqual(outcome.error.code, "DEPENDENCY.PYYAML")
        self.assertIn("python3 -m pip install pyyaml", outcome.error.action)

    def test_outside_a_repository_is_a_typed_error(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(settings_mod, "_git_toplevel", lambda start: None):
                outcome = settings_mod.find_repo_root(Path(d))
            if outcome.ok:
                self.skipTest("the temporary directory is inside a repository here")
            self.assertEqual(outcome.error.code, "REPO.NOT_FOUND")


@unittest.skipUnless(HAS_YAML, NO_YAML)
class SetCommandTests(unittest.TestCase):
    def main(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = settings_mod.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_set_true_writes_the_committed_form_and_reads_back(self):
        repo = Repo(self)
        code, out = self.main("set", "allow_remote_judge", "true", "--repository-root", str(repo.root))
        self.assertEqual(code, 0, out)
        self.assertEqual((out["data"]["value"], out["data"]["previous"], out["data"]["written"], out["data"]["commit_paths"]),
                         (True, None, True, [".sc/judge-jev/settings.yaml"]))
        self.assertEqual(repo.settings.read_text(encoding="utf-8"), HEADER + REMOTE_COMMENT + "allow_remote_judge: true\n")
        code, out = self.main("show", "--repository-root", str(repo.root))
        self.assertEqual((code, out["data"]["allow_remote_judge"]), (0, True))
        self.assertTrue(settings_mod.remote_judge_consent(repo.root).value)

    def test_set_false_reports_the_change(self):
        repo = Repo(self, HEADER)
        self.main("set", "allow_remote_judge", "true", "--repository-root", str(repo.root))
        code, out = self.main("set", "allow_remote_judge", "false", "--repository-root", str(repo.root))
        self.assertEqual((code, out["data"]["previous"], out["data"]["value"], out["data"]["written"]), (0, True, False, True))
        self.assertEqual(repo.settings.read_text(encoding="utf-8"), HEADER + REMOTE_COMMENT + "allow_remote_judge: false\n")
        code, out = self.main("set", "allow_remote_judge", "false", "--repository-root", str(repo.root))
        self.assertEqual((code, out["data"]["written"], out["data"]["commit_paths"]), (0, False, []))

    def test_bad_arguments_are_validation_input(self):
        repo = Repo(self)
        for argv in (["set", "allow_remote_judge", "yes"], ["set", "allow_remote_judge", "True"],
                     ["set", "schema_version", "1"], ["set", "allow_remote_judge"], ["delete"]):
            with self.subTest(argv=argv):
                code, out = self.main(*argv, "--repository-root", str(repo.root))
                self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))
        self.assertFalse(repo.settings.exists())

    def test_set_value_refuses_an_unsettable_key(self):
        outcome = settings_mod.set_value(Repo(self).root, "schema_version", 2)
        self.assertEqual(outcome.error.code, "VALIDATION.INPUT")

    def test_a_malformed_file_is_never_overwritten(self):
        for text, code_expected in (("schema_version: [1\n", "SETTINGS.MALFORMED"),
                                    ("schema_version: 1\nfast: 1\n", "SETTINGS.UNKNOWN_KEY"),
                                    ("schema_version: 2\n", "SETTINGS.SCHEMA_VERSION"),
                                    ("schema_version: 1\nallow_remote_judge: 'no'\n", "SETTINGS.INVALID_REMOTE_JUDGE")):
            with self.subTest(text=text):
                repo = Repo(self, text)
                code, out = self.main("set", "allow_remote_judge", "true", "--repository-root", str(repo.root))
                self.assertEqual((code, out["error"]["code"]), (2, code_expected))
                self.assertEqual(repo.settings.read_text(encoding="utf-8"), text)

    def test_set_over_a_yaml_yes_writes_false_and_keeps_yes_as_true(self):
        repo = Repo(self, HEADER + "allow_remote_judge: yes\n")
        code, out = self.main("set", "allow_remote_judge", "true", "--repository-root", str(repo.root))
        self.assertEqual((code, out["data"]["previous"], out["data"]["written"]), (0, True, False))  # already true
        code, out = self.main("set", "allow_remote_judge", "false", "--repository-root", str(repo.root))
        self.assertEqual((code, out["data"]["previous"], out["data"]["value"], out["data"]["written"]), (0, True, False, True))
        self.assertEqual(repo.settings.read_text(encoding="utf-8"), HEADER + REMOTE_COMMENT + "allow_remote_judge: false\n")

    def test_missing_pyyaml_is_a_typed_error(self):
        repo = Repo(self)
        with mock.patch.dict(sys.modules, {"yaml": None}):
            code, out = self.main("set", "allow_remote_judge", "true", "--repository-root", str(repo.root))
        self.assertEqual((code, out["error"]["code"]), (2, "DEPENDENCY.PYYAML"))
        self.assertFalse(repo.settings.exists())

    def test_the_script_runs_end_to_end(self):
        repo = Repo(self)
        subprocess.run(["git", "init", "-q", str(repo.root)], check=False, capture_output=True)
        proc = subprocess.run([sys.executable, str(SETTINGS_SCRIPT), "set", "allow_remote_judge", "true",
                               "--repository-root", str(repo.root)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["data"]["written"])
        self.assertIn("allow_remote_judge: true\n", repo.settings.read_text(encoding="utf-8"))

    def test_schema_version_stays_one(self):
        self.assertEqual(settings_mod.SCHEMA_VERSION, 1)
        self.assertIn("allow_remote_judge", settings_mod.ALLOWED_KEYS)


class PromptAndDocsTests(unittest.TestCase):
    def test_no_shipped_file_names_a_bare_allow_remote_flag(self):
        for path in [*(p for p in sorted(PLUGIN.rglob("*")) if p.is_file() and "__pycache__" not in p.parts
                       and p.suffix in {".md", ".j2", ".py", ".yaml", ".json"}), ROOT / "README.md"]:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotRegex(path.read_text(encoding="utf-8"), r"--allow-remote(?!-judge)")

    def test_installer_skill_asks_once_and_never_infers(self):
        text = (PLUGIN / "skills" / "judge-jev-installer" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Otherwise ask the user once whether record text may be sent to TypeSafe (Jev)", text)
        self.assertIn("Never infer consent from earlier runs", text)


if __name__ == "__main__":
    unittest.main()
