"""`jev_judge.py quality`: one record from a Raptor import index, its kind's decision tree, one batch request per wave
(one per MUST / MUST NOT statement for a per-statement wave).

Answers come from answers files (keyed '<record>/<node>'); Jev is never called (call_jev is replaced with a stub that
fails the test). The run log is read back through sc-observability's query API.
"""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jev_support import ROOT, SKILL, read_log
import jev_judge as jj  # noqa: E402

from test_jev_judge import answer, env, run_cli, write  # noqa: E402

QUESTIONS = SKILL / "assets" / "questions"


def statement(text):
    """A statement string, optionally prefixed 'Should: ' or 'MustNot: ' for its modal (default Must)."""
    modal, _, rest = text.partition(": ")
    return {"modal": modal, "text": rest} if rest and modal in ("Should", "MustNot") else {"modal": "Must", "text": text}


def requirement(rid, *statements, criteria=("It works.",)):
    return {"id": rid, "title": f"Title of {rid}", "status": "Draft",
            "requirement_statement": {"text": "", "statements": [statement(s) for s in statements]},
            "rationale": "Because.", "success_criteria": {"text": "", "acceptance_criteria": [{"text": c, "checked": False} for c in criteria]}}


INDEX = {
    "metadata": {"repository": "urn:raptor:repo:test", "files": 1, "records": 4},
    "requirements": [requirement("REQ-T-0001", "The CLI MUST exit 2 on a missing file.", "Should: The CLI SHOULD be quick.",
                                 "MustNot: The CLI MUST NOT write outside the worktree."),
                     requirement("REQ-T-0002", "Broken record."),
                     {**requirement("NFR-T-0001", "A run MUST finish in 5 s."), "title": "Fast"}],
    "decisions": [{"id": "ADR-T-0001", "title": "Use SQLite", "decision": {"text": "Store records in SQLite."}}],
    "diagnostics": {"issues": [{"file": "docs/r.md", "line": 3, "column": 1, "rule": "MISSING_SECTION", "id": "REQ-T-0002",
                                "message": "Found None; expected rationale.", "remedy": "Add the section."}],
                    "summary": {"records": 4}},
}


def tree_node(node_file, node="wave-1"):
    return json.loads((QUESTIONS / node_file).read_text(encoding="utf-8"))["nodes"][node]


def tree_answers(node_file, node="wave-1", p=0.9, **choices):
    """Answers for every question of ``node`` in a shipped tree: its first (passing) option unless named in ``choices``."""
    questions = tree_node(node_file, node)["questions"]
    return {qid: answer(choices.get(qid, next(iter(q["criteria"]))), p=p, options=list(q["criteria"])) for qid, q in questions.items()}


def reason_entry(question_id, question, choice, confidence):
    return {"id": question_id, "text": question["instructions"], "choice": choice,
            "criterion": question["criteria"].get(choice, ""), "confidence": confidence}


JUDGED = [{"index": 1, "modal": "Must", "text": "The CLI MUST exit 2 on a missing file."},
          {"index": 3, "modal": "MustNot", "text": "The CLI MUST NOT write outside the worktree."}]  # REQ-T-0001's MUST / MUST NOT


def never_called(*args, **kwargs):
    raise AssertionError("Jev must not be called")


