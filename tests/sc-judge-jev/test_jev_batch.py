"""`batch`, the low layer: JSONL request lines in, JSONL result lines out on stdout and in the sc-observability run log.

Ported from plan-anchor's tests/sc-plan-anchor/test_tournament.py (BatchTests). Answers come from
answers files or a stubbed transport; Jev is never called. Ordering is driven by events, not sleeps.
"""
import contextlib
import hashlib
import io
import json
import os
import sys
import threading
import unittest
from unittest import mock
import tempfile
from pathlib import Path

from child_support import run_child
from jev_support import SCRIPTS, SKILL, log_lines, read_log
import jev_judge as jj  # noqa: E402

from test_jev_judge import STATEMENT, answer, consented, env, plan_answers, run_cli, write, sc_decidr  # noqa: E402

PLAN_QS = json.loads((SKILL / "assets" / "questions" / "plan.json").read_text(encoding="utf-8"))
ROLES = ("addressed", "contradicted", "relevant")
ANCHOR_STATE = {"id": "ANC-001", "statement": STATEMENT, "scope": "the runtime crates", "kind": "directive"}


def question(role, n):
    return {"type": "choice", "instructions": f"Variant {n}: does `item.text` meet the {role} judgment for `anchor.statement`?",
            "criteria": {"yes": f"{role} holds ({n})", "no": f"{role} does not hold ({n})", "unclear": f"cannot tell ({n})"}}


def request_line(item_id, text, *cands, title=""):
    return {"item": {"id": item_id, "title": title, "text": text}, "anchor": dict(ANCHOR_STATE),
            "questions": [{"candidate_id": c, "questions": qs} for c, qs in cands]}


def alt_set(n):
    return {role: question(role, n) for role in ROLES}


def jsonl(lines):
    return "".join(json.dumps(x) + "\n" for x in lines)


class WheelCancelToken:
    def __init__(self):
        self.cancelled = False
    def cancel(self):
        self.cancelled = True


