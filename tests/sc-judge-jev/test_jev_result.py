"""Tests for the Result<T, E> helpers and how expected failures propagate through the scripts.

Ported from plan-anchor's tests/sc-plan-anchor/test_result.py. result.py is the shared discriminated
union (Ok / Err, ToolError, err). The scripts return Err for every expected failure; only their CLI
boundary turns an Err into a JSON envelope and an exit code. Standard library only.
"""
import contextlib
import dataclasses
import io
import json
import unittest
from unittest import mock

from jev_support import SCRIPTS  # noqa: F401 - renders the scripts and puts them on sys.path
import jev_judge as jj  # noqa: E402
import judge_jev_settings as settings_mod  # noqa: E402
import result  # noqa: E402
from result import Err, Ok, ToolError, err  # noqa: E402

from test_jev_judge import STATEMENT, plan_answers  # noqa: E402


class ResultHelperTests(unittest.TestCase):
    def test_ok_and_err_are_discriminated_by_the_ok_literal(self):
        self.assertIs(Ok(1).ok, True)
        self.assertIs(Err("x").ok, False)
        self.assertEqual(Ok(1).value, 1)
        self.assertEqual(Err("x").error, "x")
        self.assertNotIsInstance(Ok(1), Err)
        self.assertNotIsInstance(Err("x"), Ok)

    def test_variants_are_frozen_value_objects(self):
        self.assertEqual(Ok([1]), Ok([1]))
        self.assertNotEqual(Ok(1), Err(1))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            Ok(1).value = 2
        with self.assertRaises(TypeError):
            Ok(1, ok=False)  # the discriminant is not settable

    def test_tool_error_envelope_and_err_helper(self):
        made = err("CODE.X", "went wrong", "do this", {"k": 1})
        self.assertIsInstance(made, Err)
        self.assertEqual(made.error, ToolError("CODE.X", "went wrong", "do this", {"k": 1}))
        self.assertEqual(list(made.error.to_json().items()),
                         [("code", "CODE.X"), ("message", "went wrong"), ("recoverable", False), ("suggested_action", "do this")])
        self.assertIsNone(err("C", "m").error.to_json()["suggested_action"])

    def test_scripts_share_one_result_module(self):
        for module in (settings_mod, jj):
            self.assertIs(module.Ok, result.Ok)
            self.assertIs(module.Err, result.Err)

    def test_run_main_turns_an_interrupt_into_the_canceled_envelope(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = result.run_main(mock.Mock(side_effect=KeyboardInterrupt))
        self.assertEqual(code, result.CANCELED_EXIT)
        self.assertEqual(json.loads(buf.getvalue()), result.canceled_envelope())


class ScriptErrValueTests(unittest.TestCase):
    """Expected failures come back as Err values, not exceptions."""

    def test_jev_judge(self):
        missing = jj.load_json("/nonexistent/x.json", "thing")
        self.assertEqual((missing.error.code, missing.error.message), ("INPUT.MISSING", "thing not found: '/nonexistent/x.json'"))
        self.assertFalse(hasattr(jj, "check_api_key"))

    def test_judge_error_is_a_value_not_an_exception(self):
        self.assertFalse(issubclass(jj.JudgeError, BaseException))
        e = jj.JudgeError("C.X", "msg", recoverable=True, action="act")
        self.assertEqual(str(e), "msg")
        self.assertEqual(jj.fail("C.X", "msg").error.to_json()["error"]["message"], "msg")


class JevPropagationTests(unittest.TestCase):
    """Live wheel failures map to one consumer error; no consumer retry loop exists."""

    def test_wheel_failure_maps_to_nonrecoverable_consumer_error(self):
        error = jj.sc_agent_error({"id": "http.network", "message": "connection reset",
                                   "cause": {"id": "io.error", "message": "reset"}})
        self.assertEqual((error.code, error.recoverable), ("JEV.NETWORK", False))
        self.assertEqual(error.action, "")

    def test_main_emits_an_err_as_the_envelope_and_exits_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = jj.main(["batch", "--input", "/nonexistent/in.jsonl", "--run-dir", "/nonexistent/runs"])
        self.assertEqual(code, 2)
        self.assertEqual(set(json.loads(buf.getvalue())), {"success", "data", "error"})
        self.assertEqual(json.loads(buf.getvalue())["error"]["code"], "INPUT.MISSING")

    def test_main_reports_an_unexpected_exception_as_script_internal(self):
        buf = io.StringIO()
        with mock.patch.object(jj, "read_request_lines", side_effect=RuntimeError("boom")), contextlib.redirect_stdout(buf):
            code = jj.main(["batch", "--input", "x"])
        envelope = json.loads(buf.getvalue())
        self.assertEqual((code, envelope["error"]["code"], envelope["error"]["message"]),
                         (2, "SCRIPT.INTERNAL", "RuntimeError: boom"))


if __name__ == "__main__":
    unittest.main()
