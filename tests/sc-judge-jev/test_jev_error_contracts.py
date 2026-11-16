"""Consumer boundary tests for shared result records and as-arrived batch persistence."""
import json
import unittest
from unittest import mock

from jev_support import SCRIPTS  # noqa: F401
import jev_judge as jj  # noqa: E402
import decidr_client  # noqa: E402
from test_jev_judge import plan_answers, request_line, wheel_record  # noqa: E402


class ConsumerErrorContracts(unittest.TestCase):
    def test_single_call_uses_result_api_and_default_credentials(self):
        response = {"model": "jev-x", "answers": plan_answers()}
        record = wheel_record((json.dumps({"response": response, "sends": 1}), None))
        with mock.patch.object(decidr_client, "call_result", return_value=record) as call:
            got = jj.call_jev({"model": "jev-latest", "state": {}, "questions": {}}, 12.5)
        self.assertIsInstance(got, jj.Ok)
        self.assertEqual(got.value, response)
        self.assertEqual(call.call_args.args[0], json.dumps({"model": "jev-latest", "state": {}, "questions": {}}))
        self.assertEqual(call.call_args.kwargs["project"], "judge-jev")
        self.assertEqual(call.call_args.kwargs["agent_role"], "judge")
        self.assertEqual(call.call_args.kwargs["abort_on"], frozenset({"auth"}))
        self.assertEqual(call.call_args.kwargs["timeout_secs"], 12.5)
        self.assertNotIn("category_codes", call.call_args.kwargs)
        for name in ("keyring_service", "keyring_account", "session_log", "cancel"):
            self.assertNotIn(name, call.call_args.kwargs)

    def test_single_call_attempt_count_comes_from_record(self):
        response = {"model": "jev-x", "answers": plan_answers()}
        record = wheel_record((json.dumps({"response": response, "sends": 3}), None))
        with mock.patch.object(decidr_client, "call_result", return_value=record):
            got = jj.call_jev({"model": "jev-latest", "state": {}, "questions": {}}, 12.5)
        self.assertEqual(got.value.sc_agent_sends, 3)

    def test_context_error_preserves_retryability_and_metadata(self):
        detail = {"id": "decision.context_exceeded", "category": "validation", "message": "oversized",
                  "sends": 3, "retry_after_ms": 500}
        record = wheel_record((json.dumps({"error": detail, "sends": 3}), "JEV.VALIDATION"))
        with mock.patch.object(decidr_client, "call_result", return_value=record):
            got = jj.call_jev({"model": "jev-latest", "state": {}, "questions": {}}, 30)
        self.assertEqual((got.error.code, got.error.retryable, got.error.attempts, got.error.retry_after_ms),
                         ("JEV.CONTEXT_EXCEEDED", True, 3, 500))

    def test_batch_uses_records_default_credentials_and_attempt_count(self):
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 42.0, 2, 24000, False)
        detail = {"id": "http.provider_busy", "category": "busy", "message": "busy", "sends": 4}
        record = wheel_record((json.dumps({"error": detail, "sends": 4}), "JEV.OVERLOADED"))
        log = mock.Mock()
        log.event.return_value = jj.Ok(None)

        def batch_result(_requests, **kwargs):
            kwargs["general_log"]({"action": "sc_decidr.error", "target": "sc_decidr",
                                   "correlation_id": "request-1",
                                   "fields": {"code": "JEV.OVERLOADED", "message": "busy"}})
            kwargs["on_result"](record)
            return {"ok": True, "value": [record], "position": None, "line": None, "attempts": None}

        with mock.patch.object(jj, "check_log_events", return_value=jj.Ok(None)), \
                mock.patch.object(jj, "log_result_line", return_value=jj.Ok(None)) as log_line, \
                mock.patch.object(decidr_client, "call_batch_results", side_effect=batch_result) as call:
            got = jj._live_batch_results([request_line()], settings, log, False)
        self.assertEqual((got.value[0]["error"]["code"], got.value[0]["retry_count"],
                          got.value[0]["attempts"]), ("JEV.OVERLOADED", 3, []))
        log_line.assert_not_called()
        log.event.assert_called_once_with("sc_decidr.error",
                                          {"sc_agent_target": "sc_decidr", "code": "JEV.OVERLOADED", "message": "busy"},
                                          correlation_id="request-1")
        self.assertNotIn("category_codes", call.call_args.kwargs)
        self.assertEqual(call.call_args.kwargs["project"], "judge-jev")
        self.assertEqual(call.call_args.kwargs["agent_role"], "quality")
        self.assertEqual(call.call_args.kwargs["timeout_secs"], 42.0)
        self.assertEqual(call.call_args.kwargs["workers"], 2)
        self.assertTrue(call.call_args.kwargs["general_log"])
        self.assertTrue(call.call_args.kwargs["on_result"])
        for name in ("keyring_service", "keyring_account", "session_log", "cancel"):
            self.assertNotIn(name, call.call_args.kwargs)

    def test_callback_persists_completion_order_and_returns_input_order(self):
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 42.0, 2, 24000, False)
        records = [wheel_record((json.dumps({"response": {"model": model, "answers": plan_answers()},
                                             "position": pos, "sends": 1}), None), pos)
                   for pos, model in enumerate(("first", "second"))]
        logged = []

        def batch_result(_requests, **kwargs):
            for record in reversed(records):
                kwargs["on_result"](record)
            return {"ok": True, "value": records, "position": None, "line": None, "attempts": None}

        def log_line(_log, line, _fields):
            logged.append(line["model_answered"])
            return jj.Ok(None)

        with mock.patch.object(jj, "check_log_events", return_value=jj.Ok(None)), \
                mock.patch.object(jj, "log_result_line", side_effect=log_line), \
                mock.patch.object(decidr_client, "call_batch_results", side_effect=batch_result):
            got = jj._live_batch_results([request_line("one"), request_line("two")], settings, mock.Mock(), False)
        self.assertEqual(logged, ["second", "first"])
        self.assertEqual([line["model_answered"] for line in got.value], ["first", "second"])

    def test_shared_invalid_result_is_typed(self):
        detail = jj.ClientError("DECIDR.INVALID_RESULT", "invalid JSON", action="Inspect the invalid result.")
        got = jj._judge_result({"ok": False, "error": detail, "attempts": None, "position": None, "line": None})
        self.assertEqual((got.error.code, got.error.retryable), ("DECIDR.INVALID_RESULT", False))


if __name__ == "__main__":
    unittest.main()
