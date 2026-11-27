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
        _log_environment = mock.patch.dict(os.environ, {"JUDGE_JEV_LOG_ROOT": str(self.d / "logs")})
        _log_environment.start()
        self.addCleanup(_log_environment.stop)
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
        argv = [sys.executable, str(SCRIPTS / "jev_judge.py"), "batch", "--run-name", "r1", "--answers-file", self.put("answers.json", self.FIXTURE), "--repeat", "2", "--request-prefix", "run-7", *extra]
        proc = run_child(argv, input=stdin, cwd=str(self.d), env={**os.environ, "JUDGE_JEV_LOG_ROOT": str(self.d / run_dir)})
        return proc

    def log(self, run_dir):
        return [e["fields"] for e in read_log(self.d / run_dir, action="result")]

    @staticmethod
    def parsed(stdout):
        return [json.loads(x) for x in stdout.decode("utf-8").splitlines()]

    def test_lines_are_keyed_by_id_with_verdicts_and_wheel_schema(self):
        import importlib.resources
        import jsonschema
        proc = self.subprocess_batch("runs", "--input", self.put("in.jsonl", jsonl(self.LINES)))
        self.assertEqual((proc.returncode, proc.stderr), (0, b""))
        lines = self.parsed(proc.stdout)
        ids = ["run-7/s1/ANC-001/cur/r1", "run-7/s1/ANC-001/cur/r2", "run-7/s1/ANC-001/alt/r1", "run-7/s1/ANC-001/alt/r2", "run-7/s3/ANC-001/cur/r1", "run-7/s3/ANC-001/cur/r2"]
        self.assertEqual([line["request_id"] for line in lines], ids)
        by_id = {line["request_id"]: line for line in lines}
        self.assertEqual([by_id[ids[i]]["verdict"] for i in (0, 3, 4)], ["satisfied", "not_addressed", "contradicted"])
        self.assertEqual(len({line["run_id"] for line in lines}), 1)
        schema = json.loads((importlib.resources.files("sc_agent") / "templates" / "jev-batch-result.schema.json").read_text())
        validator = jsonschema.Draft202012Validator(schema)
        for line in lines:
            validator.validate(line)
            self.assertEqual((line["schema"], line["session_id"], line["ok"]), ("jev-batch-result/2", None, True))
            self.assertTrue({"request", "answers", "attempts"}.isdisjoint(line))

    def test_log_holds_every_stdout_line_and_stdin_matches_file_input(self):
        first = self.subprocess_batch("a", "--input", self.put("in.jsonl", jsonl(self.LINES)))
        second = self.subprocess_batch("b", stdin=jsonl(self.LINES).encode())
        self.assertEqual((first.returncode, second.returncode), (0, 0))
        lines1, lines2 = self.parsed(first.stdout), self.parsed(second.stdout)
        self.assertEqual(len(lines1), 6)
        for run_dir, lines in (("a", lines1), ("b", lines2)):
            events = read_log(self.d / run_dir)
            self.assertEqual([e["action"] for e in events], ["result"] * 6)
            self.assertEqual([e["fields"]["request_id"] for e in events], [x["request_id"] for x in lines])
            self.assertEqual([e["correlation_id"] for e in events], [x["run_id"] for x in lines])
            self.assertTrue(all({"request", "answers"}.isdisjoint(e["fields"]) for e in events))
        self.assertEqual([dict(x, run_id=None) for x in lines1], [dict(x, run_id=None) for x in lines2])
        again = self.subprocess_batch("a", "--input", str(self.d / "in.jsonl"))
        self.assertEqual(again.returncode, 0)
        self.assertEqual(len(self.log("a")), 12)

    def test_three_request_lines_are_three_results_and_three_result_events(self):
        """REQ-JEV-0002: a request file of three lines produces three result envelopes and three log entries."""
        three = [request_line(f"s{n}", "We copy the legacy crates.", ("cur", PLAN_QS["questions"])) for n in (1, 2, 3)]
        proc = self.subprocess_batch("three", "--repeat", "1", "--input", self.put("three.jsonl", jsonl(three)))
        self.assertEqual((proc.returncode, proc.stderr), (0, b""))
        self.assertEqual(len(self.parsed(proc.stdout)), 3)
        self.assertEqual(len(read_log(self.d / "three", action="result")), 3)

    def test_dry_run_writes_no_results_or_events(self):
        proc = self.subprocess_batch("dry", "--dry-run", "--repeat", "1", "--input", self.put("in.jsonl", jsonl(self.LINES[1:])))
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, b"", b""))
        self.assertEqual(read_log(self.d / "dry"), [])

    def test_stdout_lines_end_in_lf_where_text_stdout_writes_crlf(self):
        wrapper = ("import runpy, sys; sys.stdout.reconfigure(newline='\\r\\n'); sys.argv = sys.argv[1:]; "
                   "runpy.run_path(sys.argv[0], run_name='__main__')")
        argv = [sys.executable, "-c", wrapper, str(SCRIPTS / "jev_judge.py"), "batch", "--run-name", "r1", "--answers-file", self.put("answers.json", self.FIXTURE), "--input", self.put("in.jsonl", jsonl(self.LINES))]
        proc = run_child(argv, cwd=str(self.d), env={**os.environ, "JUDGE_JEV_LOG_ROOT": str(self.d / "crlf")})
        self.assertEqual((proc.returncode, proc.stderr), (0, b""))
        self.assertEqual(len(proc.stdout.splitlines()), 3)
        self.assertNotIn(b"\r", proc.stdout)
        self.assertEqual([x["request_id"] for x in self.log("crlf")], [x["request_id"] for x in self.parsed(proc.stdout)])

    def test_callbacks_match_input_indices_when_delivered_out_of_order(self):
        from sc_agent.testing import FakeRun
        line = request_line("s1", "text", ("c1", PLAN_QS["questions"]), ("c2", PLAN_QS["questions"]), ("c3", PLAN_QS["questions"]))
        settings = jj.BatchSettings("plan", 1, "p", 0.6, False)
        run = FakeRun({"run_id": "test-run", "provider": "local"})
        original = jj.decidr_client.run_batch
        def reverse(run, jobs, settings, **kwargs):
            deliver, saved = kwargs["on_line"], []
            kwargs["on_line"] = lambda line, answers: saved.append((line, answers))
            outcome = original(run, jobs, settings, **kwargs)
            for result, answers in reversed(saved):
                deliver(result, answers)
            return outcome
        with mock.patch.object(jj.decidr_client, "run_batch", side_effect=reverse):
            got = jj.judge_batch(run, [line], settings, fixture={"*": plan_answers()}, echo=False)
        self.assertTrue(got.ok, got)
        self.assertEqual([x[0].request_id.split("/")[-2] for x in got.value], ["c1", "c2", "c3"])
        self.assertEqual([x["fields"]["candidate_id"] for x in run.logged], ["c1", "c2", "c3"])

    def test_failed_call_is_a_line_and_exit_2_with_the_error_on_stderr(self):
        self.FIXTURE = {"s1/cur": {"__error__": "DECIDR.OVERLOADED"}, "*": plan_answers()}
        proc = self.subprocess_batch("runs", "--repeat", "1", stdin=jsonl(self.LINES[:1]).encode())
        self.assertEqual(proc.returncode, 2)
        lines = self.parsed(proc.stdout)
        failed = next(x for x in lines if "/cur/" in x["request_id"])
        self.assertEqual((failed["ok"], failed["error"]["code"], failed["verdict"]), (False, "DECIDR.OVERLOADED", None))
        self.assertTrue(next(x for x in lines if "/alt/" in x["request_id"])["ok"])
        self.assertEqual(json.loads(proc.stderr)["error"]["code"], "DECIDR.OVERLOADED")
        self.assertEqual([x["request_id"] for x in self.log("runs")], [x["request_id"] for x in lines])

    def test_wheel_failure_is_logged_in_result_callback(self):
        from sc_agent.testing import FakeRun
        detail = {"id": "http.network", "category": "network", "message": "controlled connection failure"}
        run = FakeRun({"provider": "local", "run_id": "test-run", "envelopes": [{"ok": False, "error": detail}]})
        line = request_line("s1", "text", ("cur", PLAN_QS["questions"]))
        settings = jj.BatchSettings("plan", 1, "p", 0.6, False)
        outcome = jj.judge_batch(run, [line], settings, fixture=None, echo=False)
        self.assertTrue(outcome.ok, outcome)
        self.assertEqual(len(run.logged), 1)
        self.assertFalse(run.logged[0]["fields"]["ok"])
        self.assertEqual(run.logged[0]["fields"]["error"]["code"], "DECIDR.NETWORK")

    def test_bad_input_is_refused_before_any_line(self):
        def refused(lines_text, *extra):
            code, out = run_cli(["batch", "--input", self.put("bad.jsonl", lines_text), "--dry-run", *extra])
            self.assertEqual((code, out["success"]), (2, False), out)
            return out["error"]["code"]
        good = jsonl(self.LINES)
        self.assertEqual(refused(good + "{not json\n"), "INPUT.MALFORMED")
        self.assertEqual(refused(jsonl([request_line("s1", "x", ("c", PLAN_QS["questions"]), ("c", PLAN_QS["questions"]))])), "VALIDATION.INPUT")
        self.assertEqual(refused(good + jsonl(self.LINES[:1])), "VALIDATION.INPUT")  # the same request twice
        self.assertEqual(refused(jsonl([request_line("bad id", "x", ("c", PLAN_QS["questions"]))])), "VALIDATION.INPUT")
        self.assertEqual(refused("\n"), "INPUT.EMPTY")
        self.assertFalse((self.d / "runs").exists())



    def test_live_auth_failure_is_reported_from_the_typed_wheel_error(self):
        from sc_agent.testing import fake_open_run
        error = {"id": "auth.credentials", "category": "auth", "message": "credential unavailable"}
        src = self.put("in.jsonl", jsonl([request_line("s1", "text", ("cur", PLAN_QS["questions"]))]))
        stdout, stderr = io.StringIO(), io.StringIO()
        with fake_open_run(jj.decidr_client, {"provider": "local", "run_id": "test-run", "envelopes": [{"ok": False, "error": error}]}), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = jj.main(["batch", "--input", src])
        line, = [json.loads(raw) for raw in stdout.getvalue().splitlines()]
        self.assertEqual((code, line["error"]["code"], json.loads(stderr.getvalue())["error"]["code"]),
                         (2, "AUTH.CREDENTIALS", "AUTH.CREDENTIALS"))

    def test_batch_summary_keeps_auth_cause_after_other_requests_are_canceled(self):
        from sc_agent.testing import fake_open_run
        auth = {"id": "auth.credentials", "category": "auth", "message": "credential unavailable", "action": "Set credentials."}
        canceled = {"id": "decision.cancelled", "category": "cancelled", "message": "the request was cancelled"}
        src = self.put("in.jsonl", jsonl([request_line("s1", "text", *[(f"c{i}", PLAN_QS["questions"]) for i in range(4)])]))
        for auth_position in (0, 1, 2, 3, None):
            with self.subTest(auth_position=auth_position):
                envelopes = [{"ok": False, "error": auth if i == auth_position else canceled} for i in range(4)]
                stdout, stderr = io.StringIO(), io.StringIO()
                with fake_open_run(jj.decidr_client, {"provider": "local", "run_id": "test-run", "envelopes": envelopes}), \
                        contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = jj.main(["batch", "--input", src])
                lines = [json.loads(raw) for raw in stdout.getvalue().splitlines()]
                summary = json.loads(stderr.getvalue())
                cause = lines[auth_position if auth_position is not None else 0]
                self.assertEqual((code, len(lines), summary["unanswered"]), (2, 4, 4))
                self.assertEqual((summary["request_id"], summary["error"]), (cause["request_id"], cause["error"]))
                self.assertEqual(summary["error"]["code"], "AUTH.CREDENTIALS" if auth_position is not None else "CANCELED")


if __name__ == "__main__":
    unittest.main()
