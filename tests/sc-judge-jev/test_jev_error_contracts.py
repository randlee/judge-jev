"""Consumer mappings for the released sc-decidr typed error chain."""
import unittest

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
            ({"id": "secrets.credential_missing", "message": "missing"}, "AUTH.CREDENTIALS"),
        )
        for detail, expected in cases:
            with self.subTest(id=detail["id"], status=detail.get("status")):
                error = jj.sc_agent_error(detail)
                self.assertEqual(error.code, expected)
                self.assertFalse(error.recoverable)

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
