"""Judge-jev preserves sc-agent's typed error and retry metadata through its public consumer."""
import json
import unittest
from unittest import mock

from jev_support import SCRIPTS  # noqa: F401 - renders the scripts and puts them on sys.path
import jev_judge as jj  # noqa: E402
import decidr_client  # noqa: E402
from test_jev_judge import plan_answers, request_line  # noqa: E402


class ConsumerErrorContracts(unittest.TestCase):
    def setUp(self):
        self.cancel = mock.Mock()

    def test_single_call_uses_public_client_and_default_sc_agent_credentials(self):
        response = {"model": "jev-x", "answers": plan_answers()}
        wire = json.dumps({"response": response})
        with mock.patch.object(jj, "_new_cancel_token", return_value=self.cancel), \
                mock.patch.object(decidr_client, "call", return_value=(wire, None)) as call:
            got = jj.call_jev({"model": "jev-latest", "state": {}, "questions": {}}, 12.5)
        self.assertIsInstance(got, jj.Ok)
        self.assertEqual(got.value, response)
        self.assertEqual(call.call_args.args[0], json.dumps({"model": "jev-latest", "state": {}, "questions": {}}))
        self.assertEqual(call.call_args.kwargs["project"], "judge-jev")
        self.assertEqual(call.call_args.kwargs["agent_role"], "judge")
        self.assertEqual(call.call_args.kwargs["abort_on"], frozenset({"auth"}))
        self.assertEqual(call.call_args.kwargs["timeout_secs"], 12.5)
        self.assertNotIn("keyring_service", call.call_args.kwargs)
        self.assertNotIn("keyring_account", call.call_args.kwargs)
        self.assertTrue(call.call_args.kwargs["session_log"])

    def test_single_call_reads_success_send_count_from_session_row(self):
        response = {"model": "jev-x", "answers": plan_answers()}
        wire = json.dumps({"response": response})

        def wheel_call(_request, **kwargs):
            kwargs["session_log"]({"action": "session.row", "fields": {"position": 0, "sends": 3}})
            return wire, None

        with mock.patch.object(jj, "_new_cancel_token", return_value=self.cancel), \
                mock.patch.object(decidr_client, "call", side_effect=wheel_call):
            got = jj.call_jev({"model": "jev-latest", "state": {}, "questions": {}}, 12.5)
        self.assertIsInstance(got, jj.Ok)
        self.assertEqual(got.value.sc_agent_sends, 3)

    def test_context_error_uses_decision_identifier_and_attempt_metadata(self):
        detail = {"id": "decision.context_exceeded", "category": "validation", "message": "oversized",
                  "attempts": 3, "retry_after_ms": 500}
        with mock.patch.object(jj, "_new_cancel_token", return_value=self.cancel), \
                mock.patch.object(decidr_client, "call", return_value=(json.dumps({"error": detail}), "JEV.VALIDATION")):
            got = jj.call_jev({"model": "jev-latest", "state": {}, "questions": {}}, 30)
        self.assertIsInstance(got, jj.Err)
        self.assertEqual((got.error.code, got.error.recoverable, got.error.meta["attempts"], got.error.retry_after),
                         ("JEV.CONTEXT_EXCEEDED", True, 3, 0.5))

    def test_batch_uses_public_client_and_preserves_error_attempts(self):
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 42.0, 2, 24000, False)
        detail = {"id": "http.provider_busy", "category": "busy", "message": "busy", "attempts": 4}
        result = (json.dumps({"error": detail}), "JEV.OVERLOADED")
        log = mock.Mock()
        with mock.patch.object(jj, "check_log_events", return_value=jj.Ok(None)), \
                mock.patch.object(jj, "_new_cancel_token", return_value=self.cancel), \
                mock.patch.object(jj, "log_result_line", return_value=jj.Ok(None)), \
                mock.patch.object(decidr_client, "call_batch", return_value=[result]) as call:
            got = jj._live_batch_results([request_line()], settings, log, False)
        self.assertIsInstance(got, jj.Ok)
        line, = got.value
        self.assertEqual((line["error"]["code"], line["retry_count"], line["attempts"][-1]["attempt"]),
                         ("JEV.OVERLOADED", 3, 4))
        self.assertEqual(call.call_args.kwargs["project"], "judge-jev")
        self.assertEqual(call.call_args.kwargs["agent_role"], "quality")
        self.assertEqual(call.call_args.kwargs["timeout_secs"], 42.0)
        self.assertEqual(call.call_args.kwargs["workers"], 2)
        self.assertTrue(call.call_args.kwargs["general_log"])
        self.assertTrue(call.call_args.kwargs["session_log"])
        self.assertNotIn("keyring_service", call.call_args.kwargs)
        self.assertNotIn("keyring_account", call.call_args.kwargs)

    def test_batch_success_uses_send_count_from_session_row(self):
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 42.0, 2, 24000, False)
        response = {"model": "jev-x", "answers": plan_answers()}
        log = mock.Mock()

        def wheel_batch(_requests, **kwargs):
            kwargs["session_log"]({"action": "session.row", "fields": {"position": 0, "sends": 3}})
            kwargs["general_log"]({"action": "http.send", "target": "sc_agent.http", "fields": {"status": 200}})
            return [(json.dumps({"response": response}), None)]

        with mock.patch.object(jj, "check_log_events", return_value=jj.Ok(None)), \
                mock.patch.object(jj, "_new_cancel_token", return_value=self.cancel), \
                mock.patch.object(jj, "log_result_line", return_value=jj.Ok(None)), \
                mock.patch.object(decidr_client, "call_batch", side_effect=wheel_batch):
            got = jj._live_batch_results([request_line()], settings, log, False)
        self.assertIsInstance(got, jj.Ok)
        line, = got.value
        self.assertEqual((line["retry_count"], line["attempts"]),
                         (2, [{"attempt": 1, "ok": False}, {"attempt": 2, "ok": False},
                              {"attempt": 3, "ok": True}]))
        log.event.assert_called_once_with("http.send", {"sc_agent_target": "sc_agent.http", "status": 200},
                                          correlation_id=None)

    def test_malformed_result_is_typed(self):
        got = jj._decode_wheel_result("not-json", None)
        self.assertEqual((got.error.code, got.error.recoverable), ("JEV.RESPONSE_INVALID", True))


if __name__ == "__main__":
    unittest.main()
