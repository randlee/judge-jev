"""The exit-code convention, end to end through each real CLI process.

A tool failure returns an error in the exit code; a call which ran properly and
returned a negative result still ran properly. So: exit 0 with the outcome in
``data`` (negative outcomes included), exit 2 with the typed error envelope when
the command could not do its job, and no exit 1 anywhere. Every case runs the
script as a subprocess, offline, with no TypeSafe key in the environment.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "sc-judge-jev"
from layout_support import SCRIPTS  # noqa: E402 - the scripts as installed
ERROR_KEYS = {"code", "message", "recoverable", "suggested_action"}


def clean_env():
    keep = ("PATH", "HOME", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP", "PYTHONPATH")
    # An explicitly empty environment key fails closed before native-store fallback.
    return {**{k: os.environ[k] for k in keep if k in os.environ}, "TYPESAFE_API_KEY": ""}


class ConventionCase(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.d = Path(self.td.name).resolve()
        self.addCleanup(self.td.cleanup)

    def run_script(self, script, *argv):
        proc = subprocess.run([sys.executable, str(script), *argv], cwd=str(self.d), env=clean_env(),
                              capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(proc.returncode, 1, f"{script.name} {argv} exited 1: {proc.stdout}{proc.stderr}")
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"{script.name} {argv} printed no JSON envelope: {proc.stdout!r} {proc.stderr!r}")
        return proc.returncode, out

    def ran(self, script, *argv):
        """Exit 0 and success true: the command ran; returns data for the outcome assertions."""
        code, out = self.run_script(script, *argv)
        self.assertEqual((code, out["success"], out["error"]), (0, True, None), out)
        return out["data"]

    def failed(self, script, *argv, code=None, data_none=True):
        """Exit 2 and the typed error envelope: the command could not do its job."""
        rc, out = self.run_script(script, *argv)
        self.assertEqual((rc, out["success"]), (2, False), out)
        self.assertEqual(set(out["error"]), ERROR_KEYS)
        if data_none:
            self.assertIsNone(out["data"])
        if code is not None:
            self.assertEqual(out["error"]["code"], code)
        return out["error"]


class OtherScripts(ConventionCase):
    def test_settings(self):
        script = SCRIPTS / "judge_jev_settings.py"
        subprocess.run(["git", "init", "-q", str(self.d)], check=True)
        try:
            import yaml  # noqa: F401
        except ImportError:  # the settings script needs PyYAML; its absence is a could-not-run error
            self.failed(script, "show", code="DEPENDENCY.PYYAML")
            return
        self.assertIsNone(self.ran(script, "show")["allow_remote_judge"])  # never asked: a negative answer, exit 0
        self.failed(script, "set", "allow_remote_judge", "maybe")

    def test_installer(self):
        self.failed(PLUGIN / "install.py", "--dest", str(self.d), "--target", "zz", code="VALIDATION.INPUT")

    def test_installer_status_of_an_empty_folder_is_a_negative_answer(self):
        self.assertEqual(self.ran(PLUGIN / "install.py", "--dest", str(self.d), "--status")["state"], "not_installed")


SHIPPED_TEXT = ("*.md", "*.j2", "*.yaml", "*.json")
EXIT_ONE = re.compile(r"\bexit(?:s|ed|ing)?\s+(?:code\s+|status\s+)?1\b|\bexit\s+\$\?", re.IGNORECASE)


class NoExitOneInShippedText(unittest.TestCase):
    def test_no_prompt_or_reference_says_exit_1(self):
        files = [ROOT / "README.md"]
        for pattern in SHIPPED_TEXT:
            # Script templates (*.py.j2) are code: their docstrings state the convention
            # ("There is no exit 1"); prompts must not mention it.
            files.extend(p for p in PLUGIN.rglob(pattern) if p.is_file() and not p.name.endswith(".py.j2"))
        self.assertGreater(len(files), 10)
        hits = [f"{p.relative_to(ROOT)}:{n}: {line.strip()}"
                for p in files for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                if EXIT_ONE.search(line)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