class QualityCase(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        self.index = write(self.d, "index.json", INDEX)

    def quality(self, *argv, answers=None):
        extra = ["--answers-file", write(self.d, "answers.json", answers)] if answers is not None else []
        with env(), mock.patch.object(jj, "call_jev", never_called):
            return run_cli(["quality", *argv, "--index", self.index, "--run-dir", str(self.d / "logs"), "--run-name", "q1", *extra])


class DryRun(QualityCase):
    def test_dry_run_reports_the_tree_record_and_wave_1_request_and_writes_nothing(self):
        code, out = self.quality("--adr", "ADR-T-0001", "--dry-run")
        self.assertEqual((code, out["success"], out["error"]), (0, True, None), out)
        (data,) = out["data"]["results"]
        shipped = QUESTIONS / "quality-adr.json"
        self.assertEqual(data["tree"], {"id": "quality-adr", "sha256": hashlib.sha256(shipped.read_bytes()).hexdigest(),
                                        "source": "shipped", "path": str(jj.QUESTIONS_DIR / "quality-adr.json")})
        self.assertEqual(data["record"], {"id": "ADR-T-0001", "kind": "adr", "source": {"raptor_index": self.index}})
        wave = data["wave"]
        self.assertEqual(wave["node"], "wave-1")
        # REQ-JEV-0209: the request carries only the record and the ADR tree's wave-1 questions
        self.assertEqual(set(wave["request"]), {"model", "state", "questions"})
        self.assertEqual(wave["request"]["questions"], tree_node("quality-adr.json")["questions"])
        self.assertEqual(wave["request"]["state"], {"item": {"id": "ADR-T-0001", "title": "Use SQLite",
                                                             "text": json.dumps(INDEX["decisions"][0], indent=2, ensure_ascii=False)}})
        self.assertEqual((wave["request_bytes"], wave["max_request_bytes"]), (len(jj.encode_body(wave["request"])), 24000))
        self.assertFalse((self.d / "logs").exists())

    def test_dry_run_of_a_per_statement_wave_shows_every_statements_request(self):
        code, out = self.quality("--req", "REQ-T-0001", "--dry-run")
        self.assertEqual(code, 0, out)
        wave = out["data"]["results"][0]["wave"]
        self.assertEqual((wave["node"], wave["per"], wave["max_request_bytes"]), ("wave-1", "statement", 24000))
        # one request per MUST / MUST NOT statement (the SHOULD at index 2 is not judged), each with all the wave's questions
        self.assertEqual([r["statement"] for r in wave["requests"]], JUDGED)
        record = INDEX["requirements"][0]
        for req, st in zip(wave["requests"], JUDGED):
            self.assertEqual(req["request"]["questions"], tree_node("quality-req.json")["questions"])
            self.assertEqual(req["request"]["state"], {"item": {
                "id": f"REQ-T-0001.s{st['index']}", "title": "Title of REQ-T-0001",
                "text": json.dumps({"statement": st, "record": record}, indent=2, ensure_ascii=False)}})
            self.assertEqual(req["request_bytes"], len(jj.encode_body(req["request"])))
        self.assertFalse((self.d / "logs").exists())

    def test_each_kind_uses_its_own_tree_and_table(self):
        for flag, rid, tree_id in (("--nfr", "NFR-T-0001", "quality-nfr"), ("--adr", "ADR-T-0001", "quality-adr")):
            code, out = self.quality(flag, rid, "--dry-run")
            (data,) = out["data"]["results"]
            self.assertEqual((code, data["tree"]["id"], data["record"]["id"]), (0, tree_id, rid), out)
        code, out = self.quality("--adr", "REQ-T-0001", "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "RECORD.NOT_FOUND"))

    def test_oversize_request_is_a_typed_error(self):
        big = {**INDEX, "requirements": [requirement("REQ-T-0001", "x" * 30000)]}
        self.index = write(self.d, "big.json", big)
        code, out = self.quality("--req", "REQ-T-0001", "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "JEV.CONTEXT_EXCEEDED"))

    def test_at_least_one_record_flag(self):
        code, out = run_cli(["quality", "--index", self.index, "--dry-run"])
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))


class RecordsWithDiagnostics(QualityCase):
    def test_a_record_raptor_rejected_is_not_sent_to_jev(self):
        answers = {"*": tree_answers("quality-req.json")}
        code, out = self.quality("--req", "REQ-T-0002", answers=answers)
        self.assertEqual((code, out["error"]["code"]), (2, "RECORD.DIAGNOSTICS"))
        self.assertEqual(out["data"]["diagnostics"], INDEX["diagnostics"]["issues"])
        self.assertFalse((self.d / "logs").exists())
        code, out = self.quality("--req", "REQ-T-0002", "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "RECORD.DIAGNOSTICS"))


class WaveReasons(QualityCase):
    """Every wave reports each question's answer as its reason; a wave without next ends with its tree's verdict_rules."""

    def test_every_wave_1_question_is_in_the_result_with_its_text_choice_criterion_and_confidence(self):
        questions = tree_node("quality-adr.json")["questions"]
        answers = {"ADR-T-0001/wave-1": {**tree_answers("quality-adr.json", p=0.8),
                                         "alternatives": answer("named only", p=0.6, options=list(questions["alternatives"]["criteria"]))}}
        code, out = self.quality("--adr", "ADR-T-0001", answers=answers)
        self.assertEqual(code, 0, out)
        (result,) = out["data"]["results"]
        (wave,) = result["waves"]
        expected = {"context": ("problem and forces", 0.8), "alternatives": ("named only", 0.6), "consequences": ("positive and negative", 0.8)}
        self.assertEqual(wave["reason"], [reason_entry(qid, q, *expected[qid]) for qid, q in questions.items()])
        self.assertIn("Fix: add why rejected", wave["reason"][1]["criterion"])  # the chosen option's fix hint is in the reason
        self.assertEqual((wave["node"], wave["next"], wave["verdict"]), ("wave-1", None, "no"))
        self.assertEqual((result["verdict"], result["path"]), ("no", ["wave-1"]))

    def test_the_verdict_comes_from_the_trees_rule(self):
        cases = (({}, "yes"), ({"context": "background only"}, "no"), ({"consequences": "positive only"}, "no"),
                 ({"alternatives": "none", "context": "missing"}, "no"))
        for choices, verdict in cases:
            answers = {"ADR-T-0001/wave-1": tree_answers("quality-adr.json", **choices)}
            code, out = self.quality("--adr", "ADR-T-0001", answers=answers)
            self.assertEqual(code, 0, out)
            self.assertEqual(out["data"]["results"][0]["verdict"], verdict, choices)

    def test_fixed_answers_compose_the_same_request_every_run(self):
        answers = {"*": tree_answers("quality-req.json")}
        logs = []
        for name in ("a", "b"):
            with env(), mock.patch.object(jj, "call_jev", never_called):
                code, out = run_cli(["quality", "--req", "REQ-T-0001", "--index", self.index, "--run-dir", str(self.d / name),
                                     "--answers-file", write(self.d, "answers.json", answers)])
            self.assertEqual(code, 0, out)
            logs.append([e["fields"]["request"] for e in read_log(self.d / name, action="request")])
        self.assertEqual(logs[0], logs[1])

    def test_the_log_holds_the_wave_with_its_request_answers_reason_verdict_tree_id_and_digest(self):
        answers = {"ADR-T-0001/wave-1": tree_answers("quality-adr.json", consequences="missing")}
        code, out = self.quality("--adr", "ADR-T-0001", answers=answers)
        self.assertEqual(code, 0, out)
        events = read_log(self.d / "logs")
        self.assertEqual([e["action"] for e in events], ["request", "answer", "result", "wave", "verdict"])
        digest = out["data"]["results"][0]["tree"]["sha256"]
        for event in events:
            self.assertEqual((event["fields"]["tree_id"], event["fields"]["tree_sha256"], event["fields"]["run"]),
                             ("quality-adr", digest, "q1"), event["action"])
        wave = events[3]["fields"]
        self.assertEqual((wave["node"], wave["next"], wave["verdict"]), ("wave-1", None, "no"))
        self.assertEqual(wave["answers"], answers["ADR-T-0001/wave-1"])
        self.assertEqual(wave["reason"], out["data"]["results"][0]["waves"][0]["reason"])
        self.assertEqual(wave["request"]["questions"], tree_node("quality-adr.json")["questions"])
        self.assertEqual((events[-1]["fields"]["verdict"], events[-1]["fields"]["path"]), ("no", ["wave-1"]))

    def test_a_wave_without_an_answer_is_exit_2_with_the_path_so_far(self):
        answers = {"ADR-T-0001/wave-1": [{"__error__": "JEV.OVERLOADED"}, {"__error__": "JEV.OVERLOADED"}]}
        code, out = self.quality("--adr", "ADR-T-0001", answers=answers)
        self.assertEqual((code, out["success"], out["error"]["code"]), (2, False, "JEV.OVERLOADED"))
        self.assertEqual((out["data"]["path"], out["data"]["results"]), (["wave-1"], []))
        self.assertEqual(out["data"]["tree"]["id"], "quality-adr")

    def test_a_live_run_needs_a_key_before_anything_is_logged(self):
        with env(), mock.patch.object(jj, "call_jev", never_called):
            code, out = run_cli(["quality", "--req", "REQ-T-0001", "--index", self.index, "--run-dir", str(self.d / "logs")])
        self.assertEqual((code, out["error"]["code"]), (2, "AUTH.CREDENTIALS"))
        self.assertFalse((self.d / "logs").exists())


class LogPath(QualityCase):
    def test_the_default_log_is_sc_judge_jev_logs_judge_jev_log_jsonl(self):
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.d)
        answers = write(self.d, "answers.json", {"*": tree_answers("quality-req.json")})
        with env(), mock.patch.object(jj, "call_jev", never_called):
            code, out = run_cli(["quality", "--req", "REQ-T-0001", "--index", self.index, "--answers-file", answers])
        self.assertEqual((code, out["data"]["log"]["log_root"]), (0, ".sc/judge-jev"), out)
        files = sorted(str(p.relative_to(self.d)) for p in (self.d / ".sc").rglob("*.jsonl"))
        self.assertEqual(files, [str(Path(".sc", "judge-jev", "logs", "judge-jev.log.jsonl"))])


class SeveralRecords(QualityCase):
    def test_one_invocation_judges_every_named_record_under_one_run_name(self):
        answers = {"*": tree_answers("quality-req.json"),
                   "NFR-T-0001.s1/wave-1": tree_answers("quality-nfr.json", check="needs a measure"),
                   "ADR-T-0001/wave-1": tree_answers("quality-adr.json")}
        code, out = self.quality("--req", "REQ-T-0001", "--adr", "ADR-T-0001", "--nfr", "NFR-T-0001", answers=answers)
        self.assertEqual(code, 0, out)
        results = out["data"]["results"]
        self.assertEqual([(r["record"]["id"], r["tree"]["id"], r["verdict"]) for r in results],
                         [("REQ-T-0001", "quality-req", "yes"), ("ADR-T-0001", "quality-adr", "yes"), ("NFR-T-0001", "quality-nfr", "no")])
        self.assertEqual(out["data"]["log"]["run"], "q1")
        events = read_log(self.d / "logs")
        self.assertEqual({e["fields"]["run"] for e in events}, {"q1"})
        self.assertEqual([e["fields"]["record_id"] for e in events if e["action"] == "verdict"], ["REQ-T-0001", "ADR-T-0001", "NFR-T-0001"])

    def test_every_record_is_checked_before_the_first_call(self):
        answers = {"*": tree_answers("quality-req.json")}
        code, out = self.quality("--req", "REQ-T-0001", "--req", "REQ-T-0002", answers=answers)
        self.assertEqual((code, out["error"]["code"], out["data"]["record"]["id"]), (2, "RECORD.DIAGNOSTICS", "REQ-T-0002"))
        self.assertFalse((self.d / "logs").exists())


class TreeOverride(QualityCase):
    TREE = {"id": "variant-7", "start": "w1", "nodes": {
        "w1": {"questions": {"q1": {"type": "choice", "instructions": "Is `item.text` short?",
                                    "criteria": {"yes": "short", "no": "long", "unclear": "cannot tell"}}},
               "next": [{"when": {"q1": "no"}, "goto": "long"}, {"goto": "w2"}]},
        "w2": {"questions": {"q2": {"type": "choice", "instructions": "Is `item.text` plain?",
                                    "criteria": {"yes": "plain", "no": "dense", "unclear": "cannot tell"}}},
               "verdict_rules": [{"any": {"q2": "no"}, "verdict": "no"}, {"verdict": "yes"}]},
        "long": {"verdict": "no"}}}

    def test_a_variation_is_a_file(self):
        path = write(self.d, "variant.json", self.TREE)
        code, out = self.quality("--req", "REQ-T-0001", "--questions", path, "--dry-run")
        self.assertEqual(code, 0, out)
        (data,) = out["data"]["results"]
        self.assertEqual(data["tree"], {"id": "variant-7", "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                                        "source": "override", "path": path})
        self.assertEqual(data["wave"]["request"]["questions"], self.TREE["nodes"]["w1"]["questions"])
        code, out = self.quality("--req", "REQ-T-0001", "--questions", path, answers={"w1": {"q1": answer("no")}})
        (data,) = out["data"]["results"]
        self.assertEqual((code, data["verdict"], data["path"]), (0, "no", ["w1", "long"]), out)

    def test_answers_select_the_next_wave_and_every_wave_reports_its_reason(self):
        path = write(self.d, "variant.json", self.TREE)
        code, out = self.quality("--req", "REQ-T-0001", "--questions", path,
                                 answers={"w1": {"q1": answer("yes")}, "w2": {"q2": answer("no", p=0.7)}})
        self.assertEqual(code, 0, out)
        (data,) = out["data"]["results"]
        self.assertEqual((data["verdict"], data["path"]), ("no", ["w1", "w2"]))
        self.assertEqual([(w["node"], w["next"], w["verdict"], w["reason"]) for w in data["waves"]], [
            ("w1", "w2", None, [{"id": "q1", "text": "Is `item.text` short?", "choice": "yes", "criterion": "short", "confidence": 0.9}]),
            ("w2", None, "no", [{"id": "q2", "text": "Is `item.text` plain?", "choice": "no", "criterion": "dense", "confidence": 0.7}])])

    def test_malformed_trees_are_typed_errors(self):
        w1, w2 = self.TREE["nodes"]["w1"], self.TREE["nodes"]["w2"]

        def nodes(**changed):
            return {**self.TREE, "nodes": {**self.TREE["nodes"], **changed}}

        bad = {
            "start missing": {**self.TREE, "start": "nope"},
            "goto missing": nodes(w1={**w1, "next": [{"goto": "nope"}]}),
            "when names no question": nodes(w1={**w1, "next": [{"when": {"zz": "no"}, "goto": "long"}]}),
            "start is a leaf": {**self.TREE, "start": "long"},
            "next and verdict_rules": nodes(w2={**w2, "next": [{"goto": "long"}]}),
            "neither next nor verdict_rules": nodes(w2={"questions": w2["questions"]}),
            "verdict rule names no question": nodes(w2={**w2, "verdict_rules": [{"any": {"zz": "no"}, "verdict": "no"}]}),
            "verdict rule without a verdict": nodes(w2={**w2, "verdict_rules": [{"any": {"q2": "no"}}]}),
            "all names no question": nodes(w2={**w2, "verdict_rules": [{"all": {"zz": "no"}, "verdict": "no"}]}),
            "empty choice list": nodes(w2={**w2, "verdict_rules": [{"any": {"q2": []}, "verdict": "no"}]}),
            "per is not statement": nodes(w1={**w1, "per": "record", "statements": "requirement_statement.statements"}),
            "per without statements": nodes(w1={**w1, "per": "statement"}),
            "statements without per": nodes(w1={**w1, "statements": "requirement_statement.statements"}),
            "modals not a list": nodes(w1={**w1, "per": "statement", "statements": "a.b", "modals": 3}),
        }
        for name, tree in bad.items():
            code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "bad.json", tree), "--dry-run")
            self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"), name)
        code, out = self.quality("--req", "REQ-T-0001", "--questions", str(self.d / "none.json"), "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MISSING"))

    def test_answers_that_loop_or_match_no_rule_are_typed_errors(self):
        w1, w2 = self.TREE["nodes"]["w1"], self.TREE["nodes"]["w2"]
        loop = {**self.TREE, "nodes": {**self.TREE["nodes"], "w1": {**w1, "next": [{"goto": "w1"}]}}}
        code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "loop.json", loop), answers={"w1": {"q1": answer("yes")}})
        self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"))
        narrow = {**self.TREE, "nodes": {**self.TREE["nodes"], "w1": {**w1, "next": [{"when": {"q1": "no"}, "goto": "long"}]}}}
        code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "narrow.json", narrow), answers={"w1": {"q1": answer("yes")}})
        self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"))
        no_verdict = {**self.TREE, "nodes": {**self.TREE["nodes"], "w2": {**w2, "verdict_rules": [{"any": {"q2": "no"}, "verdict": "no"}]}}}
        code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "nv.json", no_verdict),
                                 answers={"w1": {"q1": answer("yes")}, "w2": {"q2": answer("yes")}})
        self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"))


