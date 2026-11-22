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
import unittest
from unittest import mock
import tempfile
from pathlib import Path

from child_support import run_child
from jev_support import SCRIPTS, SKILL, log_lines, read_log
import jev_judge as jj  # noqa: E402

from test_jev_judge import BatchTransport, STATEMENT, answer, consented, env, plan_answers, run_cli, write  # noqa: E402

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

    def test_batch_without_run_dir_or_anchors_suggests_run_dir_first(self):
        stdout = io.StringIO()
        source = self.put("one.jsonl", jsonl(self.LINES[:1]))
        with contextlib.redirect_stdout(stdout):
            code = jj.main(["batch", "--input", source, "--dry-run"])
        out = json.loads(stdout.getvalue())
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), out)
        self.assertIn("--run-dir <directory>", out["error"]["suggested_action"])
        self.assertIn("for an anchor run", out["error"]["suggested_action"])

    LINES = [request_line("s1", "We copy the legacy crates.", ("cur", PLAN_QS["questions"]), ("alt", alt_set(1)), title="Sprint 1"),
             request_line("s3", "# Sprint 3\n\nCopy the legacy runtime crates.\n", ("cur", PLAN_QS["questions"]))]
    FIXTURE = {"s1/cur": plan_answers(), "s1/alt/r2": plan_answers(comp="no"), "alt": plan_answers(), "*": plan_answers(conf="yes")}

    def subprocess_batch(self, run_dir, *extra, stdin=None):
        """The rendered script as a separate process: stdout bytes exactly as a caller sees them."""
        argv = [sys.executable, str(SCRIPTS / "jev_judge.py"), "batch", "--run-dir", str(self.d / run_dir), "--run-name", "r1",
                "--answers-file", self.put("answers.json", self.FIXTURE), "--repeat", "2", "--request-prefix", "run-7", *extra]
        proc = run_child(argv, input=stdin, cwd=str(self.d))
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
                         (hashlib.sha256(b"run-7/s1/ANC-001/alt/r2").hexdigest()[:16], True, 0, "jev-batch-result/1"))
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
        proc = run_child(argv, cwd=str(self.d))
        self.assertEqual((proc.returncode, proc.stderr), (0, b""))
        self.assertEqual(len(proc.stdout.splitlines()), 3)
        self.assertNotIn(b"\r", proc.stdout)
        self.assertEqual(self.log("crlf"), self.parsed(proc.stdout))

    def test_native_callbacks_persist_finish_order_and_match_input_indices(self):
        from test_jev_judge import wheel_record
        line = request_line("s1", "text", ("c1", PLAN_QS["questions"]), ("c2", PLAN_QS["questions"]), ("c3", PLAN_QS["questions"]))
        settings = jj.BatchSettings("plan", "fixture-model", 1, "p", 0.6, 30.0, 3, 24000, False)
        records = [wheel_record((json.dumps({"response": {"answers": plan_answers()}, "sends": 1}), None), i) for i in range(3)]
        persisted = []
        def native_batch(requests, **kwargs):
            self.assertEqual(len(requests), 3)
            for i in (2, 0, 1):
                kwargs["on_result"](records[i])
                self.assertEqual(len(persisted), (2, 0, 1).index(i) + 1)
            return {"ok": True, "value": records}
        def log_result(log, result, fields):
            persisted.append(result["candidate_id"])
            return jj.Ok(None)
        with mock.patch.object(jj.decidr_client, "call_batch_results", side_effect=native_batch), \
                mock.patch.object(jj, "log_result_line", side_effect=log_result):
            got = jj._live_batch_results([line], settings, mock.Mock(), False)
        self.assertIsInstance(got, jj.Ok)
        self.assertEqual(persisted, ["c3", "c1", "c2"])
        self.assertEqual([r["candidate_id"] for r in got.value], ["c1", "c2", "c3"])

    def test_failed_call_is_a_line_and_exit_2_with_the_error_on_stderr(self):
        self.FIXTURE = {"s1/cur": [{"__error__": "DECIDR.OVERLOADED"}, {"__error__": "DECIDR.OVERLOADED"}], "*": plan_answers()}
        proc = self.subprocess_batch("runs", "--repeat", "1", stdin=jsonl(self.LINES[:1]).encode("utf-8"))
        self.assertEqual(proc.returncode, 2)
        lines = [json.loads(x) for x in proc.stdout.decode("utf-8").splitlines()]
        failed = next(x for x in lines if x["candidate_id"] == "cur")
        self.assertEqual((failed["ok"], failed["retry_count"], failed["error"]["code"], failed["verdict"]), (False, 1, "DECIDR.OVERLOADED", None))
        self.assertTrue(next(x for x in lines if x["candidate_id"] == "alt")["ok"])
        self.assertEqual(json.loads(proc.stderr)["error"]["code"], "DECIDR.OVERLOADED")
        self.assertEqual(self.log("runs"), lines)

    def test_wheel_failure_is_flushed_to_run_log_during_result_callback(self):
        detail = {"id": "http.network", "category": "network", "message": "controlled connection failure",
                  "recovery": "Check connectivity and retry."}
        source = self.put("in.jsonl", jsonl(self.LINES[:1]))
        transport = BatchTransport((json.dumps({"error": detail, "sends": 1}), "DECIDR.NETWORK"))
        observed = []

        def checked_transport(requests, **kwargs):
            persist = kwargs["on_result"]

            def received(record):
                persist(record)
                observed.append(self.log("runs"))

            kwargs["on_result"] = received
            return transport(requests, **kwargs)

        stdout, stderr = io.StringIO(), io.StringIO()
        with consented(), mock.patch.object(jj.decidr_client, "call_batch_results", checked_transport), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = jj.main(["batch", "--input", source, "--run-dir", str(self.d / "runs")])
        lines = [json.loads(raw) for raw in stdout.getvalue().splitlines()]
        self.assertEqual(code, 2)
        self.assertEqual([len(snapshot) for snapshot in observed], [1, 2])
        self.assertEqual(observed[0], lines[:1])
        self.assertEqual(observed[1], lines)
        self.assertFalse(observed[0][0]["ok"])
        self.assertEqual(observed[0][0]["error"]["code"], "DECIDR.NETWORK")
        self.assertTrue(lines[1]["ok"])

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

    def test_live_auth_failure_is_reported_from_the_typed_wheel_error(self):
        error = {"id": "auth.credentials", "category": "auth", "message": "credential unavailable", "sends": 1}
        transport = BatchTransport((json.dumps({"error": error}), "AUTH.CREDENTIALS"))
        src = self.put("in.jsonl", jsonl([request_line("s1", "text", ("cur", PLAN_QS["questions"]))]))
        stdout, stderr = io.StringIO(), io.StringIO()
        with consented(), mock.patch.object(jj.decidr_client, "call_batch_results", transport), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = jj.main(["batch", "--input", src, "--run-dir", str(self.d / "runs")])
        line, = [json.loads(raw) for raw in stdout.getvalue().splitlines()]
        self.assertEqual((code, line["error"]["code"], json.loads(stderr.getvalue())["error"]["code"]),
                         (2, "AUTH.CREDENTIALS", "AUTH.CREDENTIALS"))

    def test_batch_summary_keeps_auth_cause_after_other_requests_are_canceled(self):
        auth = {"id": "auth.credentials", "category": "auth", "message": "credential unavailable",
                "recovery": "Set TYPESAFE_API_KEY or store it in the default credential entry."}
        canceled = {"id": "decision.cancelled", "category": "cancelled", "message": "the request was cancelled"}
        src = self.put("in.jsonl", jsonl([request_line("s1", "text", *[
            (f"c{i}", PLAN_QS["questions"]) for i in range(4)])]))
        for auth_position in (0, 1, 2, 3, None):
            with self.subTest(auth_position=auth_position):
                transport = BatchTransport(*[
                    (json.dumps({"error": auth if i == auth_position else canceled, "sends": 1}), None)
                    for i in range(4)])
                stdout, stderr = io.StringIO(), io.StringIO()
                with consented(), mock.patch.object(jj.decidr_client, "call_batch_results", transport), \
                        contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = jj.main(["batch", "--input", src, "--run-dir", str(self.d / f"runs-{auth_position}")])
                lines = [json.loads(raw) for raw in stdout.getvalue().splitlines()]
                summary = json.loads(stderr.getvalue())
                cause = lines[auth_position if auth_position is not None else 0]
                self.assertEqual((code, len(lines), summary["unanswered"]), (2, 4, 4))
                self.assertEqual(summary["request_id"], cause["request_id"])
                self.assertEqual(summary["error"], cause["error"])
                self.assertEqual(summary["error"]["code"], "AUTH.CREDENTIALS" if auth_position is not None else "CANCELED")
                if auth_position is not None:
                    self.assertEqual(summary["error"]["message"], auth["message"])
                    self.assertEqual(summary["error"]["suggested_action"], auth["recovery"])


