"""CLI boundaries of every rendered script: usage errors are a VALIDATION.INPUT envelope on stdout, --help is text.

Ported from plan-anchor's tests/sc-plan-anchor/test_cli_boundaries.py (UsageErrorEnvelopeTests), plus
a check that every rendered script is free of template syntax and of the plan-anchor names it was
copied from.
"""
import json
import os
import re
import subprocess
import sys
import unittest

from jev_support import SCRIPTS, SKILL

CLEAN_ENV = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}


def run(script, *argv):
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), *argv], capture_output=True, text=True,
                          encoding="utf-8", env=CLEAN_ENV)
    return proc.returncode, proc.stdout, proc.stderr


class UsageErrorEnvelopeTests(unittest.TestCase):
    CASES = {
        "jev_judge.py": (["batch", "--no-such-flag"], ["frobnicate"], ["judge"], []),
        "judge_jev_settings.py": (["set", "plan_dir", "x"], ["frobnicate"], []),
    }

    def test_usage_errors_are_validation_input_on_stdout(self):
        for script, cases in self.CASES.items():
            for argv in cases:
                with self.subTest(script=script, argv=argv):
                    code, out, err = run(script, *argv)
                    self.assertEqual((code, err), (2, ""))
                    envelope = json.loads(out)
                    self.assertEqual((envelope["success"], envelope["data"], envelope["error"]["code"]),
                                     (False, None, "VALIDATION.INPUT"))
                    self.assertTrue(envelope["error"]["message"].startswith(script), envelope["error"]["message"])
                    self.assertIn("--help", envelope["error"]["suggested_action"])

    def test_help_still_prints_text_and_exits_zero(self):
        for script in self.CASES:
            with self.subTest(script=script):
                code, out, _ = run(script, "--help")
                self.assertEqual(code, 0)
                self.assertIn("usage:", out)


class RenderedTextTests(unittest.TestCase):
    def test_rendered_scripts_hold_no_template_syntax_or_plan_anchor_names(self):
        names = sorted(p.name for p in SCRIPTS.glob("*.py"))
        self.assertEqual(names, ["jev_definitions.py", "jev_errors.py", "jev_gate.py", "jev_graph.py", "jev_judge.py", "jev_ports.py", "jev_runs.py", "judge_jev_paths.py", "judge_jev_settings.py", "result.py"])
        for name in names:
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertIsNone(re.search(r"\{\{\s*\w|\{%-?\s*\w", text))
                # the one plan-anchor name kept on purpose: the shared credential store entry
                text = text.replace('CREDENTIAL_SERVICE = "plan-anchor"', "")
                self.assertIsNone(re.search(r"plan[-_]anchor", text, re.IGNORECASE))


    def test_rendered_jev_api_reference_names_only_the_kept_command(self):
        text = (SKILL / "references" / "jev-api.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\{\{\s*\w|\{%-?\s*\w", text))
        self.assertIsNone(re.search(r"plan[-_]anchor", text, re.IGNORECASE))
        self.assertIn("version: 0.0.0-test", text)
        for dropped in ("`judge`", "`tournament`", "`bead-batch`", "`rubric`", "`check-fixtures`", "`dedupe", "## Judging flags",
                        "## Attempt policy", "## Other Jev-backed subcommands"):
            self.assertNotIn(dropped, text)


if __name__ == "__main__":
    unittest.main()