class QaFindings(QualityCase):
    def test_every_error_after_the_tree_loads_names_the_record_and_the_tree(self):
        tree = {"id": "quality-req", "sha256": hashlib.sha256((QUESTIONS / "quality-req.json").read_bytes()).hexdigest(),
                "source": "shipped", "path": str(jj.QUESTIONS_DIR / "quality-req.json")}

        def refs(rid):
            return {"record": {"id": rid, "kind": "req", "source": {"raptor_index": self.index}}, "tree": tree}

        code, out = self.quality("--req", "REQ-T-0002", "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "RECORD.DIAGNOSTICS"))
        self.assertEqual({k: out["data"][k] for k in ("record", "tree")}, refs("REQ-T-0002"))
        code, out = self.quality("--req", "REQ-T-9999", "--dry-run")
        self.assertEqual((code, out["error"]["code"], out["data"]), (2, "RECORD.NOT_FOUND", refs("REQ-T-9999")))
        self.index = write(self.d, "big.json", {**INDEX, "requirements": [requirement("REQ-T-0001", "x" * 30000)]})
        code, out = self.quality("--req", "REQ-T-0001", "--dry-run")
        self.assertEqual((code, out["error"]["code"], out["data"]), (2, "JEV.CONTEXT_EXCEEDED", refs("REQ-T-0001")))
        self.index = write(self.d, "index.json", INDEX)
        refused = jj.fail("LOG.WRITE", "the sc-observability logger could not start")
        with mock.patch.object(jj, "open_run_log", return_value=refused):
            code, out = self.quality("--req", "REQ-T-0001", answers={"*": tree_answers("quality-req.json")})
        self.assertEqual((code, out["error"]["code"], out["data"]), (2, "LOG.WRITE", refs("REQ-T-0001")))

    def test_a_crlf_checkout_of_a_tree_has_the_lf_digest(self):
        self.assertIn("*.json text eol=lf", (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines())
        lf = (QUESTIONS / "quality-req.json").read_bytes().replace(b"\r\n", b"\n")
        crlf = self.d / "crlf.json"
        crlf.write_bytes(lf.replace(b"\n", b"\r\n"))
        code, out = self.quality("--req", "REQ-T-0001", "--questions", str(crlf), "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["results"][0]["tree"]["sha256"], hashlib.sha256(lf).hexdigest())

    def test_a_rule_that_is_not_an_object_is_quality_tree(self):
        w1, w2 = TreeOverride.TREE["nodes"]["w1"], TreeOverride.TREE["nodes"]["w2"]
        for name, nodes in (("next", {"w1": {**w1, "next": ["oops"]}}), ("verdict_rules", {"w2": {**w2, "verdict_rules": ["oops"]}})):
            tree = {**TreeOverride.TREE, "nodes": {**TreeOverride.TREE["nodes"], **nodes}}
            code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "bad.json", tree), "--dry-run")
            self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"), name)

    def test_modals_as_a_string_is_quality_tree(self):
        tree = json.loads((QUESTIONS / "quality-req.json").read_text(encoding="utf-8"))
        tree["nodes"]["wave-1"]["modals"] = "MustNot"  # a string: "Must" in "MustNot" would match by substring
        code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "bad.json", tree), "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"), out)

    def test_an_override_tree_of_another_kind_is_refused(self):
        code, out = self.quality("--req", "REQ-T-0001", "--questions", str(QUESTIONS / "quality-adr.json"), "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"), out)

    def test_an_empty_record_id_is_validation_input(self):
        # Python 3.12+ argparse accepts `--req ""` (3.11 refuses it), so cmd_quality gets every id empty
        args = jj.build_parser().parse_args(["quality", "--req", "REQ-T-0001", "--index", self.index, "--dry-run"])
        args.req = [""]
        got = jj.cmd_quality(args)
        self.assertIsInstance(got, jj.Err)
        self.assertEqual(got.error.code, "VALIDATION.INPUT")


