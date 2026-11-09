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
        self.assertEqual(jj.check_api_key("").error.code, "AUTH.CREDENTIALS")
        self.assertEqual(jj.check_api_key("k"), Ok(None))

    def test_judge_error_is_a_value_not_an_exception(self):
        self.assertFalse(issubclass(jj.JudgeError, BaseException))
        e = jj.JudgeError("C.X", "msg", recoverable=True, action="act")
        self.assertEqual(str(e), "msg")
        self.assertEqual(jj.fail("C.X", "msg").error.to_json()["error"]["message"], "msg")


class JevPropagationTests(unittest.TestCase):
    """An Err from the transport travels into the batch line unchanged, with its attempt bookkeeping, and becomes one envelope in main."""

    def job(self):
        settings = jj.BatchSettings("plan", "m", 1, "p", 0.6, 1.0, 1, 24000, False)
        base = jj.load_question_set("plan").value
        line = {"item": {"id": "ex-42", "title": "", "text": "Sprint 2 copies the legacy runtime crates."},
                "anchor": {"id": "ANC-001", "statement": STATEMENT},
                "questions": [{"candidate_id": "cur", "questions": base.questions}]}
        return jj.batch_jobs(line, 1, settings, base.roles).value[0], settings

    def run_job(self, transport_result):
        job, settings = self.job()
        abort = jj._AbortFlag()
        sleeps = []
        with mock.patch.object(jj, "call_jev", return_value=transport_result) as called, mock.patch.object(jj, "_sleep", sleeps.append):
            line = jj.run_batch_job(job, settings, "k", None, abort)
        return line, called.call_count, sleeps, abort

    def test_non_transient_err_is_recorded_once(self):
        line, calls, sleeps, abort = self.run_job(Err(jj.JudgeError("JEV.VALIDATION", "Jev HTTP 422: bad", status=422)))
        self.assertEqual((line["ok"], line["error"]["code"], line["retry_count"], calls, sleeps, abort.is_set()),
                         (False, "JEV.VALIDATION", 0, 1, [], False))

    def test_abort_code_stops_the_batch(self):
        refused = jj.JudgeError("AUTH.CREDENTIALS", "Jev HTTP 401", status=401)
        line, calls, _, abort = self.run_job(Err(refused))
        self.assertEqual((line["error"]["code"], calls, abort.is_set(), abort.error), ("AUTH.CREDENTIALS", 1, True, refused))

    def test_transient_err_is_retried_once_then_recorded(self):
        down = jj.JudgeError("JEV.NETWORK", "down", recoverable=True)
        line, calls, sleeps, _ = self.run_job(Err(down))
        self.assertEqual((line["ok"], line["error"]["code"], calls, line["retry_count"], sleeps),
                         (False, "JEV.NETWORK", jj.BATCH_RETRIES + 1, jj.BATCH_RETRIES, [jj.RETRY_DELAYS[0]]))

    def test_invalid_ok_response_becomes_err(self):
        line, calls, _, _ = self.run_job(Ok({"answers": []}))
        self.assertEqual((line["ok"], line["error"]["code"], calls), (False, "JEV.RESPONSE_INVALID", 2))

    def test_valid_ok_response_is_the_line_answer(self):
        line, calls, _, _ = self.run_job(Ok({"model": "jev-x", "answers": plan_answers()}))
        self.assertEqual((line["ok"], line["verdict"], line["leaning"], line["model_answered"], calls), (True, "satisfied", "satisfied", "jev-x", 1))

    def run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = jj.main(argv)
        return code, json.loads(buf.getvalue())

    def test_main_emits_an_err_as_the_envelope_and_exits_2(self):
        code, out = self.run_main(["batch", "--input", "/nonexistent/in.jsonl", "--run-dir", "/nonexistent/runs"])
        self.assertEqual(code, 2)
        self.assertEqual(set(out), {"success", "data", "error"})
        self.assertEqual((out["success"], out["error"]["code"]), (False, "INPUT.MISSING"))

    def test_main_reports_an_unexpected_exception_as_script_internal(self):
        with mock.patch.object(jj, "read_request_lines", side_effect=RuntimeError("boom")):
            code, out = self.run_main(["batch", "--input", "x"])
        self.assertEqual((code, out["error"]["code"], out["error"]["message"]), (2, "SCRIPT.INTERNAL", "RuntimeError: boom"))


if __name__ == "__main__":
    unittest.main()
