"""`jev_judge.py quality`: one record from a Raptor import index, its kind's decision tree, one batch request per wave.

Answers come from answers files (keyed '<record>/<node>'); Jev is never called (call_jev is replaced with a stub that
fails the test). The run log is read back through sc-observability's query API.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jev_support import ROOT, SKILL, read_log
import jev_judge as jj  # noqa: E402

from test_jev_judge import answer, env, run_cli, write  # noqa: E402

QUESTIONS = SKILL / "assets" / "questions"


def statement(text):
    return {"modal": "Must", "text": text}


def requirement(rid, *statements, criteria=("It works.",)):
    return {"id": rid, "title": f"Title of {rid}", "status": "Draft",
            "requirement_statement": {"text": "", "statements": [statement(s) for s in statements]},
            "rationale": "Because.", "success_criteria": {"text": "", "acceptance_criteria": [{"text": c, "checked": False} for c in criteria]}}


INDEX = {
    "metadata": {"repository": "urn:raptor:repo:test", "files": 1, "records": 4},
    "requirements": [requirement("REQ-T-0001", "The CLI MUST exit 2 on a missing file."),
                     requirement("REQ-T-0002", "Broken record."),
                     {**requirement("NFR-T-0001", "A run MUST finish in 5 s."), "title": "Fast"}],
    "decisions": [{"id": "ADR-T-0001", "title": "Use SQLite", "decision": {"text": "Store records in SQLite."}}],
    "diagnostics": {"issues": [{"file": "docs/r.md", "line": 3, "column": 1, "rule": "MISSING_SECTION", "id": "REQ-T-0002",
                                "message": "Found None; expected rationale.", "remedy": "Add the section."}],
                    "summary": {"records": 4}},
}


def tree_answers(node_file, node, **choices):
    """Answers for every question of ``node`` in a shipped tree: ``yes`` unless named in ``choices``."""
    questions = json.loads((QUESTIONS / node_file).read_text(encoding="utf-8"))["nodes"][node]["questions"]
    return {qid: answer(choices.get(qid, "yes")) for qid in questions}


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
        code, out = self.quality("--req", "REQ-T-0001", "--dry-run")
        self.assertEqual((code, out["success"], out["error"]), (0, True, None), out)
        data = out["data"]
        shipped = QUESTIONS / "quality-req.json"
        self.assertEqual(data["tree"], {"id": "quality-req", "sha256": hashlib.sha256(shipped.read_bytes()).hexdigest(),
                                        "source": "shipped", "path": str(jj.QUESTIONS_DIR / "quality-req.json")})
        self.assertEqual(data["record"], {"id": "REQ-T-0001", "kind": "req", "source": {"raptor_index": self.index}})
        wave = data["wave"]
        tree = json.loads(shipped.read_text(encoding="utf-8"))
        self.assertEqual(wave["node"], "wave-1")
        # REQ-JEV-0209: the request carries only the record and the REQ tree's wave-1 questions
        self.assertEqual(set(wave["request"]), {"model", "state", "questions"})
        self.assertEqual(wave["request"]["questions"], tree["nodes"]["wave-1"]["questions"])
        self.assertEqual(wave["request"]["state"], {"item": {"id": "REQ-T-0001", "title": "Title of REQ-T-0001",
                                                             "text": json.dumps(INDEX["requirements"][0], indent=2, ensure_ascii=False)}})
        self.assertEqual((wave["request_bytes"], wave["max_request_bytes"]), (len(jj.encode_body(wave["request"])), 24000))
        self.assertFalse((self.d / "logs").exists())

    def test_each_kind_uses_its_own_tree_and_table(self):
        for flag, rid, tree_id in (("--nfr", "NFR-T-0001", "quality-nfr"), ("--adr", "ADR-T-0001", "quality-adr")):
            code, out = self.quality(flag, rid, "--dry-run")
            self.assertEqual((code, out["data"]["tree"]["id"], out["data"]["record"]["id"]), (0, tree_id, rid), out)
        code, out = self.quality("--adr", "REQ-T-0001", "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "RECORD.NOT_FOUND"))

    def test_oversize_request_is_a_typed_error(self):
        big = {**INDEX, "requirements": [requirement("REQ-T-0001", "x" * 30000)]}
        self.index = write(self.d, "big.json", big)
        code, out = self.quality("--req", "REQ-T-0001", "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "JEV.CONTEXT_EXCEEDED"))

    def test_exactly_one_record_flag(self):
        code, out = run_cli(["quality", "--req", "A", "--adr", "B", "--index", self.index, "--dry-run"])
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))
        code, out = run_cli(["quality", "--index", self.index, "--dry-run"])
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))


class RecordsWithDiagnostics(QualityCase):
    def test_a_record_raptor_rejected_is_not_sent_to_jev(self):
        answers = {"*": tree_answers("quality-req.json", "wave-1")}
        code, out = self.quality("--req", "REQ-T-0002", answers=answers)
        self.assertEqual((code, out["error"]["code"]), (2, "RECORD.DIAGNOSTICS"))
        self.assertEqual(out["data"]["diagnostics"], INDEX["diagnostics"]["issues"])
        self.assertFalse((self.d / "logs").exists())
        code, out = self.quality("--req", "REQ-T-0002", "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "RECORD.DIAGNOSTICS"))


class Waves(QualityCase):
    PASS = {"REQ-T-0001/wave-1": tree_answers("quality-req.json", "wave-1"),
            "REQ-T-0001/wave-2": tree_answers("quality-req.json", "wave-2")}

    def test_fixed_wave_1_answers_select_the_same_wave_2_every_run(self):
        runs = []
        for name in ("a", "b"):
            with env(), mock.patch.object(jj, "call_jev", never_called):
                code, out = run_cli(["quality", "--req", "REQ-T-0001", "--index", self.index, "--run-dir", str(self.d / name),
                                     "--answers-file", write(self.d, "answers.json", self.PASS)])
            self.assertEqual(code, 0, out)
            runs.append((out["data"], read_log(self.d / name, action="request")))
        (first, first_log), (second, second_log) = runs
        self.assertEqual((first["verdict"], first["path"]), ("yes", ["wave-1", "wave-2", "pass"]))
        self.assertEqual(first["path"], second["path"])
        self.assertEqual([e["fields"]["request"] for e in first_log], [e["fields"]["request"] for e in second_log])
        wave_2 = json.loads((QUESTIONS / "quality-req.json").read_text(encoding="utf-8"))["nodes"]["wave-2"]["questions"]
        self.assertEqual(first_log[1]["fields"]["request"]["questions"], wave_2)

    def test_no_observable_outcome_reports_no_with_the_testable_node(self):
        answers = {"REQ-T-0001/wave-1": tree_answers("quality-req.json", "wave-1", testable="no")}
        code, out = self.quality("--req", "REQ-T-0001", answers=answers)
        self.assertEqual((code, out["success"]), (0, True), out)
        self.assertEqual((out["data"]["verdict"], out["data"]["path"]), ("no", ["wave-1", "testable"]))
        self.assertEqual(out["data"]["waves"][0]["choices"]["testable"], "no")

    def test_the_log_holds_every_wave_with_its_request_answers_branch_tree_id_and_digest(self):
        code, out = self.quality("--req", "REQ-T-0001", answers=self.PASS)
        self.assertEqual(code, 0, out)
        events = read_log(self.d / "logs")
        self.assertEqual([e["action"] for e in events],
                         ["request", "answer", "result", "wave"] * 2 + ["verdict"])
        digest = out["data"]["tree"]["sha256"]
        for event in events:
            self.assertEqual((event["fields"]["tree_id"], event["fields"]["tree_sha256"], event["fields"]["run"]),
                             ("quality-req", digest, "q1"), event["action"])
        waves = [e["fields"] for e in events if e["action"] == "wave"]
        self.assertEqual([(w["node"], w["next"]) for w in waves], [("wave-1", "wave-2"), ("wave-2", "pass")])
        self.assertEqual(waves[0]["answers"], self.PASS["REQ-T-0001/wave-1"])
        self.assertEqual(waves[0]["request"]["questions"], json.loads((QUESTIONS / "quality-req.json").read_text(encoding="utf-8"))["nodes"]["wave-1"]["questions"])
        self.assertEqual(events[-1]["fields"]["path"], ["wave-1", "wave-2", "pass"])
        results = [e["fields"] for e in events if e["action"] == "result"]
        self.assertEqual([(r["anchor_id"], r["verdict"]) for r in results], [(None, None), (None, None)])

    def test_a_wave_without_an_answer_is_exit_2_with_the_path_so_far(self):
        answers = {**self.PASS, "REQ-T-0001/wave-2": [{"__error__": "JEV.OVERLOADED"}, {"__error__": "JEV.OVERLOADED"}]}
        code, out = self.quality("--req", "REQ-T-0001", answers=answers)
        self.assertEqual((code, out["success"], out["error"]["code"]), (2, False, "JEV.OVERLOADED"))
        self.assertEqual(out["data"]["path"], ["wave-1", "wave-2"])
        self.assertEqual(out["data"]["tree"]["id"], "quality-req")

    def test_a_live_run_needs_a_key_before_anything_is_logged(self):
        with env(), mock.patch.object(jj, "call_jev", never_called):
            code, out = run_cli(["quality", "--req", "REQ-T-0001", "--index", self.index, "--run-dir", str(self.d / "logs")])
        self.assertEqual((code, out["error"]["code"]), (2, "AUTH.CREDENTIALS"))
        self.assertFalse((self.d / "logs").exists())


class TreeOverride(QualityCase):
    TREE = {"id": "variant-7", "start": "w1", "nodes": {
        "w1": {"questions": {"q1": {"type": "choice", "instructions": "Is `item.text` short?",
                                    "criteria": {"yes": "short", "no": "long", "unclear": "cannot tell"}}},
               "next": [{"when": {"q1": "no"}, "goto": "long"}, {"goto": "fine"}]},
        "long": {"verdict": "no"}, "fine": {"verdict": "yes"}}}

    def test_a_variation_is_a_file(self):
        path = write(self.d, "variant.json", self.TREE)
        code, out = self.quality("--req", "REQ-T-0001", "--questions", path, "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["tree"], {"id": "variant-7", "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                                               "source": "override", "path": path})
        self.assertEqual(out["data"]["wave"]["request"]["questions"], self.TREE["nodes"]["w1"]["questions"])
        code, out = self.quality("--req", "REQ-T-0001", "--questions", path, answers={"w1": {"q1": answer("no")}})
        self.assertEqual((code, out["data"]["verdict"], out["data"]["path"]), (0, "no", ["w1", "long"]), out)

    def test_malformed_trees_are_typed_errors(self):
        bad = {
            "start missing": {**self.TREE, "start": "nope"},
            "goto missing": {**self.TREE, "nodes": {**self.TREE["nodes"], "w1": {**self.TREE["nodes"]["w1"], "next": [{"goto": "nope"}]}}},
            "when names no question": {**self.TREE, "nodes": {**self.TREE["nodes"], "w1": {**self.TREE["nodes"]["w1"], "next": [{"when": {"zz": "no"}, "goto": "fine"}]}}},
            "start is a leaf": {**self.TREE, "start": "fine"},
        }
        for name, tree in bad.items():
            code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "bad.json", tree), "--dry-run")
            self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"), name)
        code, out = self.quality("--req", "REQ-T-0001", "--questions", str(self.d / "none.json"), "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MISSING"))

    def test_answers_that_loop_or_match_no_branch_are_typed_errors(self):
        loop = {**self.TREE, "nodes": {**self.TREE["nodes"], "w1": {**self.TREE["nodes"]["w1"], "next": [{"goto": "w1"}]}}}
        code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "loop.json", loop), answers={"w1": {"q1": answer("yes")}})
        self.assertEqual((code, out["error"]["code"]), (2, "QUALITY.TREE"))
        narrow = {**self.TREE, "nodes": {**self.TREE["nodes"], "w1": {**self.TREE["nodes"]["w1"], "next": [{"when": {"q1": "no"}, "goto": "long"}]}}}
        code, out = self.quality("--req", "REQ-T-0001", "--questions", write(self.d, "narrow.json", narrow), answers={"w1": {"q1": answer("yes")}})
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
            code, out = self.quality("--req", "REQ-T-0001", answers={"*": tree_answers("quality-req.json", "wave-1")})
        self.assertEqual((code, out["error"]["code"], out["data"]), (2, "LOG.WRITE", refs("REQ-T-0001")))

    def test_a_crlf_checkout_of_a_tree_has_the_lf_digest(self):
        self.assertIn("*.json text eol=lf", (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines())
        lf = (QUESTIONS / "quality-req.json").read_bytes().replace(b"\r\n", b"\n")
        crlf = self.d / "crlf.json"
        crlf.write_bytes(lf.replace(b"\n", b"\r\n"))
        code, out = self.quality("--req", "REQ-T-0001", "--questions", str(crlf), "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["tree"]["sha256"], hashlib.sha256(lf).hexdigest())

    def test_an_empty_record_id_is_validation_input(self):
        # Python 3.12+ argparse accepts `--req ""` (3.11 refuses it), so cmd_quality gets every id empty
        args = jj.build_parser().parse_args(["quality", "--req", "REQ-T-0001", "--index", self.index, "--dry-run"])
        args.req = ""
        got = jj.cmd_quality(args)
        self.assertIsInstance(got, jj.Err)
        self.assertEqual(got.error.code, "VALIDATION.INPUT")


class ShippedTrees(unittest.TestCase):
    def test_one_draft_tree_per_kind_that_loads(self):
        for kind in ("req", "adr", "nfr"):
            tree = jj.load_quality_tree(kind)
            self.assertIsInstance(tree, jj.Ok, kind)
            raw = json.loads((QUESTIONS / f"quality-{kind}.json").read_text(encoding="utf-8"))
            self.assertEqual((raw["id"], raw["approved"], raw["note"]), (f"quality-{kind}", False, "draft, pending Rand approval"))
            for node in raw["nodes"].values():
                for q in node.get("questions", {}).values():
                    self.assertEqual(set(q["criteria"]), {"yes", "no", "unclear"})

    def test_an_anchorless_line_matches_the_batch_schemas(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed")
        record = INDEX["requirements"][0]
        node = json.loads((QUESTIONS / "quality-req.json").read_text(encoding="utf-8"))["nodes"]["wave-1"]
        line = jj.wave_line(record, "wave-1", node)
        settings = jj.quality_settings(False)
        job = jj.batch_jobs(line, 1, settings, {}).value[0]
        result = jj.run_batch_job(job, settings, "", {"*": tree_answers("quality-req.json", "wave-1")}, jj._AbortFlag())
        self.assertEqual((result["request_id"], result["anchor_id"], result["verdict"]), ("quality/REQ-T-0001/wave-1/r1", None, None))
        schemas = SKILL / "assets" / "schemas"
        for name, value in (("jev-batch-request", line), ("jev-batch-result", result)):
            jsonschema.Draft202012Validator(json.loads((schemas / f"{name}.schema.json").read_text(encoding="utf-8"))).validate(value)


if __name__ == "__main__":
    unittest.main()
