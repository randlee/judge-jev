"""judge-jev turns script failures into typed public envelopes."""
import contextlib
import io
import json
import unittest
from unittest import mock

import jev_support  # noqa: F401
import jev_judge as jj


class ScriptErrors(unittest.TestCase):
    def test_missing_input_is_a_typed_value(self):
        missing = jj.load_json("/nonexistent/x.json", "thing")
        self.assertEqual((missing.error.code, missing.error.message), ("INPUT.MISSING", "thing not found: '/nonexistent/x.json'"))

    def test_shared_error_is_carried_in_result_and_can_be_raised(self):
        error = jj.ClientError("C.X", "msg", retryable=True, action="act")
        self.assertIsInstance(error, BaseException)
        self.assertEqual((str(error), jj.fail("C.X", "msg").error.to_json()["error"]["message"]), ("msg", "msg"))

    def run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = jj.main(argv)
        return code, json.loads(buf.getvalue())

    def test_main_emits_an_err_as_the_envelope_and_exits_2(self):
        code, out = self.run_main(["batch", "--input", "/nonexistent/in.jsonl"])
        self.assertEqual((code, set(out), out["success"], out["error"]["code"]), (2, {"success", "data", "error"}, False, "INPUT.MISSING"))

    def test_main_reports_an_unexpected_exception_as_script_internal(self):
        with mock.patch.object(jj, "read_request_lines", side_effect=RuntimeError("boom")):
            code, out = self.run_main(["batch", "--input", "x"])
        self.assertEqual((code, out["error"]["code"], out["error"]["message"]), (2, "SCRIPT.INTERNAL", "RuntimeError: boom"))
