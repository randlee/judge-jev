"""TYPESAFE_API_KEY is the plugin's only configuration variable.

The shipped tree reads no other environment variable as configuration, and
names no plugin-prefixed variable.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "sc-judge-jev"
JUDGE_TEMPLATE = PLUGIN / "install" / "templates" / "skills" / "judge-jev" / "scripts" / "jev_judge.py.j2"


class ShippedTreeNamesNoPluginVariable(unittest.TestCase):
    SHIPPED = (PLUGIN, ROOT / ".claude-plugin", ROOT / ".cursor-plugin", ROOT / ".agents", ROOT / "README.md")

    def shipped_files(self):
        for top in self.SHIPPED:
            if top.is_file():
                yield top
            else:
                yield from (p for p in sorted(top.rglob("*")) if p.is_file() and "__pycache__" not in p.parts)

    def test_no_plugin_prefix_in_shipped_files(self):
        hits = [p.relative_to(ROOT).as_posix() for p in self.shipped_files()
                if b"JUDGE_JEV_" in p.read_bytes() or b"PLAN_ANCHOR_" in p.read_bytes()]
        self.assertEqual(hits, [])

    def found(self):
        read = re.compile(r"""(?:environ\.get|environ\[|getenv)\(?\s*["']([^"']+)["']""")
        found = {}
        for path in sorted([*PLUGIN.rglob("*.py"), *PLUGIN.rglob("*.py.j2")]):  # the scripts are *.py.j2 templates
            for name in read.findall(path.read_text(encoding="utf-8")):
                found.setdefault(name, []).append(path.relative_to(PLUGIN).as_posix())
        return found

    def test_only_typesafe_key_is_read_from_the_environment(self):
        # USER is the operating system's login name, not plugin configuration.
        allowed = {"TYPESAFE_API_KEY", "USER"}
        found = self.found()
        self.assertEqual(sorted(set(found) - allowed), [], found)

    @unittest.skipUnless(JUDGE_TEMPLATE.is_file(), "jev_judge.py.j2 is not in this tree yet")
    def test_the_judge_reads_typesafe_key(self):
        self.assertIn("TYPESAFE_API_KEY", self.found())


if __name__ == "__main__":
    unittest.main()
