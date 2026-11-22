"""Consumer boundary tests for shared result records and as-arrived batch persistence."""
import json
import unittest
from unittest import mock

from jev_support import SCRIPTS  # noqa: F401
import jev_judge as jj  # noqa: E402
import decidr_client  # noqa: E402
from test_jev_judge import plan_answers, request_line, wheel_record  # noqa: E402


class ConsumerErrorContracts(unittest.TestCase):
    def test_batch_uses_records_default_credentials_and_attempt_count(self):
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 42.0, 2, 24000, False)
        detail = {"id": "http.provider_busy", "category": "busy", "message": "busy", "sends": 4}
        record = wheel_record((json.dumps({"error": detail, "sends": 4}), "DECIDR.OVERLOADED"))
        log = mock.Mock()
        log.event.return_value = jj.Ok(None)

        def batch_result(_requests, **kwargs):
            self.assertIs(kwargs["general_log"], log)
            kwargs["on_result"](record)
            return {"ok": True, "value": [record], "position": None, "line": None, "attempts": None}

        with                mock.patch.object(jj, "log_result_line", return_value=jj.Ok(None)) as log_line, \
                mock.patch.object(decidr_client, "call_batch_results", side_effect=batch_result) as call:
            got = jj._live_batch_results([request_line()], settings, log, False)
        self.assertEqual((got.value[0]["error"]["code"], got.value[0]["retry_count"],
                          got.value[0]["attempts"]), ("DECIDR.OVERLOADED", 3, []))
        log_line.assert_called_once_with(log, got.value[0], {})
        log.event.assert_not_called()  # Native general events are not forwarded through Python.

        self.assertNotIn("category_codes", call.call_args.kwargs)
        self.assertNotIn("project", call.call_args.kwargs)
        self.assertNotIn("agent_role", call.call_args.kwargs)
        self.assertEqual(call.call_args.kwargs["timeout_secs"], 42.0)
        self.assertEqual(call.call_args.kwargs["workers"], 2)
        self.assertIs(call.call_args.kwargs["general_log"], log)
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

        with                mock.patch.object(jj, "log_result_line", side_effect=log_line), \
                mock.patch.object(decidr_client, "call_batch_results", side_effect=batch_result):
            got = jj._live_batch_results([request_line("one"), request_line("two")], settings, mock.Mock(), False)
        self.assertEqual(logged, ["second", "first"])
        self.assertEqual([line["model_answered"] for line in got.value], ["first", "second"])



if __name__ == "__main__":
    unittest.main()
