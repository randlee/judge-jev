"""Environment configuration belongs to the shared wheel, not the plugin."""
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

    def test_only_shared_log_root_is_named_in_shipped_files(self):
        token = re.compile(r"\b(?:JUDGE_JEV|PLAN_ANCHOR)_[A-Z0-9_]+\b")
        found = {name for p in self.shipped_files() for name in token.findall(p.read_text(encoding="utf-8", errors="replace"))}
        self.assertEqual(found - {"JUDGE_JEV_LOG_ROOT"}, set())

    def found(self):
        read = re.compile(r"""(?:environ\.get|environ\[|getenv)\(?\s*["']([^"']+)["']""")
        found = {}
        for path in sorted([*PLUGIN.rglob("*.py"), *PLUGIN.rglob("*.py.j2")]):  # the scripts are *.py.j2 templates
            for name in read.findall(path.read_text(encoding="utf-8")):
                found.setdefault(name, []).append(path.relative_to(PLUGIN).as_posix())
        return found

    def test_only_os_user_is_read_from_the_environment(self):
        # USER is the operating system's login name, not plugin configuration.
        allowed = {"USER"}
        found = self.found()
        self.assertEqual(sorted(set(found) - allowed), [], found)

    @unittest.skipUnless(JUDGE_TEMPLATE.is_file(), "jev_judge.py.j2 is not in this tree yet")
    def test_credentials_are_left_to_the_shared_wheel(self):
        self.assertNotIn("TYPESAFE_API_KEY", self.found())


if __name__ == "__main__":
    unittest.main()
