"""SKILL.md Step 1, run as written: the consent check reports a settings error instead of null, and RAPTOR is set and
checked before it is used.

The commands are taken from the rendered SKILL.md and run in a shell. The settings command's ``uv run -q --no-project
--with pyyaml python`` prefix is replaced by this interpreter (which has PyYAML), so the test needs no network; the jq
filter and the settings script run unchanged.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from layout_support import rendered_skill

SKILL = rendered_skill()

UV_PREFIX = "uv run -q --no-project --with pyyaml python"


def step1_block() -> str:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    section = text[text.index("## Step 1"):text.index("## Step 2")]
    return re.search(r"```bash\n(.*?)```", section, re.S).group(1)


def command(block: str, start: str) -> str:
    """The command that starts with ``start``, with its backslash continuation lines joined."""
    lines = block.splitlines()
    i = next(n for n, line in enumerate(lines) if line.startswith(start))
    out = [lines[i]]
    while out[-1].rstrip().endswith("\\"):
        i += 1
        out.append(lines[i])
    return "\n".join(out).replace("<this skill's directory>", str(SKILL))


def sh(script: str, cwd: Path, env: dict) -> str:
    proc = subprocess.run(["bash", "-c", script], cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8")
    return proc.stdout.strip()


@unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "needs jq and bash on PATH, as SKILL.md Step 1 does")
class Step1(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp = Path(td.name).resolve()
        self.block = step1_block()
        self.env = {k: v for k, v in os.environ.items() if k not in ("RAPTOR", "TYPESAFE_API_KEY")}
        self.env["HOME"] = str(self.tmp / "home")

    def consent(self, cwd: Path) -> str:
        cmd = command(self.block, "uv run -q --no-project --with pyyaml python")
        self.assertIn(UV_PREFIX, cmd)
        return sh(cmd.replace(UV_PREFIX, f'"{sys.executable}"'), cwd, self.env)

    def test_a_settings_error_prints_an_error_line_not_null(self):
        outside = self.tmp / "not-a-repo"
        outside.mkdir()
        self.assertRegex(self.consent(outside), r"^ERROR REPO\.NOT_FOUND: ")

    def test_the_recorded_answer_or_null_when_never_asked(self):
        repo = self.tmp / "repo"
        (repo / ".git").mkdir(parents=True)
        self.assertEqual(self.consent(repo), "null")
        settings = repo / ".sc" / "judge-jev" / "settings.yaml"
        settings.parent.mkdir(parents=True)
        settings.write_text("schema_version: 1\nallow_remote_judge: false\n", encoding="utf-8")
        self.assertEqual(self.consent(repo), "false")

    def test_the_skill_says_an_error_line_is_not_an_answer(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("An `ERROR` line means the settings could not be read: it is not an answer", text)

    def raptor(self, raptor=None) -> str:
        env = dict(self.env, **({"RAPTOR": str(raptor)} if raptor else {}))
        script = command(self.block, "RAPTOR=") + "\n" + command(self.block, 'test -x "$RAPTOR')
        return sh(script, self.tmp, env)

    def test_raptor_defaults_under_home_and_is_reported_missing(self):
        self.assertEqual(self.raptor(), f"raptor missing at {self.tmp / 'home' / '.local' / 'share' / 'raptor'}")

    def test_raptor_ok_only_with_its_venv_and_extract_script(self):
        raptor = self.tmp / "raptor"
        (raptor / "scripts").mkdir(parents=True)
        (raptor / "scripts" / "extract.py").write_text("", encoding="utf-8")
        self.assertEqual(self.raptor(raptor), f"raptor missing at {raptor}")
        python = raptor / ".venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.write_text("#!/bin/sh\n", encoding="utf-8")
        python.chmod(0o755)
        self.assertEqual(self.raptor(raptor), "raptor ok")

    def test_raptor_is_set_before_any_use(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(text.index('RAPTOR="${RAPTOR:-'), text.index('"$RAPTOR'))


if __name__ == "__main__":
    unittest.main()