class PerStatement(QualityCase):
    """A per-statement wave: one request per MUST / MUST NOT statement, a reason per statement, rules over statements."""

    def judge(self, s1=None, s3=None, flag="--req", rid="REQ-T-0001", tree="quality-req.json"):
        answers = {f"{rid}.s1/wave-1": tree_answers(tree, **(s1 or {})), f"{rid}.s3/wave-1": tree_answers(tree, p=0.7, **(s3 or {}))}
        code, out = self.quality(flag, rid, answers=answers)
        self.assertEqual(code, 0, out)
        return out["data"]["results"][0]

    def test_one_request_per_must_and_must_not_statement_each_with_every_question(self):
        self.judge()
        requests = [e["fields"] for e in read_log(self.d / "logs", action="request")]
        self.assertEqual([r["request_id"] for r in requests], ["quality/REQ-T-0001.s1/wave-1/r1", "quality/REQ-T-0001.s3/wave-1/r1"])
        for r in requests:
            self.assertEqual(r["request"]["questions"], tree_node("quality-req.json")["questions"])
        self.assertEqual(len(read_log(self.d / "logs", action="answer")), 2)

    def test_the_reason_lists_each_statement_with_every_questions_choice_criterion_and_confidence(self):
        result = self.judge(s3={"obligations": "2", "joined_by": "and-list"})
        (wave,) = result["waves"]
        questions = tree_node("quality-req.json")["questions"]
        s3 = {"obligations": "2", "joined_by": "and-list"}
        self.assertEqual(wave["reason"], [
            {"statement": JUDGED[0], "answers": [reason_entry(q, questions[q], next(iter(questions[q]["criteria"])), 0.9) for q in questions]},
            {"statement": JUDGED[1], "answers": [reason_entry(q, questions[q], s3.get(q, next(iter(questions[q]["criteria"]))), 0.7)
                                                 for q in questions]}])
        self.assertIn("Fix: split into one statement per item", wave["reason"][1]["answers"][1]["criterion"])
        self.assertEqual((wave["per"], wave["matched_statements"], wave["verdict"], result["verdict"]), ("statement", [3], "no", "no"))
        self.assertEqual(wave["request_ids"], ["quality/REQ-T-0001.s1/wave-1/r1", "quality/REQ-T-0001.s3/wave-1/r1"])

    def test_the_verdict_fires_when_any_one_statement_matches_a_rule(self):
        cases = (({}, {}, "yes", [1, 3]),
                 ({}, {"obligations": "2", "joined_by": "alternatives"}, "no", [3]),
                 ({"obligations": "4+", "joined_by": "obligation+rationale"}, {}, "no", [1]),
                 # `all`: a fix-needing join counts only with two or more obligations, and a condition is not a second one
                 ({"obligations": "1", "joined_by": "and-list"}, {}, "yes", [1, 3]),
                 ({"obligations": "2", "joined_by": "condition+obligation"}, {}, "yes", [1, 3]),
                 ({"term": "vague qualifier"}, {"term": "project term defined in a linked record"}, "no", [1]),
                 ({}, {"term": "undefined acronym"}, "no", [3]),
                 ({"check": "none"}, {"check": "needs a measure"}, "no", [1, 3]),
                 ({"check": "CLI run"}, {"check": "inspection or grep"}, "yes", [1, 3]))
        for s1, s3, verdict, matched in cases:
            result = self.judge(s1, s3)
            self.assertEqual((result["verdict"], result["waves"][0]["matched_statements"]), (verdict, matched), (s1, s3))

    def test_nfr_uses_the_same_per_statement_questions(self):
        answers = {"NFR-T-0001.s1/wave-1": tree_answers("quality-nfr.json", check="needs a measure")}
        code, out = self.quality("--nfr", "NFR-T-0001", answers=answers)
        self.assertEqual(code, 0, out)
        (wave,) = out["data"]["results"][0]["waves"]
        self.assertEqual((wave["verdict"], wave["matched_statements"], wave["reason"][0]["statement"]["text"]),
                         ("no", [1], "A run MUST finish in 5 s."))

    def test_the_log_holds_every_statements_request_and_answers(self):
        answers = {"REQ-T-0001.s1/wave-1": tree_answers("quality-req.json"),
                   "REQ-T-0001.s3/wave-1": tree_answers("quality-req.json", check="none")}
        code, out = self.quality("--req", "REQ-T-0001", answers=answers)
        self.assertEqual(code, 0, out)
        events = read_log(self.d / "logs")
        self.assertEqual([e["action"] for e in events], ["request", "answer", "result"] * 2 + ["statement"] * 2 + ["wave", "verdict"])
        result_wave = out["data"]["results"][0]["waves"][0]
        statements = [e["fields"] for e in events[6:8]]
        self.assertEqual([s["statement"] for s in statements], JUDGED)
        self.assertEqual([s["answers"] for s in statements], [answers["REQ-T-0001.s1/wave-1"], answers["REQ-T-0001.s3/wave-1"]])
        self.assertEqual([s["request_id"] for s in statements], result_wave["request_ids"])
        self.assertEqual([e["fields"]["request_id"] for e in events if e["action"] == "request"], result_wave["request_ids"])
        self.assertEqual([{"statement": s["statement"], "answers": s["reason"]} for s in statements], result_wave["reason"])
        wave = events[8]["fields"]
        self.assertEqual((wave["request_ids"], wave["matched_statements"], wave["verdict"]), (result_wave["request_ids"], [3], "no"))

    def test_a_statement_without_an_answer_names_the_statement(self):
        answers = {"REQ-T-0001.s1/wave-1": tree_answers("quality-req.json"),
                   "REQ-T-0001.s3/wave-1": [{"__error__": "JEV.OVERLOADED"}, {"__error__": "JEV.OVERLOADED"}]}
        code, out = self.quality("--req", "REQ-T-0001", answers=answers)
        self.assertEqual((code, out["error"]["code"]), (2, "JEV.OVERLOADED"))
        self.assertIn("statement 3", out["error"]["message"])
        self.assertEqual((out["data"]["statement"], out["data"]["path"]), (JUDGED[1], ["wave-1"]))

    def test_a_record_without_judged_statements_is_a_typed_error(self):
        for record in (requirement("REQ-T-0001", "Should: It SHOULD be quick."),
                       {"id": "REQ-T-0001", "title": "No statements field"}):
            self.index = write(self.d, "idx.json", {**INDEX, "requirements": [record]})
            code, out = self.quality("--req", "REQ-T-0001", "--dry-run")
            self.assertEqual((code, out["error"]["code"], out["data"]["record"]["id"]), (2, "RECORD.STATEMENTS", "REQ-T-0001"), out)


