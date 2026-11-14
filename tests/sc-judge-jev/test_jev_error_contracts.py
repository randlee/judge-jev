"""Consumer mappings for the released sc-decidr typed error chain."""
import json
import tempfile
import types
from pathlib import Path
import unittest
from unittest import mock

from jev_support import SCRIPTS  # noqa: F401
import jev_judge as jj


class ScDecidrErrorContracts(unittest.TestCase):
    def test_provider_error_ids_map_to_jev_contracts(self):
        cases = (
            ({"id": "http.provider_busy", "status": 429, "message": "busy"}, "JEV.RATE_LIMITED"),
            ({"id": "http.provider_busy", "status": 529, "message": "busy"}, "JEV.OVERLOADED"),
            ({"id": "http.network", "message": "offline"}, "JEV.NETWORK"),
            ({"id": "decision.response_parse", "message": "invalid"}, "JEV.RESPONSE_INVALID"),
            ({"id": "decision.api_validation", "message": "invalid request"}, "JEV.VALIDATION"),
            ({"id": "secrets.key_missing", "message": "missing"}, "AUTH.CREDENTIALS"),
        )
        for detail, expected in cases:
            with self.subTest(id=detail["id"], status=detail.get("status")):
                error = jj.sc_agent_error(detail)
                self.assertEqual(error.code, expected)
                self.assertFalse(error.recoverable)

    def test_remaining_final_result_mappings_keep_the_native_chain(self):
        base = jj.load_question_set("plan").value
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        request = {"item": {"id": "item", "title": "", "text": "record"},
                   "questions": [{"candidate_id": "cur", "questions": base.questions}]}
        job = jj.batch_jobs(request, 1, settings, base.roles).value[0]
        cases = (
            ({"id": "http.quota_exhausted", "message": "quota exhausted"}, "JEV.RATE_LIMITED"),
            ({"id": "decision.api_status", "status": 502, "message": "gateway failed"}, "JEV.HTTP"),
            ({"id": "http.response_too_large", "message": "response exceeded its bound"}, "JEV.RESPONSE_INVALID"),
            ({"id": "decision.schema_mismatch", "message": "wrong answer shape"}, "JEV.RESPONSE_INVALID"),
            ({"id": "decision.cancelled", "message": "cancelled"}, "CANCELED"),
            # Stable observed IDs with no specialized consumer mapping retain
            # JEV.HTTP. Future unknown IDs remain JEV.UNMAPPED (f-n2).
            ({"id": "decidr.decision", "message": "backend failed", "cause": {
                "id": "decision.backend", "message": "wrapped", "cause": {
                    "id": "llm.api_status", "message": "HTTP 502"}}}, "JEV.HTTP"),
            # Message prose cannot restore the removed status-scraping fallback.
            ({"id": "http.provider_busy", "message": "HTTP 429"}, "JEV.UNMAPPED"),
        )
        for detail, expected in cases:
            with self.subTest(detail=detail):
                line = jj._sc_agent_result(job, settings, {"position": 0, "error": detail})
                self.assertEqual((line["ok"], line["error"]["code"], line["retry_count"]), (False, expected, 0))
                self.assertEqual(line["error"]["detail"], detail)
                self.assertEqual(len(line["attempts"]), 1)
                self.assertEqual(line["attempts"][0]["error"]["code"], expected)
                self.assertEqual(line["error"]["recoverable"], expected == "CANCELED")
                self.assertEqual(line["attempts"][0]["error"]["recoverable"], expected == "CANCELED")

    def test_causal_detail_is_retained_on_result_line(self):
        base = jj.load_question_set("plan").value
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        request = {"item": {"id": "item", "title": "", "text": "record"},
                   "anchor": {"id": "ANC-001", "statement": "requirement"},
                   "questions": [{"candidate_id": "cur", "questions": base.questions}]}
        job = jj.batch_jobs(request, 1, settings, base.roles).value[0]
        detail = {"id": "http.network", "message": "request failed", "cause": {"id": "io.error", "message": "reset"}}
        line = jj._sc_agent_result(job, settings, {"position": 0, "error": detail})
        self.assertEqual(line["error"]["detail"], detail)
        self.assertEqual(line["error"]["code"], "JEV.NETWORK")
        self.assertEqual(line["retry_count"], 0)