class BatchCase(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.d = Path(self.td.name)
        self.addCleanup(self.td.cleanup)

    def put(self, name, value):
        return write(self.d, name, value)


class BatchTests(BatchCase):
    """The low layer: JSONL request lines in, JSONL result lines out on stdout and in the sc-observability run log."""

    LINES = [request_line("s1", "We copy the legacy crates.", ("cur", PLAN_QS["questions"]), ("alt", alt_set(1)), title="Sprint 1"),
             request_line("s3", "# Sprint 3\n\nCopy the legacy runtime crates.\n", ("cur", PLAN_QS["questions"]))]
    FIXTURE = {"s1/cur": plan_answers(), "s1/alt/r2": plan_answers(comp="no"), "alt": plan_answers(), "*": plan_answers(conf="yes")}

    def subprocess_batch(self, run_dir, *extra, stdin=None):
        """The rendered script as a separate process: stdout bytes exactly as a caller sees them."""
        argv = [sys.executable, str(SCRIPTS / "jev_judge.py"), "batch", "--run-dir", str(self.d / run_dir), "--run-name", "r1",
                "--answers-file", self.put("answers.json", self.FIXTURE), "--repeat", "2", "--request-prefix", "run-7", *extra]
        proc = run_child(argv, input=stdin, capture_output=True, cwd=str(self.d))
        return proc

    def log(self, run_dir):
        """The result lines rebuilt from the run log's request, answer and result events."""
        return log_lines(self.d / run_dir)

    @staticmethod
    def parsed(stdout):
        return [json.loads(x) for x in stdout.decode("utf-8").splitlines()]

    def test_lines_are_keyed_by_id_with_verdicts_and_request_evidence(self):
        proc = self.subprocess_batch("runs", "--input", self.put("in.jsonl", jsonl(self.LINES)))
        self.assertEqual((proc.returncode, proc.stderr), (0, b""))
        lines = [json.loads(x) for x in proc.stdout.decode("utf-8").splitlines()]
        self.assertEqual([x["request_id"] for x in lines],
                         ["run-7/s1/ANC-001/cur/r1", "run-7/s1/ANC-001/cur/r2", "run-7/s1/ANC-001/alt/r1", "run-7/s1/ANC-001/alt/r2",
                          "run-7/s3/ANC-001/cur/r1", "run-7/s3/ANC-001/cur/r2"])
        by_key = {(x["item_id"], x["candidate_id"], x["repeat"]): x for x in lines}
        self.assertEqual((by_key[("s1", "cur", 1)]["verdict"], by_key[("s1", "alt", 2)]["verdict"], by_key[("s3", "cur", 1)]["verdict"]),
                         ("satisfied", "not_addressed", "contradicted"))
        line = by_key[("s1", "alt", 2)]
        self.assertEqual(line["answers"]["addressed"]["probabilities"], answer("no")["probabilities"])
        self.assertEqual((line["run_id"], line["ok"], line["retry_count"], line["schema"]),
                         (hashlib.sha256(b"run-7/s1/ANC-001/alt/r2").hexdigest()[:16], True, 0, "judge-jev/jev-batch-result/1"))
        self.assertEqual(line["request"]["questions"], alt_set(1))
        self.assertEqual(line["request"]["state"]["item"], {"id": "s1", "title": "Sprint 1", "text": "We copy the legacy crates."})
        self.assertEqual(by_key[("s1", "cur", 1)]["request_sha256"], by_key[("s1", "cur", 2)]["request_sha256"])
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed; the schema half of this test needs it")
        schemas = SKILL / "assets" / "schemas"
        for name, values in (("jev-batch-request", self.LINES), ("jev-batch-result", lines)):
            validator = jsonschema.Draft202012Validator(json.loads((schemas / f"{name}.schema.json").read_text(encoding="utf-8")))
            for value in values:
                validator.validate(value)

    def test_log_holds_every_stdout_line_and_stdin_matches_file_input(self):
        from_file = self.subprocess_batch("a", "--input", self.put("in.jsonl", jsonl(self.LINES)))
        from_stdin = self.subprocess_batch("b", stdin=jsonl(self.LINES).encode("utf-8"))
        self.assertEqual((from_file.returncode, from_stdin.returncode), (0, 0))
        self.assertEqual(len(from_file.stdout.splitlines()), 6)
        self.assertEqual(self.log("a"), self.parsed(from_file.stdout))
        self.assertEqual(self.log("b"), self.parsed(from_stdin.stdout))
        self.assertEqual(from_stdin.stdout, from_file.stdout)
        events = read_log(self.d / "a")
        self.assertEqual([e["action"] for e in events], ["request", "answer", "result"] * 6)
        self.assertEqual({e["fields"]["run"] for e in events}, {"r1"})
        self.assertEqual([e["correlation_id"] for e in events if e["action"] == "result"], [x["run_id"] for x in self.parsed(from_file.stdout)])
        self.assertEqual(list((self.d / "a").rglob("tournament-*.jsonl")), [])  # REQ-JEV-0008: no own log format
        # the log is append-only: a second run with the same name adds its events after the first run's
        again = self.subprocess_batch("a", "--input", str(self.d / "in.jsonl"))
        self.assertEqual(self.log("a"), self.parsed(from_file.stdout) + self.parsed(again.stdout))

    def test_three_request_lines_are_three_results_and_three_result_events(self):
        """REQ-JEV-0002: a request file of three lines produces three result envelopes and three log entries."""
        three = [request_line(f"s{n}", "We copy the legacy crates.", ("cur", PLAN_QS["questions"])) for n in (1, 2, 3)]
        proc = self.subprocess_batch("three", "--repeat", "1", "--input", self.put("three.jsonl", jsonl(three)))
        self.assertEqual((proc.returncode, proc.stderr), (0, b""))
        self.assertEqual(len(self.parsed(proc.stdout)), 3)
        self.assertEqual(len(read_log(self.d / "three", action="result")), 3)

    def test_dry_run_logs_requests_and_results_without_answers(self):
        proc = self.subprocess_batch("dry", "--dry-run", "--repeat", "1", "--input", self.put("in.jsonl", jsonl(self.LINES[1:])))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([e["action"] for e in read_log(self.d / "dry")], ["request", "result"])
        self.assertEqual(self.log("dry"), self.parsed(proc.stdout))

    def test_stdout_lines_end_in_lf_where_text_stdout_writes_crlf(self):
        """On Windows a text-mode stdout turns "\n" into "\r\n"; the result lines must still match the log byte for byte.
        The child gets the same CRLF-translating stdout on every OS, so this check does not depend on the runner OS."""
        wrapper = ("import runpy, sys; sys.stdout.reconfigure(newline='\\r\\n'); sys.argv = sys.argv[1:]; "
                   "runpy.run_path(sys.argv[0], run_name='__main__')")
        argv = [sys.executable, "-c", wrapper, str(SCRIPTS / "jev_judge.py"), "batch", "--run-dir", str(self.d / "crlf"),
                "--run-name", "r1", "--answers-file", self.put("answers.json", self.FIXTURE), "--input",
                self.put("in.jsonl", jsonl(self.LINES))]
        proc = run_child(argv, capture_output=True, cwd=str(self.d))
        self.assertEqual((proc.returncode, proc.stderr), (0, b""))
        self.assertEqual(len(proc.stdout.splitlines()), 3)
        self.assertNotIn(b"\r", proc.stdout)
        self.assertEqual(self.log("crlf"), self.parsed(proc.stdout))

    def test_live_callback_completion_order_is_buffered_to_request_order(self):
        line = request_line("s1", "text", ("c1", PLAN_QS["questions"]), ("c2", PLAN_QS["questions"]), ("c3", PLAN_QS["questions"]))
        class Reordered:
            CancelToken = WheelCancelToken
            def send_batch(self, requests, *, on_result=None, **kwargs):
                results = [{"position": i, "response": {"model": "jev-test", "answers": plan_answers()}}
                           for i in (2, 0, 1)]
                for result in results:
                    on_result(result)
                return results
        with consented(), mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(Reordered())):
            code, output = run_cli(["batch", "--input", self.put("live.jsonl", jsonl([line])), "--run-dir", str(self.d / "live")])
        self.assertEqual(code, 0, output)
        self.assertEqual([item["candidate_id"] for item in (json.loads(line) for line in output.splitlines())], ["c1", "c2", "c3"])

    def test_keyboard_interrupt_cancels_the_wheel_token(self):
        class Interrupted:
            CancelToken = WheelCancelToken
            token = None
            def send_batch(inner, requests, *, cancel=None, **kwargs):
                inner.token = cancel
                raise KeyboardInterrupt
        wheel = Interrupted()
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        log = jj.open_run_log(self.d / "interrupt", "interrupt")
        self.addCleanup(log.value.close)
        with self.assertRaises(KeyboardInterrupt), mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(wheel)):
            jj.pump_batch([self.LINES[0]], settings, None, log.value, echo=False)
        self.assertIsInstance(wheel.token, WheelCancelToken)
        self.assertTrue(wheel.token.cancelled)

    def test_credential_failure_cancels_the_wheel_batch(self):
        class CredentialFailure:
            CancelToken = WheelCancelToken
            token = None
            def send_batch(inner, requests, *, cancel=None, on_result=None, **kwargs):
                inner.token = cancel
                result = {"position": 0, "error": {"id": "secrets.credential_rejected", "message": "credential rejected"}}
                on_result(result)
                return [result]
        wheel = CredentialFailure()
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        one = request_line("s1", "text", ("c1", PLAN_QS["questions"]))
        log = jj.open_run_log(self.d / "credential", "credential")
        self.addCleanup(log.value.close)
        with mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(wheel)), \
                mock.patch.object(jj, "log_result_line", return_value=jj.Ok(None)):
            result = jj.pump_batch([one], settings, None, log.value, echo=False)
        self.assertTrue(wheel.token.cancelled)
        self.assertEqual((result.value[0]["error"]["code"], result.value[0]["retry_count"]), ("AUTH.CREDENTIALS", 0))

    def test_failed_call_is_a_line_and_exit_2_with_the_error_on_stderr(self):
        self.FIXTURE = {"s1/cur": [{"__error__": "JEV.OVERLOADED"}, {"__error__": "JEV.OVERLOADED"}], "*": plan_answers()}
        proc = self.subprocess_batch("runs", "--repeat", "1", stdin=jsonl(self.LINES[:1]).encode("utf-8"))
        self.assertEqual(proc.returncode, 2)
        lines = [json.loads(x) for x in proc.stdout.decode("utf-8").splitlines()]
        failed = next(x for x in lines if x["candidate_id"] == "cur")
        self.assertEqual((failed["ok"], failed["retry_count"], failed["error"]["code"], failed["verdict"]), (False, 1, "JEV.OVERLOADED", None))
        self.assertTrue(next(x for x in lines if x["candidate_id"] == "alt")["ok"])
        self.assertEqual(json.loads(proc.stderr)["error"]["code"], "JEV.OVERLOADED")
        self.assertEqual(self.log("runs"), lines)

    def test_bad_input_is_refused_before_any_line(self):
        def refused(lines_text, *extra):
            code, out = run_cli(["batch", "--input", self.put("bad.jsonl", lines_text), "--run-dir", str(self.d / "runs"), "--dry-run", *extra])
            self.assertEqual((code, out["success"]), (2, False), out)
            return out["error"]["code"]
        good = jsonl(self.LINES)
        self.assertEqual(refused(good + "{not json\n"), "INPUT.MALFORMED")
        self.assertEqual(refused(jsonl([request_line("s1", "x", ("c", PLAN_QS["questions"]), ("c", PLAN_QS["questions"]))])), "VALIDATION.INPUT")
        self.assertEqual(refused(good + jsonl(self.LINES[:1])), "VALIDATION.INPUT")  # the same request twice
        self.assertEqual(refused(jsonl([request_line("bad id", "x", ("c", PLAN_QS["questions"]))])), "VALIDATION.INPUT")
        self.assertEqual(refused(good, "--max-workers", "5"), "VALIDATION.INPUT")
        self.assertEqual(refused("\n"), "INPUT.EMPTY")
        self.assertFalse((self.d / "runs").exists())
        code, out = run_cli(["batch", "--input", self.put("ok.jsonl", good)])
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))  # no log directory

    def test_max_request_bytes_over_the_loggable_ceiling_is_refused_before_any_line(self):
        src = self.put("big.jsonl", jsonl([request_line("s1", "x" * 80000, ("cur", PLAN_QS["questions"]))]))
        code, out = run_cli(["batch", "--input", src, "--run-dir", str(self.d / "runs"), "--dry-run", "--max-request-bytes", "200000"])
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), out)
        self.assertFalse((self.d / "runs").exists())

    def test_live_run_fails_closed_without_committed_consent(self):
        with mock.patch.object(jj, "remote_judge_consent", return_value=jj.Err(jj.JudgeError(
                "POLICY.REMOTE_JUDGE_DISABLED", "consent missing", action="ask the repository owner"))):
            code, out = run_cli(["batch", "--input", self.put("in.jsonl", jsonl(self.LINES)), "--run-dir", str(self.d / "runs")])
        self.assertEqual((code, out["error"]["code"]), (2, "POLICY.REMOTE_JUDGE_DISABLED"))
        self.assertFalse((self.d / "runs").exists())


