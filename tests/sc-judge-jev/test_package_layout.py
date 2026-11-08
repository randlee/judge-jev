from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "sc-judge-jev"


class MarketplacePackageLayoutTests(unittest.TestCase):
    def test_maintainer_tests_are_not_redistributed_with_the_plugin(self):
        test_directories = [path for path in PLUGIN.rglob("tests") if path.is_dir()]
        python_tests = list(PLUGIN.rglob("test_*.py"))

        self.assertEqual(test_directories, [])
        self.assertEqual(python_tests, [])


if __name__ == "__main__":
    unittest.main()
