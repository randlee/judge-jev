"""`jev_judge.py validate` (REQ-JEV-0210), the field paths of model refusals (ADR-JEV-0005), invalid UTF-8 on stdin, and
the log-event size check made before any request (REQ-JEV-0211). Jev is never called; nothing here sleeps or times."""
import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jev_support import SCRIPTS
import test_quality as tq
from test_jev_judge import env, jsonl, request_line, run_cli, write

jj = tq.jj
SHIPPED_TREES = ("quality-req.json", "quality-adr.json", "quality-nfr.json")


def validate(*argv):
    """Run `validate` in-process with no key, no consent and Jev, the run log and the key lookup all forbidden."""
    with env(), mock.patch.object(jj, "call_jev", tq.never_called), \
            mock.patch.object(jj, "open_run_log", side_effect=AssertionError("validate wrote a log")), \
            mock.patch.object(jj, "resolved_api_key", side_effect=AssertionError("validate read the key")):
        return run_cli(["validate", *argv])


class ValidateKinds(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)

    def accepted(self, flag, path, kind):
        code, out = validate(flag, str(path))
        self.assertEqual((code, out["success"], out["error"]), (0, True, None), out)
        digest = hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        self.assertEqual(out["data"], {"kind": kind, "path": str(path), "sha256": digest})

    def refused(self, flag, path, code_name):
        code, out = validate(flag, str(path))
        self.assertEqual((code, out["success"], out["data"], out["error"]["code"]), (2, False, None, code_name), out)
        return out["error"]["message"]

    def test_shipped_trees_and_question_sets_pass(self):
        for name in SHIPPED_TREES:
            self.accepted("--tree", tq.QUESTIONS / name, "tree")
        for name in ("plan.json", "dev.json"):
            self.accepted("--questions", tq.QUESTIONS / name, "questions")

    def test_index_answers_and_requests_pass(self):
        self.accepted("--index", write(self.d, "index.json", tq.INDEX), "index")
        self.accepted("--answers", write(self.d, "answers.json", {"ADR-T-0001/wave-1": tq.tree_answers("quality-adr.json"), "*": {}}), "answers")
        fixture = {"a/c/r1": [{"__error__": "JEV.NETWORK"}, tq.tree_answers("quality-adr.json")], "n": {"q": {"noul": 0.3}}}
        self.accepted("--answers", write(self.d, "fixture.json", fixture), "answers")
        self.accepted("--requests", write(self.d, "requests.jsonl", jsonl([request_line(), request_line("ex-43")])), "requests")

    def test_each_kind_refuses_what_its_command_refuses(self):
        tree = json.loads((tq.QUESTIONS / "quality-adr.json").read_text(encoding="utf-8"))
        tree["nodes"]["wave-1"]["next"] = [{"goto": "wave-1"}]  # both next and verdict_rules
        self.refused("--tree", write(self.d, "t.json", tree), "QUALITY.TREE")
        plan = json.loads((tq.QUESTIONS / "plan.json").read_text(encoding="utf-8"))
        plan["roles"]["conflict"] = "nope"
        self.refused("--questions", write(self.d, "q.json", plan), "QUESTIONS.ROLES")
        self.refused("--index", write(self.d, "i.json", {"requirements": []}), "INPUT.MALFORMED")
        # the answers file is Jev's response stand-in: only its envelope is refused here (an answer's body is checked after the send)
        self.refused("--answers", write(self.d, "a.json", {"k": ["x"]}), "INPUT.MALFORMED")
        self.refused("--requests", write(self.d, "r.jsonl", jsonl([{"item": {"id": "x"}}])), "VALIDATION.INPUT")
        self.refused("--requests", write(self.d, "bad.jsonl", "{nope\n"), "INPUT.MALFORMED")
        self.refused("--tree", str(self.d / "missing.json"), "INPUT.MISSING")

    def test_exactly_one_input_kind(self):
        for argv in ([], ["--tree", "a", "--index", "b"]):
            code, out = validate(*argv)
            self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), argv)

    def test_stdin_is_dash(self):
        text = (tq.QUESTIONS / "quality-nfr.json").read_text(encoding="utf-8")
        with mock.patch.object(sys, "stdin", io.StringIO(text)):
            code, out = validate("--tree", "-")
        self.assertEqual((code, out["data"]["kind"], out["data"]["path"], out["data"]["sha256"]),
                         (0, "tree", "-", hashlib.sha256(text.encode("utf-8")).hexdigest()), out)

    def test_requests_use_the_gate_and_cap_batch_uses(self):
        big = write(self.d, "big.jsonl", jsonl([request_line(text="x" * 30000)]))
        self.assertIn("over --max-request-bytes 24000", self.refused("--requests", big, "JEV.CONTEXT_EXCEEDED"))
        dev = write(self.d, "dev.jsonl", jsonl([request_line(text="x" * 30000, questions=jj.load_question_set("dev").value.questions)]))
        code, out = validate("--requests", dev, "--gate", "dev")  # the dev gate's cap is larger
        self.assertEqual(code, 0, out)
        self.assertEqual(validate("--requests", big, "--gate", "dev")[1]["error"]["code"], "QUESTIONS.ROLES")  # plan questions, dev roles
        code, out = validate("--requests", big, "--max-request-bytes", "70000")
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), out)

    def test_raw_json_no_value_can_express_is_input_malformed(self):
        tree_text = (tq.QUESTIONS / "quality-adr.json").read_text(encoding="utf-8")
        for name, raw in (("NaN", "NaN"), ("Infinity", "Infinity"), ("big int", "9" * 5000), ("deep", "[" * 50000 + "]" * 50000),
                          ("lone surrogate", '"\\ud800"')):
            path = write(self.d, "t.json", tree_text.replace('"approved": false', f'"approved": {raw}', 1))
            with self.subTest(name):
                self.refused("--tree", path, "INPUT.MALFORMED")