class OfflineFinalResults(unittest.TestCase):
    def setUp(self):
        base = jj.load_question_set("plan").value
        self.settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        request = {"item": {"id": "item", "title": "", "text": "record"},
                   "questions": [{"candidate_id": "cur", "questions": base.questions}]}
        self.job = jj.batch_jobs(request, 1, self.settings, base.roles).value[0]
        self.answers = jj.worst_answers(base.questions)

    def test_an_error_then_answer_stops_after_the_first_fixture_entry(self):
        fixture = {"*": [{"__error__": "JEV.NETWORK"}, self.answers]}
        with mock.patch.object(jj, "_fixture_result", wraps=jj._fixture_result) as read, \
                mock.patch.object(jj, "sc_agent_module", side_effect=AssertionError("offline fixture contacted wheel")):
            line = jj.run_batch_job(self.job, self.settings, fixture, jj._AbortFlag())
        read.assert_called_once_with(self.job, fixture)
        self.assertEqual((line["ok"], line["retry_count"], line["error"]["code"]), (False, 0, "JEV.NETWORK"))
        self.assertEqual(len(line["attempts"]), 1)
        self.assertFalse(line["error"]["recoverable"])
        self.assertIsNone(line["answers"])

    def test_native_fixture_errors_use_the_same_final_wheel_mapping(self):
        for native, legacy in (("http.network", "JEV.NETWORK"), ("http.provider_busy", "JEV.UNMAPPED"),
                               ("decision.response_parse", "JEV.RESPONSE_INVALID"),
                               ("secrets.key_missing", "AUTH.CREDENTIALS")):
            with self.subTest(native=native):
                with mock.patch.object(jj, "sc_agent_error", wraps=jj.sc_agent_error) as mapped:
                    line = jj.run_batch_job(self.job, self.settings, {"*": {"__error__": native}}, jj._AbortFlag())
                mapped.assert_called_once_with({"id": native, "message": f"fixture failure {native}"})
                self.assertEqual((line["error"]["code"], line["retry_count"], len(line["attempts"])), (legacy, 0, 1))
                self.assertFalse(line["error"]["recoverable"])

    def test_legacy_codes_keep_their_outward_names_without_retrying(self):
        for code in ("JEV.RATE_LIMITED", "JEV.OVERLOADED", "JEV.NETWORK", "JEV.RESPONSE_INVALID",
                     "JEV.VALIDATION", "AUTH.CREDENTIALS", "CANCELED", "CUSTOM.FIXTURE"):
            with self.subTest(code=code):
                line = jj.run_batch_job(self.job, self.settings, {"*": {"__error__": code}}, jj._AbortFlag())
                self.assertEqual((line["error"]["code"], line["retry_count"], len(line["attempts"])), (code, 0, 1))
                self.assertEqual(line["error"]["recoverable"], code == "CANCELED")
                self.assertEqual(line["attempts"][0]["error"]["recoverable"], code == "CANCELED")

    def test_direct_and_wrapped_native_cancellation_are_recoverable_without_retry(self):
        cancellation = {"id": "decision.cancelled", "message": "cancelled", "recovery": "Submit a new request."}
        for detail in (cancellation, {"id": "decidr.decision", "message": "wrapped", "cause": cancellation}):
            with self.subTest(detail=detail):
                error = jj.sc_agent_error(detail)
                self.assertEqual((error.code, error.recoverable), ("CANCELED", True))
                line = jj._sc_agent_result(self.job, self.settings, {"position": 0, "error": detail})
                self.assertEqual(line["error"]["detail"], detail)
                self.assertTrue(line["error"]["recoverable"])
                self.assertEqual((line["retry_count"], len(line["attempts"])), (0, 1))
                self.assertTrue(line["attempts"][0]["error"]["recoverable"])

    def test_credential_abort_and_dry_run_do_not_consume_a_later_fixture(self):
        abort = jj._AbortFlag()
        first = jj.run_batch_job(self.job, self.settings, {"*": {"__error__": "AUTH.CREDENTIALS"}}, abort)
        self.assertEqual(first["error"]["code"], "AUTH.CREDENTIALS")
        with mock.patch.object(jj, "_fixture_result", side_effect=AssertionError("fixture consumed after abort")):
            later = jj.run_batch_job(self.job, self.settings, {"*": self.answers}, abort)
            dry = jj.run_batch_job(self.job, self.settings._replace(dry_run=True), {"*": self.answers}, jj._AbortFlag())
        self.assertEqual((later["ok"], later["retry_count"], later["error"]["code"]), (False, 0, "AUTH.CREDENTIALS"))
        self.assertEqual((dry["dry_run"], dry["attempts"], dry["retry_count"]), (True, [], 0))