class BatchRetryPolicyTests(BatchCase):
    """The shared wheel owns retries; judge-jev records the wheel's typed attempt count."""

    LINE = request_line("s1", "We copy the legacy crates.", ("cur", PLAN_QS["questions"]))

    def live_batch(self, result):
        stdout, stderr = io.StringIO(), io.StringIO()
        with consented(), mock.patch.object(jj.decidr_client, "call_batch_results", BatchTransport(result)), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = jj.main(["batch", "--input", self.put("in.jsonl", jsonl([self.LINE])),
                            "--run-dir", str(self.d / "runs"), "--run-name", "r1", "--max-workers", "1"])
        lines = [json.loads(raw) for raw in stdout.getvalue().splitlines()]
        envelope = json.loads(stderr.getvalue()) if stderr.getvalue() else None
        return code, lines, envelope

    def test_retry_count_comes_from_wheel_error_attempts(self):
        detail = {"id": "http.provider_busy", "category": "busy", "message": "busy", "sends": 4}
        code, lines, envelope = self.live_batch((json.dumps({"error": detail, "sends": 4}), "DECIDR.OVERLOADED"))
        line, = lines
        self.assertEqual((code, line["ok"], line["retry_count"], line["attempts"]), (2, False, 3, []))
        self.assertEqual(envelope["error"]["code"], "DECIDR.OVERLOADED")

    def test_success_is_not_retried_by_judge_jev(self):
        response = {"model": "jev-x", "answers": plan_answers()}
        code, lines, envelope = self.live_batch((json.dumps({"response": response, "sends": 1}), None))
        line, = lines
        self.assertEqual((code, envelope, line["ok"], line["retry_count"], line["attempts"], line["verdict"]),
                         (0, None, True, 0, [], "satisfied"))


if __name__ == "__main__":
    unittest.main()
