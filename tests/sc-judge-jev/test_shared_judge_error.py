"""One JudgeError, defined in jev_errors: a graph-layer error reaches the CLI envelope as it was built."""
import tempfile
import unittest
from pathlib import Path

import jev_support  # noqa: F401  (puts the rendered scripts on sys.path)
import jev_errors  # noqa: E402
import jev_graph  # noqa: E402
import jev_judge as jj  # noqa: E402

from test_graph_tree import BRANCH_TTL  # noqa: E402
from test_jev_judge import run_cli  # noqa: E402


class SharedJudgeError(unittest.TestCase):
    def test_the_scripts_share_one_class(self):
        self.assertIs(jj.JudgeError, jev_errors.JudgeError)
        self.assertIs(jev_graph.JudgeError, jev_errors.JudgeError)

    def test_a_graph_error_reaches_the_cli_envelope_with_its_original_code(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "t.ttl"
            path.write_text(BRANCH_TTL.replace("jj:goto t:b:done", "jj:goto t:b:wave-1"), encoding="utf-8")  # a cycle: a SHACL violation
            graph_error = jev_graph.validate_tree(jev_graph.load_tree(str(path)).value).error
            code, out = run_cli(["validate", "--tree", str(path)])
        self.assertIsInstance(graph_error, jev_errors.JudgeError)
        self.assertEqual(graph_error.code, "QUALITY.TREE")
        self.assertEqual(code, 2)
        self.assertEqual((out["success"], out["error"]["code"], out["error"]["message"]), (False, "QUALITY.TREE", graph_error.message))
        self.assertEqual(out["error"]["suggested_action"], graph_error.action)
        self.assertEqual(out["data"], jj.redact_sensitive(graph_error.data))


if __name__ == "__main__":
    unittest.main()
