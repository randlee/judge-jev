"""call_jev's error envelopes, driven through urllib so the internal error channel is not assumed.

Ported from plan-anchor's tests/sc-plan-anchor/test_error_contracts.py (JevTransportErrorContracts),
run through `batch` instead of `judge`: every transport failure keeps its exact code, message and
recoverable flag on the result line. No network is touched.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

from jev_support import SCRIPTS  # noqa: F401 - renders the scripts and puts them on sys.path
import jev_judge as jj  # noqa: E402

from test_jev_judge import jsonl, plan_answers, request_line  # noqa: E402

LIVE = {"TYPESAFE_API_KEY": "sk-test-0001"}


class FakeResponse:
    def __init__(self, raw: bytes):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n=-1):
        return self.raw[:n] if n >= 0 else self.raw


def http_error(status, body=b"", headers=None):
    return urllib.error.HTTPError("http://jev", status, "x", headers or {}, io.BytesIO(body))


class JevTransportErrorContracts(unittest.TestCase):
    def batch(self, responses):
        responses = list(responses)
        for response in responses:
            if isinstance(response, urllib.error.HTTPError):
                self.addCleanup(response.close)
        sleeps, out, err = [], io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.jsonl"
            src.write_text(jsonl([request_line()]), encoding="utf-8")
            with mock.patch.dict(os.environ, {"PATH": os.environ.get("PATH", ""), **LIVE}, clear=True), \
                    mock.patch.object(jj, "credential_store_api_key", return_value=""), \
                    mock.patch.object(jj.urllib.request, "urlopen", side_effect=responses) as opened, \
                    mock.patch.object(jj, "_sleep", sleeps.append), \
                    mock.patch.object(jj, "remote_judge_consent", return_value=jj.Ok(None)), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = jj.main(["batch", "--input", str(src), "--run-dir", str(Path(d) / "runs"), "--max-workers", "1"])
        line = json.loads(out.getvalue())
        envelope = json.loads(err.getvalue()) if code == 2 else None
        if code == 0:
            self.assertEqual(err.getvalue(), "")
        return code, line, envelope, opened, sleeps

    def test_request_shape_and_auth_header(self):
        code, line, _, opened, _ = self.batch([FakeResponse(json.dumps({"model": "jev-x", "answers": plan_answers()}).encode("utf-8"))])
        self.assertEqual((code, line["verdict"], line["model_answered"]), (0, "satisfied", "jev-x"))
        request = opened.call_args.args[0]
        self.assertEqual((request.full_url, request.get_method()), ("https://api.typesafe.ai/v1/systemone", "POST"))
        self.assertEqual((request.get_header("Authorization"), request.get_header("Content-type"), request.get_header("User-agent")),
                         ("Bearer sk-test-0001", "application/json", "judge-jev/jev_judge"))
        self.assertEqual(json.loads(request.data), line["request"])
        self.assertEqual(sorted(line["request"]), ["model", "questions", "state"])
        self.assertEqual(line["request"]["model"], "jev-latest")
        self.assertEqual(opened.call_args.kwargs, {"timeout": 30.0})

    def test_401_aborts_with_body_withheld(self):
        code, line, envelope, opened, sleeps = self.batch([http_error(401, b"Bearer sk-test-0001 is wrong")])
        self.assertEqual((code, opened.call_count, sleeps), (2, 1, []))
        self.assertEqual(line["error"], {"code": "AUTH.CREDENTIALS", "message": "Jev HTTP 401; response body withheld", "recoverable": False})
        self.assertEqual(envelope["error"]["code"], "AUTH.CREDENTIALS")
        self.assertNotIn("sk-test-0001", json.dumps(line))

    def test_transient_codes_retry_once_then_leave_the_line_without_an_answer(self):
        cases = (
            (http_error(429, headers={"Retry-After": "7"}), "JEV.RATE_LIMITED", "Jev HTTP 429; response body withheld", [7.0]),
            (http_error(529), "JEV.OVERLOADED", "Jev HTTP 529; response body withheld", [1.0]),
            (http_error(503), "JEV.HTTP", "Jev HTTP 503; response body withheld", [1.0]),
            (urllib.error.URLError("refused"), "JEV.NETWORK", "Could not reach Jev: refused", [1.0]),
            (ConnectionResetError("reset"), "JEV.NETWORK", "Jev connection failed: ConnectionResetError: reset", [1.0]),
            (FakeResponse(b"not json"), "JEV.RESPONSE_INVALID", "Jev response was not JSON", [1.0]),
            (FakeResponse(b"[1]"), "JEV.RESPONSE_INVALID", "Jev response was not a JSON object", [1.0]),
            (FakeResponse(b"x" * (jj.MAX_RESPONSE_BYTES + 1)), "JEV.RESPONSE_INVALID", "Jev response exceeded the size limit", [1.0]),
            (FakeResponse(b'{"answers": {}}'), "JEV.RESPONSE_INVALID",
             "Jev answer ids differ from the questions (missing ['addressed', 'contradicted', 'relevant'], unexpected [])", [1.0]),
        )
        for failure, error_code, message, delays in cases:
            with self.subTest(error_code=error_code, message=message):
                code, line, envelope, opened, sleeps = self.batch([failure, failure])
                self.assertEqual((code, envelope["error"]["code"]), (2, error_code))
                self.assertEqual((line["ok"], line["verdict"], opened.call_count, sleeps, line["retry_count"]), (False, None, 2, delays, 1))
                self.assertEqual(line["error"], {"code": error_code, "message": message, "recoverable": True})

    def test_transient_failure_then_success_passes(self):
        ok = FakeResponse(json.dumps({"model": "jev-x", "answers": plan_answers()}).encode("utf-8"))
        code, line, _, opened, sleeps = self.batch([http_error(500), ok])
        self.assertEqual((code, opened.call_count, sleeps, line["verdict"], line["retry_count"]), (0, 2, [1.0], "satisfied", 1))

    def test_non_transient_http_errors_are_recorded_without_retry(self):
        code, line, envelope, opened, _ = self.batch([http_error(422, b"questions.addressed is invalid")])
        self.assertEqual((code, opened.call_count, envelope["error"]["code"]), (2, 1, "JEV.VALIDATION"))
        self.assertEqual(line["error"], {"code": "JEV.VALIDATION", "message": "Jev HTTP 422: questions.addressed is invalid", "recoverable": False})
        code, line, envelope, opened, _ = self.batch([http_error(418, b"teapot")])
        self.assertEqual((code, opened.call_count, envelope["error"]["code"]), (2, 1, "JEV.HTTP"))
        self.assertEqual(line["error"], {"code": "JEV.HTTP", "message": "Jev HTTP 418; response body withheld", "recoverable": False})

    def test_context_overflow_is_recoverable_and_retried_once(self):
        code, line, envelope, opened, sleeps = self.batch([http_error(400, b"max_tokens exceeded"), http_error(400, b"max_tokens exceeded")])
        self.assertEqual((code, opened.call_count, sleeps, envelope["error"]["code"]), (2, 2, [1.0], "JEV.CONTEXT_EXCEEDED"))
        self.assertEqual(line["error"], {"code": "JEV.CONTEXT_EXCEEDED", "message": "Jev HTTP 400: request exceeds the model's context window",
                                         "recoverable": True})

    def test_non_numeric_flag_exits_two_with_json(self):
        for flag, value, kind in (("--max-workers", "lots", "int"), ("--repeat", "1.5", "int"), ("--threshold", "high", "float")):
            proc = subprocess.run([sys.executable, str(SCRIPTS / "jev_judge.py"), "batch", "--input", "x", "--dry-run", flag, value],
                                  capture_output=True, text=True, encoding="utf-8")
            self.assertEqual((proc.returncode, proc.stderr), (2, ""), flag)
            self.assertEqual(json.loads(proc.stdout), {"success": False, "data": None, "error": {
                "code": "VALIDATION.INPUT", "message": f"jev_judge.py batch: argument {flag}: invalid {kind} value: {value!r}",
                "recoverable": False, "suggested_action": "Run 'jev_judge.py <subcommand> --help' for the accepted arguments."}})


if __name__ == "__main__":
    unittest.main()