class ShippedTrees(unittest.TestCase):
    def test_one_draft_wave_1_only_tree_per_kind_that_loads(self):
        for kind in ("req", "adr", "nfr"):
            tree = jj.load_quality_tree(kind)
            self.assertIsInstance(tree, jj.Ok, kind)
            raw = json.loads((QUESTIONS / f"quality-{kind}.json").read_text(encoding="utf-8"))
            self.assertEqual((raw["id"], raw["approved"], raw["note"]), (f"quality-{kind}", False, "draft, pending Rand approval"))
            self.assertEqual((raw["start"], list(raw["nodes"])), ("wave-1", ["wave-1"]))

    def test_req_and_nfr_ask_four_questions_per_statement_and_adr_three_per_record(self):
        options = {"obligations": ["1", "2", "3", "4+"],
                   "joined_by": ["none", "and-list", "condition+obligation", "alternatives", "obligation+rationale"],
                   "term": ["none", "project term defined in a linked record", "project term defined nowhere", "vague qualifier",
                            "undefined acronym"],
                   "check": ["unit test", "CLI run", "inspection or grep", "needs a measure", "none"]}
        for kind in ("req", "nfr"):
            node = tree_node(f"quality-{kind}.json")
            self.assertEqual((node["per"], node["statements"], node["modals"]),
                             ("statement", "requirement_statement.statements", ["Must", "MustNot"]))
            self.assertEqual({qid: list(q["criteria"]) for qid, q in node["questions"].items()}, options)
        node = tree_node("quality-adr.json")
        self.assertNotIn("per", node)
        self.assertEqual({qid: list(q["criteria"]) for qid, q in node["questions"].items()},
                         {"context": ["problem and forces", "background only", "missing"],
                          "alternatives": ["named with reasons rejected", "named only", "none"],
                          "consequences": ["positive and negative", "positive only", "missing"]})
        for kind in ("req", "nfr", "adr"):  # every option a `no` rule names carries its fix hint in its criterion
            node = tree_node(f"quality-{kind}.json")
            for rule in node["verdict_rules"]:
                if rule["verdict"] != "no":
                    continue
                for qid, choices in {**rule.get("all", {}), **rule.get("any", {})}.items():
                    for choice in choices:
                        if qid != "obligations":  # counts need no fix of their own; the join says what to do
                            self.assertIn("Fix:", node["questions"][qid]["criteria"][choice], (kind, qid, choice))

    def test_an_anchorless_line_matches_the_batch_schemas(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed")
        record = INDEX["requirements"][0]
        node = tree_node("quality-req.json")
        line = jj.wave_line(record, "wave-1", node, JUDGED[1])  # a per-statement line is a plain anchorless batch line
        settings = jj.quality_settings(False)
        job = jj.batch_jobs(line, 1, settings, {}).value[0]
        result = jj.run_batch_job(job, settings, "", {"*": tree_answers("quality-req.json")}, jj._AbortFlag())
        self.assertEqual((result["request_id"], result["anchor_id"], result["verdict"]), ("quality/REQ-T-0001.s3/wave-1/r1", None, None))
        schemas = SKILL / "assets" / "schemas"
        for name, value in (("jev-batch-request", line), ("jev-batch-result", result)):
            jsonschema.Draft202012Validator(json.loads((schemas / f"{name}.schema.json").read_text(encoding="utf-8"))).validate(value)


if __name__ == "__main__":
    unittest.main()
