"""The installed scripts use the client rendered from the shared wheel."""
from pathlib import Path
import sys
import unittest
from unittest import mock

import jev_support  # noqa: F401
from child_support import run_child
import decidr_client
import jev_judge


class ConsumerAdoptionTests(unittest.TestCase):
    def test_scripts_import_without_a_result_module(self):
        code = ("import sys\n"
                f"sys.path.insert(0, {str(jev_support.SCRIPTS)!r})\n"
                "sys.modules['result'] = None\n"
                "import jev_judge, jev_graph, jev_runs, jev_definitions, judge_jev_settings\n"
                "assert jev_judge.decidr_client is sys.modules['decidr_client']\n")
        proc = run_child([sys.executable, "-c", code], text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_judge_imports_rendered_client(self):
        self.assertIs(jev_judge.decidr_client, decidr_client)
        self.assertEqual(decidr_client.SC_DECIDR_VERSION, jev_support.SC_DECIDR_VERSION)
        self.assertTrue(callable(decidr_client.extract))

    def test_missing_wheel_returns_actionable_shared_error(self):
        with mock.patch.dict(sys.modules, {"sc_agent": None}):
            result = decidr_client.extract("python", "source", "query")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "DEPENDENCY.SC_DECIDR")
        self.assertTrue(result.error.action)

    def test_sitr_extracts_real_source(self):
        source = Path(__file__).parent / "fixtures" / "sitr_match.rs"
        result = decidr_client.extract("rust", source.read_text(encoding="utf-8"), "(match_expression) @match")
        self.assertTrue(result.ok, result)
        self.assertTrue(result.value)

    def test_shared_error_preserves_message_and_action(self):
        error = decidr_client.wheel_error({"id": "test", "category": "network", "message": "controlled", "action": "retry"})
        self.assertEqual((error.code, error.message, error.action), ("DECIDR.NETWORK", "controlled", "retry"))


if __name__ == "__main__":
    unittest.main()