class StructuredErrorMapping(unittest.TestCase):
    def test_every_pinned_owned_error_id_has_an_explicit_mapping(self):
        pinned = json.loads((Path(__file__).parent / "fixtures" / "sc-decidr-0.1.0-error-ids.json").read_text())
        self.assertEqual(pinned["source_commit"], "7afe38348fd736bcb6a0cfb632c25c7c20e60327")
        for identity in pinned["ids"]:
            with self.subTest(identity=identity):
                status = 429 if identity == "http.provider_busy" else 500
                code = jj.sc_agent_error({"id": identity, "status": status, "message": "wording may change"}).code
                self.assertNotEqual(code, "JEV.UNMAPPED", f"unmapped published ID from {pinned['ids'][identity]}")

    def test_only_the_matching_nodes_structured_status_controls_classification(self):
        cases = (
            ({"id": "http.provider_busy", "status": 429, "message": "HTTP 529"}, "JEV.RATE_LIMITED"),
            ({"id": "http.provider_busy", "status": 503, "message": "HTTP 429"}, "JEV.OVERLOADED"),
            ({"id": "http.provider_busy", "status": 529, "message": "HTTP 401"}, "JEV.OVERLOADED"),
            ({"id": "decision.api_status", "status": 401, "message": "HTTP 422"}, "AUTH.CREDENTIALS"),
            ({"id": "decision.api_status", "status": 422, "message": "HTTP 401"}, "JEV.VALIDATION"),
            ({"id": "decision.api_status", "status": 500, "message": "HTTP 401"}, "JEV.HTTP"),
            ({"id": "http.network", "message": "HTTP 401"}, "JEV.NETWORK"),
            ({"id": "log.rows_lost", "message": "HTTP 401"}, "JEV.HTTP"),
            ({"id": "vendor.new", "status": 401, "message": "HTTP 401"}, "JEV.UNMAPPED"),
            ({"id": "secrets.future_error", "message": "credential missing"}, "JEV.UNMAPPED"),
            ({"id": "http.provider_busy", "message": "HTTP 429"}, "JEV.UNMAPPED"),
            ({"id": "decision.api_status", "message": "HTTP 401"}, "JEV.UNMAPPED"),
            ({"id": "http.provider_busy", "status": "429", "message": "HTTP 429"}, "JEV.UNMAPPED"),
            ({"id": "decision.api_status", "status": True, "message": "HTTP 401"}, "JEV.UNMAPPED"),
            ({"id": "decidr.http", "status": 429, "cause": {"id": "http.provider_busy", "message": "busy"}}, "JEV.UNMAPPED"),
        )
        for detail, code in cases:
            with self.subTest(detail=detail):
                error = jj.sc_agent_error(detail)
                self.assertEqual(error.code, code)
                self.assertFalse(error.recoverable)

    def test_native_cause_and_message_remain_exact_when_status_cannot_be_classified(self):
        detail = {"id": "decidr.http", "message": "wrapped", "cause": {"id": "http.provider_busy", "message": "HTTP 429: provider words"}}
        base = jj.load_question_set("plan").value
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        request = {"item": {"id": "i", "title": "", "text": "record"}, "questions": [{"candidate_id": "c", "questions": base.questions}]}
        job = jj.batch_jobs(request, 1, settings, base.roles).value[0]
        line = jj._sc_agent_result(job, settings, {"position": 0, "error": detail})
        self.assertEqual((line["error"]["code"], line["error"]["message"]), ("JEV.UNMAPPED", "HTTP 429: provider words"))
        self.assertEqual(line["error"]["detail"], detail)

    def test_only_sagerror_uses_native_exception_arguments(self):
        class SagError(Exception):
            pass
        module = types.SimpleNamespace(SagError=SagError)
        native = {"id": "http.network", "message": "reset", "cause": {"id": "io.error", "message": "closed"}}
        self.assertEqual(jj._sc_agent_exception_detail(SagError("decidr.http", "outer", json.dumps(native)), module), native)
        self.assertEqual(jj._sc_agent_exception_detail(SagError("http.network", "reset", "invalid JSON"), module), {"id": "http.network", "message": "reset"})
        for exc in (RuntimeError("http.network", "reset", json.dumps(native)), SagError("HTTP 401"), ValueError("HTTP 429")):
            with self.subTest(exc=exc):
                detail = jj._sc_agent_exception_detail(exc, module)
                self.assertNotIn("id", detail)
                self.assertEqual(jj.sc_agent_error(detail).code, "JEV.UNMAPPED")
                self.assertEqual(detail["message"], str(exc))

    def test_batch_exception_retains_typed_detail_and_does_not_invent_an_id(self):
        from test_jev_batch import WheelCancelToken
        base = jj.load_question_set("plan").value
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        request = {"item": {"id": "i", "title": "", "text": "record"}, "questions": [{"candidate_id": "c", "questions": base.questions}]}
        def failed(*args, **kwargs):
            raise RuntimeError("HTTP 401 is only text")
        module = types.SimpleNamespace(CancelToken=WheelCancelToken, send_batch=failed)
        with tempfile.TemporaryDirectory() as directory:
            log = jj.open_run_log(directory, "exception").value
            try:
                with mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(module)):
                    result = jj.pump_batch([request], settings, None, log, echo=False)
            finally:
                log.close()
        self.assertIsInstance(result, jj.Err)
        self.assertEqual(result.error.code, "JEV.UNMAPPED")
        self.assertNotIn("id", result.error.data["sc_agent_error"])
        self.assertEqual(result.error.data["sc_agent_error"]["message"], "HTTP 401 is only text")