class BatchRetryPolicyTests(BatchCase):
    """The consumer delegates live retry policy; fake wheel results are deterministic and never sleep or call a provider."""

    LINE = request_line("s1", "We copy the legacy crates.", ("cur", PLAN_QS["questions"]))

    def test_live_error_is_recorded_once_without_consumer_retry(self):
        class Failed:
            CancelToken = WheelCancelToken
            calls = 0
            def send_batch(inner, requests, *, on_result=None, **kwargs):
                inner.calls += 1
                result = {"position": 0, "error": {"id": "http.network", "message": "connection refused", "cause": {"id": "io.error", "message": "refused"}}}
                on_result(result)
                return [result]
        wheel = Failed()
        with consented(), mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(wheel)), contextlib.redirect_stderr(io.StringIO()):
            code, out = run_cli(["batch", "--input", self.put("in.jsonl", jsonl([self.LINE])), "--run-dir", str(self.d / "runs"), "--run-name", "r1"])
        self.assertEqual((code, wheel.calls, out["retry_count"], out["error"]["code"]), (2, 1, 0, "JEV.NETWORK"))
        self.assertEqual(out["error"]["detail"]["cause"]["id"], "io.error")

    def test_invalid_response_is_not_retried_by_the_consumer(self):
        class Invalid:
            CancelToken = WheelCancelToken
            calls = 0
            def send_batch(inner, requests, *, on_result=None, **kwargs):
                inner.calls += 1
                result = {"position": 0, "response": {"model": "jev-test", "answers": {}}}
                on_result(result)
                return [result]
        wheel = Invalid()
        with consented(), mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(wheel)), contextlib.redirect_stderr(io.StringIO()):
            code, out = run_cli(["batch", "--input", self.put("bad-response.jsonl", jsonl([self.LINE])), "--run-dir", str(self.d / "invalid")])
        self.assertEqual((code, wheel.calls, out["retry_count"], out["error"]["code"]), (2, 1, 0, "JEV.RESPONSE_INVALID"))


if __name__ == "__main__":
    unittest.main()