class FieldPaths(unittest.TestCase):
    """Every model refusal names the field path and the rule it breaks (REQ-JEV-0210)."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        self.adr = json.loads((tq.QUESTIONS / "quality-adr.json").read_text(encoding="utf-8"))

    def message(self, flag, value, code_name):
        code, out = validate(flag, write(self.d, "input.json", value))
        self.assertEqual((code, out["error"]["code"]), (2, code_name), out)
        return out["error"]["message"]

    def tree_message(self, mutate):
        tree = copy.deepcopy(self.adr)
        mutate(tree["nodes"]["wave-1"])
        return self.message("--tree", tree, "QUALITY.TREE")

    def test_tree_paths(self):
        one = self.tree_message(lambda w: w["questions"]["context"].__setitem__("criteria", {"only": "one"}))
        self.assertIn("nodes.wave-1.questions.context.criteria:", one)
        self.assertIn("at least 2", one)
        blank = self.tree_message(lambda w: w["questions"]["context"].__setitem__("instructions", " "))
        self.assertIn("nodes.wave-1.questions.context.instructions: ", blank)
        self.assertIn("must not be blank", blank)
        bad_id = self.tree_message(lambda w: w["questions"].__setitem__("bad id", w["questions"]["context"]))
        self.assertIn("nodes.wave-1.questions.bad id", bad_id)
        stray = self.tree_message(lambda w: w.__setitem__("goto", "x"))
        self.assertIn("nodes.wave-1.goto: Extra inputs are not permitted", stray)
        choice = self.tree_message(lambda w: w["verdict_rules"][0]["any"].__setitem__("context", ["nope"]))
        self.assertIn("nodes.wave-1: verdict_rules[0].any.context: 'nope' is not an option of question 'context'", choice)
        last = self.tree_message(lambda w: w["verdict_rules"].__setitem__(-1, {"any": {"context": "missing"}, "verdict": "x"}))
        self.assertIn("nodes.wave-1: the last verdict_rules rule must have no any or all", last)

    def test_tree_graph_paths(self):
        two = copy.deepcopy(self.adr)
        two["nodes"]["wave-1"] = {"questions": two["nodes"]["wave-1"]["questions"], "next": [{"goto": "nope"}]}
        self.assertIn("nodes.wave-1.next[0].goto: 'nope' is not a node", self.message("--tree", two, "QUALITY.TREE"))
        loop = copy.deepcopy(self.adr)
        loop["nodes"]["wave-1"] = {"questions": loop["nodes"]["wave-1"]["questions"], "next": [{"goto": "wave-1"}]}
        self.assertIn("can lead back to itself", self.message("--tree", loop, "QUALITY.TREE"))
        leaf = copy.deepcopy(self.adr)
        leaf["start"] = "end"
        leaf["nodes"]["end"] = {"verdict": "no", "next": []}
        self.assertIn("nodes.end.next: Extra inputs are not permitted", self.message("--tree", leaf, "QUALITY.TREE"))

    def test_question_set_index_answers_and_request_paths(self):
        plan = json.loads((tq.QUESTIONS / "plan.json").read_text(encoding="utf-8"))
        plan["roles"]["compliance"] = "gone"
        self.assertIn("must map role 'compliance' to a question id in the set", self.message("--questions", plan, "QUESTIONS.ROLES"))
        plan = json.loads((tq.QUESTIONS / "plan.json").read_text(encoding="utf-8"))
        plan["questions"] = {}
        self.assertIn("questions: Dictionary should have at least 1 item", self.message("--questions", plan, "INPUT.MALFORMED"))
        index = copy.deepcopy(tq.INDEX)
        index["diagnostics"]["issues"] = "none"
        self.assertIn("diagnostics.issues: Input should be a valid list", self.message("--index", index, "INPUT.MALFORMED"))
        index = copy.deepcopy(tq.INDEX)
        del index["decisions"][0]["id"]
        self.assertIn("decisions.0: needs a string id", self.message("--index", index, "INPUT.MALFORMED"))
        answers = {"ADR/wave-1": {"context": {"type": "choice", "choice": "a", "confidence": 2, "probabilities": {"a": 1}}}}
        self.assertEqual(validate("--answers", write(self.d, "body.json", answers))[0], 0)  # a bad answer body is JEV.RESPONSE_INVALID after the send
        listed = {"k": [{"__error__": "X"}, {"__error__": 7}]}
        self.assertIn("k.1: __error__: Input should be a valid string", self.message("--answers", listed, "INPUT.MALFORMED"))
        line = request_line()
        line["item"]["id"] = "bad id"
        code, out = validate("--requests", write(self.d, "r.jsonl", jsonl([line])))
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))
        self.assertIn("request line 1: item.id: must be letters, digits and _.:- only", out["error"]["message"])

    def test_the_command_that_reads_the_input_gives_the_same_message(self):
        tree = copy.deepcopy(self.adr)
        tree["nodes"]["wave-1"]["questions"]["context"]["criteria"] = {}
        path = write(self.d, "t.json", tree)
        _code, said = validate("--tree", path)
        index = write(self.d, "index.json", tq.INDEX)
        with env(), mock.patch.object(jj, "call_jev", tq.never_called):
            _code, ran = run_cli(["quality", "--adr", "ADR-T-0001", "--index", index, "--questions", path, "--dry-run"])
        self.assertEqual((ran["error"]["code"], ran["error"]["message"]), (said["error"]["code"], said["error"]["message"]))

    def test_a_long_list_of_problems_is_capped(self):
        tree = copy.deepcopy(self.adr)
        for qid in list(tree["nodes"]["wave-1"]["questions"]):
            tree["nodes"]["wave-1"]["questions"][qid]["x"] = 1
            tree["nodes"]["wave-1"]["questions"][qid]["y"] = 1
        message = self.message("--tree", tree, "QUALITY.TREE")
        self.assertIn("; and 1 more", message)
        self.assertLess(len(message), 2500)


class StdinIsNeverACrash(unittest.TestCase):
    """QA finding C1: invalid UTF-8 on stdin was SCRIPT.INTERNAL."""

    BAD = b"\xff\xfe{"

    def run_script(self, *argv):
        proc = subprocess.run([sys.executable, str(SCRIPTS / "jev_judge.py"), *argv], input=self.BAD, capture_output=True, timeout=120)
        self.assertNotIn(b"Traceback", proc.stderr)
        return proc.returncode, json.loads(proc.stdout.decode("utf-8"))

    def test_index_on_stdin(self):
        code, out = self.run_script("quality", "--adr", "ADR-T-0001", "--index", "-", "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MALFORMED"), out)
        self.assertIn("on stdin", out["error"]["message"])

    def test_every_kind_of_validate_on_stdin(self):
        for flag in ("--tree", "--questions", "--answers", "--index", "--requests"):
            with self.subTest(flag):
                code, out = self.run_script("validate", flag, "-")
                self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MALFORMED"), out)

    def test_batch_input_on_stdin(self):
        with tempfile.TemporaryDirectory() as td:
            code, out = self.run_script("batch", "--run-dir", td, "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MALFORMED"), out)

    def test_in_process_text_stream_with_invalid_utf8(self):
        stream = io.TextIOWrapper(io.BytesIO(self.BAD), encoding="utf-8")
        with mock.patch.object(sys, "stdin", stream):
            code, out = validate("--index", "-")
        self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MALFORMED"), out)

    def test_closed_stdin(self):
        with mock.patch.object(sys, "stdin", None):
            code, out = validate("--index", "-")
        self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MALFORMED"), out)


class LogEventLimit(unittest.TestCase):
    """REQ-JEV-0211: every log event of a request is sized the way the sc-observability logger sizes it, before the request is sent."""

    def setUp(self):
        import sc_observability as sco
        self.sco = sco
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        self.limit = sco.AdapterPolicy().max_request_bytes

    def logger_accepts(self, fields):
        created = self.sco.create_logger(self.sco.LoggerConfig(service="judge-jev", log_root=str(self.d / "log")))
        self.assertNotIsInstance(created, self.sco.Err)
        try:
            got = created.value.log(self.sco.LogEvent(level="info", target=jj.LOG_TARGET, action="request", correlation_id="c",
                                                      fields={"run": jj.LOG_RUN_NAME_WORST, **fields}))
        finally:
            created.value.shutdown()
        return not isinstance(got, self.sco.Err) and got.value.kind == "accepted"

    def size(self, fields):
        got = jj.log_event_size(self.sco, "request", fields, "c")
        self.assertIsInstance(got, jj.Ok)
        return got.value

    def test_the_measure_is_the_loggers_at_its_boundary(self):
        shapes = {"ascii": lambda n: {"x": "a" * n}, "escaped": lambda n: {"x": "é" * n}, "nested": lambda n: {"x": {"k": ["v"] * n}},
                  "numbers": lambda n: {"x": [1] * n}}
        for name, make in shapes.items():
            lo, hi = 0, 100000  # the largest n whose event the measure keeps within the limit (bisection on the measure alone)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                lo, hi = (mid, hi) if self.size(make(mid)) <= self.limit else (lo, mid - 1)
            with self.subTest(name):
                self.assertLessEqual(self.size(make(lo)), self.limit)
                self.assertGreater(self.size(make(lo + 1)), self.limit)
                self.assertTrue(self.logger_accepts(make(lo)), "the logger refused an event the measure accepts")
                self.assertFalse(self.logger_accepts(make(lo + 1)), "the logger accepted an event the measure refuses")

    def adr_with_questions(self, questions, options):
        tree = json.loads((tq.QUESTIONS / "quality-adr.json").read_text(encoding="utf-8"))
        tree["nodes"]["wave-1"] = {"questions": {f"q{i}": {"type": "choice", "instructions": "Q", "criteria": {f"o{j}": "d" for j in range(options)}}
                                                 for i in range(questions)}, "verdict_rules": [{"verdict": "yes"}]}
        return tree

    def quality(self, tree, *mode):
        index = write(self.d, "index.json", tq.INDEX)
        sent = []
        with env(), mock.patch.object(jj, "call_jev", tq.never_called), \
                mock.patch.object(jj, "pump_batch", side_effect=lambda *a, **k: sent.append(a) or AssertionError("sent")):
            code, out = run_cli(["quality", "--adr", "ADR-T-0001", "--index", index, "--questions", write(self.d, "tree.json", tree),
                                 "--run-dir", str(self.d / "logs"), "--run-name", "c2", *mode])
        self.assertEqual(sent, [], "a request was sent")
        self.assertFalse((self.d / "logs").exists(), "the run log was opened")
        return code, out

    def test_c2_a_tree_whose_request_fits_but_whose_log_events_do_not_is_refused_before_any_call(self):
        tree = self.adr_with_questions(7, 255)
        line = jj.wave_line(tq.INDEX["decisions"][0], "wave-1", jj.parse_quality_tree(json.dumps(tree), "t").value.nodes["wave-1"])
        size = len(jj.encode_body({"model": jj.DEFAULT_MODEL, "state": {"item": line["item"]}, "questions": line["questions"][0]["questions"]}))
        self.assertLessEqual(size, jj.DEFAULT_MAX_REQUEST_BYTES, "the request itself must fit --max-request-bytes")
        answers = write(self.d, "answers.json", {"*": {}})
        for mode in (["--dry-run"], ["--answers-file", answers]):
            with self.subTest(mode=mode[0]):
                code, out = self.quality(tree, *mode)
                self.assertEqual((code, out["error"]["code"]), (2, "JEV.CONTEXT_EXCEEDED"), out)
                message = out["error"]["message"]
                self.assertRegex(message, r"the (request|answer|result) log event would be \d+ bytes, over the run log's 65536-byte event limit")
                self.assertIn("ADR-T-0001/wave-1", message)

    def test_the_answer_event_is_the_one_named_when_only_the_answer_is_too_big(self):
        code, out = self.quality(self.adr_with_questions(6, 255), "--dry-run")
        self.assertEqual(out["error"]["code"], "JEV.CONTEXT_EXCEEDED", out)
        self.assertIn("log event would be", out["error"]["message"])

    def test_a_tree_within_the_limit_still_runs(self):
        tree = self.adr_with_questions(3, 20)
        index = write(self.d, "index.json", tq.INDEX)
        with env(), mock.patch.object(jj, "call_jev", tq.never_called):
            code, out = run_cli(["quality", "--adr", "ADR-T-0001", "--index", index, "--questions", write(self.d, "tree.json", tree), "--dry-run"])
        self.assertEqual((code, out["success"]), (0, True), out)

    def test_worst_answers_are_answers_the_validator_accepts(self):
        questions = {qid: q.model_dump() for qid, q in jj.load_quality_tree("req").value.nodes["wave-1"].questions.items()}
        answers = jj.worst_answers(questions)
        self.assertIsInstance(jj.validate_response({"answers": answers}, questions), jj.Ok)

    def test_the_batch_command_refuses_the_same_way(self):
        big = {f"q{i}": {"type": "choice", "instructions": "Q", "criteria": {f"o{j}": "d" for j in range(255)}} for i in range(7)}
        line = request_line(questions=big)
        del line["anchor"]  # an anchorless line needs no roles
        src = write(self.d, "in.jsonl", jsonl([line]))
        with env(), mock.patch.object(jj, "call_jev", tq.never_called):
            code, out = run_cli(["batch", "--input", src, "--run-dir", str(self.d / "runs"), "--dry-run"])
        self.assertEqual((code, out["error"]["code"]), (2, "JEV.CONTEXT_EXCEEDED"), out)
        self.assertFalse((self.d / "runs").exists())


if __name__ == "__main__":
    unittest.main()
