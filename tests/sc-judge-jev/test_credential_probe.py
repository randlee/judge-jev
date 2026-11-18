"""Check the installed credential hints without reading a real key or keychain."""
import re
import tempfile
import unittest
from pathlib import Path

from child_support import run_child
from layout_support import SKILL_SRC, render_cli


class CredentialProbeTests(unittest.TestCase):
    def test_rendered_probes_agree_and_report_the_available_source(self):
        templates = (
            SKILL_SRC / "SKILL.md.j2",
            SKILL_SRC / "references" / "installation-and-troubleshooting.md.j2",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            probes = []
            for index, template in enumerate(templates):
                output = root / f"rendered-{index}.md"
                render_cli(template, output)
                match = re.search(r'^if \[ -f \.env \]; then\n.*?^fi$',
                                  output.read_text(encoding="utf-8"), re.M | re.S)
                self.assertIsNotNone(match, template)
                probes.append(match.group())
            self.assertEqual(probes[0], probes[1])

            cases = (
                (True, False, "repository .env present (key not verified)"),
                (True, True, "repository .env present (key not verified)"),
                (False, True, "process key set"),
                (False, False, "sc-agent may use the platform credential store"),
            )
            for dotenv, key, expected in cases:
                with self.subTest(dotenv=dotenv, key=key):
                    with tempfile.TemporaryDirectory(dir=root) as cwd:
                        if dotenv:
                            (Path(cwd) / ".env").write_text("", encoding="utf-8")
                        env = {"TYPESAFE_API_KEY": "test-key"} if key else {}
                        result = run_child(["sh", "-c", probes[0]], cwd=cwd, env=env,
                                           text=True, encoding="utf-8", check=True)
                        self.assertEqual(result.stdout.strip(), expected)
                        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
