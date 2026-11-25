"""Issue #137: the REQ / NFR gate asks term (yes/no) and checkable in wave-1, and joined_by in an ``only_matched`` wave-2.

Engine: an ``only_matched`` per-statement wave asks only the statements the branch rule that led to it matched; the flag
is refused on a wave that is not per statement; the TTL form (``jj:onlyMatched``) compiles to the same JSON.

Regression from data: ``docs/evidence/issue-137-gate-fix/gate-runs.json`` holds three real Jev runs per record under the
0.7 tree (``ship``) and the prototype of the new tree (``proto``), statement text omitted. Its per-run confidences and
runner-ups become fixture answers on synthetic statements (no record text); each run goes through ``jev_judge.py
quality`` and the three result files through the installed ``jev_gate.py``. Jev is never called.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from child_support import run_child
from jev_support import ROOT, read_log
from layout_support import SCRIPTS
import jev_graph  # noqa: E402
import jev_judge as jj  # noqa: E402
from result import Ok  # noqa: E402

from test_jev_judge import answer, write  # noqa: E402
import test_quality  # noqa: E402 - the module, so its test classes are not collected again here
from test_quality import INDEX, QUESTIONS, QualityCase, requirement, tree_answers  # noqa: E402
from test_graph_tree import write as write_text  # noqa: E402

GATE = SCRIPTS / "jev_gate.py"
EVIDENCE = json.loads((ROOT / "docs" / "evidence" / "issue-137-gate-fix" / "gate-runs.json").read_text(encoding="utf-8"))["records"]
SHIPPED_REQ = json.loads((QUESTIONS / "quality-req.json").read_text(encoding="utf-8"))


def old_shape_tree():
    """The 0.7 REQ tree shape (origin/develop before #137): one per-statement wave asking obligations, joined_by, term
    and check, with its verdict rules. Built from the new tree's questions: the old term and check questions live on as
    the d_term_kind and d_check_method diagnostics with the same options."""
    w1, w2 = SHIPPED_REQ["nodes"]["wave-1"], SHIPPED_REQ["nodes"]["wave-2"]
    q = w1["questions"]
    return {"id": "quality-req-0.7-shape", "kind": "req", "start": "wave-1", "nodes": {"wave-1": {
        "per": "statement", "statements": w1["statements"], "modals": w1["modals"],
        "questions": {"obligations": q["obligations"], "joined_by": w2["questions"]["joined_by"],
                      "term": q["d_term_kind"], "check": q["d_check_method"]},
        "verdict_rules": [
            {"all": {"obligations": ["2", "3", "4+"], "joined_by": ["and-list", "alternatives", "obligation+rationale"]}, "verdict": "no"},
            {"any": {"term": ["project term defined nowhere", "vague qualifier", "undefined acronym"],
                     "check": ["needs a measure", "none"]}, "verdict": "no"},
            {"verdict": "yes"}]}}}


def measured(choice, confidence, options, runner_up=None, runner_up_p=None):
    """A fixture answer with the measured confidence and runner-up; the rest of the mass is spread over the other
    options. With no other option left the runner-up takes 1 - confidence, so the table sums to 1 as answers must."""
    rest = [o for o in options if o not in (choice, runner_up)]
    probs = {o: 0.0 for o in options}
    probs[choice] = confidence
    if runner_up is not None:
        probs[runner_up] = runner_up_p if rest else round(1 - confidence, 4)
    left = max(round(1 - sum(probs.values()), 4), 0.0)
    for o in rest:
        probs[o] = round(left / len(rest), 4)
    return {"type": "choice", "choice": choice, "confidence": confidence, "probabilities": probs}


def evidence_answers(record, tree, statement, run, questions):
    """``{question id: fixture answer}`` for ``questions`` (a wave's question objects) from run ``run`` (0..2) of
    ``statement`` of ``record`` under ``tree`` ('ship' or 'proto'); a question the evidence lacks (a diagnostic) gets
    its first option at 0.9."""
    found = {a["question"]: a for a in EVIDENCE[record][tree]["answers"] if a["statement"] == statement}
    out = {}
    for qid, question in questions.items():
        options = list(question["criteria"])
        a = found.get(qid)
        if a is None:
            out[qid] = answer(options[0], p=0.9, options=options)
        else:
            out[qid] = measured(a["choice"], a["runs"][run], options, a["runner_up"], a["runner_up_p"])
    return out


class GateRuns(QualityCase):
    """Three quality runs of synthetic records driven by the evidence, then jev_gate.py over the three result files."""

    RECORDS = {"REQ-X-0018": 1, "REQ-X-0019": 1, "REQ-X-0014": 1, "REQ-X-0602": 3}

    def setUp(self):
        super().setUp()
        records = [requirement(rid, *[f"Statement {i} of {rid} MUST hold (text omitted)." for i in range(1, n + 1)])
                   for rid, n in self.RECORDS.items()]
        self.index = write(self.d, "index.json", {**INDEX, "requirements": records})

    def runs(self, record_id, statements, tree, questions_file=None):
        """Three quality runs; ``statements`` maps the synthetic statement index to the evidence's (record, index).
        Returns the three result envelopes' results and the gate's record."""
        nodes = json.loads((questions_file or (QUESTIONS / "quality-req.json")).read_text(encoding="utf-8"))["nodes"]
        waves = {nid: n for nid, n in nodes.items() if "questions" in n}
        files, results = [], []
        for run in range(3):
            answers = {f"{record_id}.s{index}/{nid}": evidence_answers(source, tree, at, run, wave["questions"])
                       for index, (source, at) in statements.items() for nid, wave in waves.items()}
            extra = ["--questions", str(questions_file)] if questions_file else []
            code, out = self.quality("--req", record_id, *extra, answers=answers)
            self.assertEqual(code, 0, out)
            files.append(write(self.d, f"run-{record_id}-{tree}-{run}.json", out))
            results.append(out["data"]["results"][0])
        proc = run_child([sys.executable, str(GATE), *files], text=True, encoding="utf-8")
        self.assertEqual((proc.returncode, proc.stderr), (0, ""), proc.stdout)
        data = json.loads(proc.stdout)["data"]
        (record,) = data["records"]
        return results, record

    def old_tree_file(self):
        return Path(write(self.d, "old-shape.json", old_shape_tree()))

    def test_a_check_split_between_two_acceptable_methods_fails_the_old_gate_and_passes_checkable(self):
        # REQ-SAG-0018 statement 5 under the 0.7 tree: check = unit test at 0.42 / 0.56 / 0.49, runner-up inspection or grep
        results, record = self.runs("REQ-X-0018", {1: ("REQ-SAG-0018", 5)}, "ship", self.old_tree_file())
        self.assertEqual([r["verdict"] for r in results], ["yes"] * 3)
        self.assertFalse(record["pass"])
        self.assertEqual([(low["question"], low["choice"], low["median"]) for low in record["low"]], [("check", "unit test", 0.49)])
        self.assertEqual(record["lowest"]["runner_up"]["choice"], "inspection or grep")
        # the same statement under the new tree: checkable = yes at 0.98 in every run
        results, record = self.runs("REQ-X-0018", {1: ("REQ-SAG-0018", 5)}, "proto")
        self.assertEqual([(r["verdict"], r["path"]) for r in results], [("yes", ["wave-1", "yes"])] * 3)
        self.assertTrue(record["pass"], record)
        gated = {a["question"]: (a["choice"], a["median"]) for a in record["answers"]}
        self.assertEqual(gated, {"checkable": ("yes", 0.98), "obligations": ("1", 1.0), "term": ("yes", 0.84)})

    def test_a_single_obligation_is_not_asked_joined_by_and_joined_by_does_not_gate_it(self):
        # REQ-SAG-0019 statement 6 under the 0.7 tree: obligations 1, joined_by condition+obligation at 0.39 / 0.40 / 0.44
        results, record = self.runs("REQ-X-0019", {1: ("REQ-SAG-0019", 6)}, "ship", self.old_tree_file())
        self.assertFalse(record["pass"])
        self.assertEqual([(low["question"], low["median"]) for low in record["low"]], [("joined_by", 0.4)])
        # under the new tree the answers file still holds that low joined_by answer for wave-2, but wave-2 is never asked
        old_join = {a["question"]: a for a in EVIDENCE["REQ-SAG-0019"]["ship"]["answers"] if a["statement"] == 6}["joined_by"]
        self.assertEqual(old_join["median"], 0.4)
        results, record = self.runs("REQ-X-0019", {1: ("REQ-SAG-0019", 6)}, "proto")
        self.assertEqual([(r["verdict"], r["path"], [w["node"] for w in r["waves"]]) for r in results],
                         [("yes", ["wave-1", "yes"], ["wave-1"])] * 3)
        self.assertNotIn("joined_by", {a["question"] for a in record["answers"]})
        requested = [e["fields"]["request_id"] for e in read_log(self.d / "logs", action="request")]
        self.assertIn("quality/REQ-X-0019.s1/wave-1/r1", requested)
        self.assertFalse([r for r in requested if r.startswith("quality/REQ-X-0019.") and "/wave-2/" in r], requested)
        self.assertTrue(record["pass"], record)

    def test_control_checkable_needs_a_measure_is_still_no(self):
        # REQ-SAG-0014 statement 1: checkable = needs a measure in every run
        results, record = self.runs("REQ-X-0014", {1: ("REQ-SAG-0014", 1)}, "proto")
        self.assertEqual([(r["verdict"], r["path"], r["waves"][0]["matched_statements"]) for r in results],
                         [("no", ["wave-1", "no"], [1])] * 3)
        self.assertEqual({a["question"]: a["choice"] for a in record["answers"]}["checkable"], "needs a measure")
        self.assertFalse(record["pass"])

    def test_control_term_no_is_still_no(self):
        # REQ-SAG-0602 statements 1-3: statement 1 term = no in every run
        statements = {i: ("REQ-SAG-0602", i) for i in (1, 2, 3)}
        results, record = self.runs("REQ-X-0602", statements, "proto")
        self.assertEqual([(r["verdict"], r["path"], r["waves"][0]["matched_statements"]) for r in results],
                         [("no", ["wave-1", "no"], [1])] * 3)
        self.assertEqual({(a["statement"], a["question"]): a["choice"] for a in record["answers"]}[(1, "term")], "no")
        self.assertFalse(record["pass"])


class OnlyMatched(QualityCase):
    def judge(self, questions=None):
        answers = {"REQ-T-0001.s1/wave-1": tree_answers("quality-req.json", obligations="2"),
                   "REQ-T-0001.s3/wave-1": tree_answers("quality-req.json"),
                   "REQ-T-0001.s1/wave-2": tree_answers("quality-req.json", "wave-2", joined_by="and-list"),
                   "REQ-T-0001.s3/wave-2": tree_answers("quality-req.json", "wave-2")}
        extra = ["--questions", questions] if questions else []
        code, out = self.quality("--req", "REQ-T-0001", *extra, answers=answers)
        self.assertEqual(code, 0, out)
        requested = [e["fields"]["request_id"] for e in read_log(self.d / "logs", action="request")]
        return out["data"]["results"][0], requested

    def test_wave_2_asks_only_the_statements_the_obligations_rule_matched(self):
        result, requested = self.judge()
        self.assertEqual(requested, ["quality/REQ-T-0001.s1/wave-1/r1", "quality/REQ-T-0001.s3/wave-1/r1",
                                     "quality/REQ-T-0001.s1/wave-2/r1"])
        wave1, wave2 = result["waves"]
        self.assertEqual((wave1["next"], wave1["matched_statements"]), ("wave-2", [1]))
        self.assertEqual(([r["statement"]["index"] for r in wave2["reason"]], wave2["matched_statements"], result["verdict"]),
                         ([1], [1], "no"))

    def test_without_only_matched_wave_2_asks_every_statement(self):
        tree = copy.deepcopy(SHIPPED_REQ)
        del tree["nodes"]["wave-2"]["only_matched"]
        _result, requested = self.judge(write(self.d, "all.json", tree))
        self.assertEqual(requested[2:], ["quality/REQ-T-0001.s1/wave-2/r1", "quality/REQ-T-0001.s3/wave-2/r1"])

    def test_only_matched_on_a_wave_that_is_not_per_statement_is_refused(self):
        tree = copy.deepcopy(test_quality.TreeOverride.TREE)
        tree["nodes"]["w2"]["only_matched"] = True
        code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "bad.json", tree), "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"), out)
        self.assertIn("only_matched needs per statement", out["error"]["message"])
        parsed = jj.parse_quality_tree(json.dumps(tree), "bad.json", True)
        self.assertEqual(parsed.error.code, "QUALITY.TREE")


class OnlyMatchedTtl(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.dir = scratch.name

    def test_the_shipped_ttl_trees_compile_to_the_shipped_json_trees_with_only_matched(self):
        for kind in ("req", "nfr"):
            with self.subTest(kind):
                loaded = jev_graph.load_tree(str(QUESTIONS / f"quality-{kind}.ttl"))
                self.assertIsInstance(loaded, Ok)
                converted = jev_graph.tree_to_quality_json(loaded.value)
                expected = json.loads((QUESTIONS / f"quality-{kind}.json").read_text(encoding="utf-8"))
                self.assertEqual(converted, expected)
                self.assertIs(converted["nodes"]["wave-2"]["only_matched"], True)
                self.assertNotIn("only_matched", converted["nodes"]["wave-1"])

    def test_jj_only_matched_compiles_to_only_matched_and_needs_per(self):
        ttl = (QUESTIONS / "quality-req.ttl").read_text(encoding="utf-8")
        self.assertEqual(ttl.count("jj:onlyMatched true ;"), 1)
        without = ttl.replace("    jj:onlyMatched true ;\n", "")
        converted = jev_graph.tree_to_quality_json(jev_graph.load_tree(write_text(self.dir, without, "without.ttl")).value)
        self.assertNotIn("only_matched", converted["nodes"]["wave-2"])
        expected = copy.deepcopy(SHIPPED_REQ)
        del expected["nodes"]["wave-2"]["only_matched"]
        self.assertEqual(converted, expected)
        # jj:onlyMatched on a wave without jj:per is refused by the shapes
        from test_graph_tree import BRANCH_TTL
        bad = BRANCH_TTL.replace('t:b:wave-1 a jj:Wave ; jj:id "wave-1" ;', 't:b:wave-1 a jj:Wave ; jj:id "wave-1" ; jj:onlyMatched true ;')
        self.assertNotEqual(bad, BRANCH_TTL)
        tree = jev_graph.load_tree(write_text(self.dir, bad, "bad.ttl"))
        refused = jev_graph.validate_tree(tree.value) if isinstance(tree, Ok) else tree
        self.assertEqual(refused.error.code, "QUALITY.TREE")
        self.assertIn("onlyMatched", refused.error.message)
        good = BRANCH_TTL.replace('t:b:wave-2 a jj:Wave ; jj:id "wave-2" ;', 't:b:wave-2 a jj:Wave ; jj:id "wave-2" ; jj:onlyMatched true ;')
        compiled = jev_graph.tree_to_quality_json(jev_graph.load_tree(write_text(self.dir, good, "good.ttl")).value)
        self.assertIs(compiled["nodes"]["wave-2"]["only_matched"], True)


if __name__ == "__main__":
    unittest.main()
