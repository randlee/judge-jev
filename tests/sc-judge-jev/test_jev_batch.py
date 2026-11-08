"""`batch`, the low layer: JSONL request lines in, JSONL result lines out on stdout and in the sc-observability run log.

Ported from plan-anchor's tests/sc-plan-anchor/test_tournament.py (BatchTests). Answers come from
answers files or a stubbed transport; Jev is never called. Ordering is driven by events, not sleeps.
"""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import threading
import unittest
from unittest import mock
import tempfile
from pathlib import Path

from jev_support import SCRIPTS, SKILL, log_lines, read_log
import jev_judge as jj  # noqa: E402

from test_jev_judge import STATEMENT, Transport, answer, consented, env, http, plan_answers, run_cli, write  # noqa: E402

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
        proc = subprocess.run(argv, input=stdin, capture_output=True, cwd=str(self.d))
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
        proc = subprocess.run(argv, capture_output=True, cwd=str(self.d))
        self.assertEqual((proc.returncode, proc.stderr), (0, b""))
        self.assertEqual(len(proc.stdout.splitlines()), 3)
        self.assertNotIn(b"\r", proc.stdout)
        self.assertEqual(self.log("crlf"), self.parsed(proc.stdout))

    def test_results_stream_in_request_order_as_each_answer_arrives(self):
        """Completion order is forced to c3, c1, c2 with events (no sleeps); lines still come out c1, c2, c3, and c1
        is yielded while c2 is still unanswered, so nothing is held back for the end of the batch."""
        line = request_line("s1", "text", ("c1", PLAN_QS["questions"]), ("c2", PLAN_QS["questions"]), ("c3", PLAN_QS["questions"]))
        c3_done, release_c2 = threading.Event(), threading.Event()
        completed, waits = [], []
        real = jj.run_batch_job

        def controlled(job, settings, api_key, fixture, abort):
            if job.candidate_id == "c1":
                waits.append(c3_done.wait(timeout=30))  # a guard against a deadlocked implementation, not a timing input
            if job.candidate_id == "c2":
                waits.append(release_c2.wait(timeout=30))
            result = real(job, settings, api_key, fixture, abort)
            completed.append(job.candidate_id)
            if job.candidate_id == "c3":
                c3_done.set()
            return result

        settings = jj.BatchSettings("plan", "fixture-model", 1, "p", 0.6, 30.0, 3, 24000, False)

        async def consume():
            got = []
            async for result in jj.stream_batch([line], settings, "", {"*": plan_answers()}):
                got.append((result["candidate_id"], list(completed)))
                release_c2.set()
            return got

        with mock.patch.object(jj, "run_batch_job", controlled):
            got = jj.asyncio.run(consume())
        self.assertEqual(waits, [True, True])
        self.assertEqual([cid for cid, _ in got], ["c1", "c2", "c3"])
        self.assertEqual(got[0][1], ["c3", "c1"])  # c1 was yielded before c2 had an answer
        self.assertEqual(completed, ["c3", "c1", "c2"])

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

    def test_live_run_fails_closed_before_any_line(self):
        with mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}), mock.patch.object(jj, "credential_store_api_key", return_value=""):
            code, out = run_cli(["batch", "--input", self.put("in.jsonl", jsonl(self.LINES)), "--run-dir", str(self.d / "runs")])
        self.assertEqual((code, out["error"]["code"]), (2, "AUTH.CREDENTIALS"))
        self.assertFalse((self.d / "runs").exists())


class BatchRetryPolicyTests(BatchCase):
    """One retry per failed call (Retry-After first), AUTH.CREDENTIALS stops the remaining calls; the transport is stubbed."""

    LINE = request_line("s1", "We copy the legacy crates.", ("cur", PLAN_QS["questions"]))

    def live_batch(self, transport, *extra):
        """Runs batch in-process; stderr (the error envelope when a line has no answer) is checked, never dropped."""
        sleeps, err = [], io.StringIO()
        with env(TYPESAFE_API_KEY="sk-test-0001"), consented(), mock.patch.object(jj, "call_jev", transport), \
                mock.patch.object(jj, "_sleep", sleeps.append), contextlib.redirect_stderr(err):
            code, out = run_cli(["batch", "--input", self.put("in.jsonl", jsonl([self.LINE])), "--run-dir", str(self.d / "runs"),
                                 "--run-name", "r1", "--max-workers", "1", *extra])
        if code == 0:
            self.assertEqual(err.getvalue(), "")
        else:
            envelope = json.loads(err.getvalue())
            self.assertEqual((envelope["success"], envelope["data"]), (False, None))
            self.assertEqual(envelope["error"]["suggested_action"],
                             "Read each failed line's error field; rerun only those requests once the cause is fixed.")
            self.stderr_code = envelope["error"]["code"]
        return code, out, sleeps

    def test_transient_failure_then_success_is_one_retry(self):
        t = Transport(http(429, retry_after=7.0))
        code, out, sleeps = self.live_batch(t)
        self.assertEqual((code, out["ok"], out["retry_count"], out["verdict"], len(t.bodies), sleeps), (0, True, 1, "satisfied", 2, [7.0]))
        self.assertEqual([a["ok"] for a in out["attempts"]], [False, True])
        self.assertEqual(out["attempts"][0]["error"]["code"], "JEV.RATE_LIMITED")

    def test_two_transient_failures_leave_the_line_without_an_answer(self):
        t = Transport(http(503), http(503))
        code, out, sleeps = self.live_batch(t)
        self.assertEqual((code, out["ok"], out["retry_count"], out["error"]["code"], len(t.bodies), sleeps), (2, False, 1, "JEV.HTTP", 2, [1.0]))
        self.assertEqual(self.stderr_code, "JEV.HTTP")

    def test_non_transient_failure_is_not_retried(self):
        t = Transport(http(422, "questions.addressed is invalid"))
        code, out, sleeps = self.live_batch(t)
        self.assertEqual((code, out["ok"], out["retry_count"], out["error"]["code"], len(t.bodies), sleeps), (2, False, 0, "JEV.VALIDATION", 1, []))
        self.assertEqual(self.stderr_code, "JEV.VALIDATION")

    def test_invalid_response_is_retried_as_transient(self):
        t = Transport({"model": "x", "answers": {}})
        code, out, _ = self.live_batch(t)
        self.assertEqual((code, out["ok"], out["retry_count"], out["verdict"]), (0, True, 1, "satisfied"))
        self.assertEqual(out["attempts"][0]["error"]["code"], "JEV.RESPONSE_INVALID")

    def test_credentials_rejected_by_jev_stop_the_remaining_calls(self):
        t = Transport(http(401, "Bearer sk-test-0001 is wrong"))
        code, out, sleeps = self.live_batch(t, "--repeat", "3")
        lines = log_lines(self.d / "runs")
        self.assertEqual((code, len(t.bodies), sleeps, self.stderr_code), (2, 1, [], "AUTH.CREDENTIALS"))
        self.assertEqual([x["error"]["code"] for x in lines], ["AUTH.CREDENTIALS"] * 3)
        self.assertEqual([x["attempts"][0]["error"]["message"] for x in lines[1:]], ["not sent: the batch aborted"] * 2)
        self.assertNotIn("sk-test-0001", json.dumps(read_log(self.d / "runs")))


if __name__ == "__main__":
    unittest.main()
