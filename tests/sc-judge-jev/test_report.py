"""`jev_report.py`: the quality report built from real `quality` runs (answers files, Jev never called) and the check
report built from the check results contract. The page, its panels and the sidecar are read back from disk."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path
from unittest import mock

from jev_support import SKILL  # noqa: F401  (renders the skill and puts its scripts on sys.path)
import jev_judge as jj  # noqa: E402
import jev_report  # noqa: E402

from test_jev_judge import env, run_cli, write  # noqa: E402
from test_quality import INDEX, never_called, tree_answers  # noqa: E402

RECORD = "REQ-T-0001"
FAILING = {f"{RECORD}.s1/wave-1": tree_answers("quality-req.json", check="none"), "*": tree_answers("quality-req.json")}
PASSING = {"*": tree_answers("quality-req.json")}
EDITED = "The CLI MUST exit 2 when the input file is missing."


def report(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = jev_report.main(argv)
    return code, json.loads(buf.getvalue())


def edited_index():
    index = copy.deepcopy(INDEX)
    index["requirements"][0]["requirement_statement"]["statements"][0]["text"] = EDITED
    return index


class ReportCase(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        self.run_dir = self.d / "runs"

    def judge(self, run_name, index, answers):
        with env(), mock.patch.object(jj, "call_jev", never_called):
            code, out = run_cli(["quality", "--req", RECORD, "--index", write(self.d, f"{run_name}.index.json", index),
                                 "--run-dir", str(self.run_dir), "--run-name", run_name,
                                 "--answers-file", write(self.d, f"{run_name}.answers.json", answers)])
        self.assertEqual(code, 0, out)
        return out["data"]["results"][0]["verdict"]

    def fix_loop(self):
        """Two repeats of a failing base step, then one run of the edited record."""
        verdicts = [self.judge("t-base-r1", INDEX, FAILING), self.judge("t-base-r2", INDEX, FAILING),
                    self.judge("t-final-r1", edited_index(), PASSING)]
        self.assertEqual(verdicts, ["no", "no", "yes"])

    def quality_report(self, *extra):
        return report(["quality", "--run-dir", str(self.run_dir), "--out", str(self.d / "out"), *extra])


class QualityReport(ReportCase):
    def test_steps_answers_and_text_diff_come_from_the_log(self):
        self.fix_loop()
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        data = out["data"]
        self.assertEqual((data["status"], data["records"], data["passing_first"], data["passing_last"]), ("PASS", 1, 0, 1))
        sidecar = json.loads(Path(data["sidecar"]).read_text(encoding="utf-8"))
        self.assertEqual(sidecar["schema"], "judge-jev/report/1")
        (unit,) = sidecar["records"]
        self.assertEqual([(s["step"], s["runs"], s["tally"]) for s in unit["steps"]],
                         [("t-base", 2, "no 2/2"), ("t-final", 1, "yes 1/1")])
        self.assertEqual([a["item"] for a in unit["first_failing"]], ["wave-1 · s1 · check"])
        self.assertIn("Fix:", unit["first_failing"][0]["criterion"])
        self.assertEqual(unit["last_failing"], [])
        (change,) = unit["changes"]
        self.assertEqual(change["field"], "requirement_statement.statements")
        self.assertIn(EDITED, change["after"])
        self.assertEqual([t["run"] for t in unit["trail"]], ["t-base-r1", "t-base-r2", "t-final-r1"])

    def test_the_panel_is_well_formed_xhtml_with_the_diff_and_one_dot_per_answer(self):
        self.fix_loop()
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        (panel,) = out["data"]["panels"]
        dom = xml.dom.minidom.parse(panel)
        self.assertEqual(dom.documentElement.getAttribute("id"), f"record-{RECORD}")
        text = Path(panel).read_text(encoding="utf-8")
        for fragment in ("<del>on</del><ins>when</ins>", "<del>file.</del><ins>file is missing.</ins>",
                         '<div class="eq">Should: The CLI SHOULD be quick.</div>'):
            self.assertTrue(fragment in text, fragment)
        chart = json.loads(dom.getElementsByTagName("div")[[d.getAttribute("class") for d in dom.getElementsByTagName("div")]
                                                            .index("conf-chart")].getAttribute("data-chart"))
        questions = len(json.loads((SKILL / "assets" / "questions" / "quality-req.json").read_text(encoding="utf-8"))
                        ["nodes"]["wave-1"]["questions"])
        self.assertEqual(len(chart["rows"]), 2 * questions)  # REQ-T-0001's MUST and MUST NOT statements
        self.assertTrue(all(len(r["dots"]) == 3 for r in chart["rows"]))  # three runs
        self.assertEqual([s["style"] for s in chart["series"]], ["first", "last"])
        page = Path(out["data"]["html"]).read_text(encoding="utf-8")
        self.assertIn(text.strip()[:200], page)  # the page embeds the panel as rendered

    def test_run_and_record_filters_narrow_the_report(self):
        self.fix_loop()
        code, out = self.quality_report("--run", "t-base-r1")
        self.assertEqual(code, 0, out)
        unit = json.loads(Path(out["data"]["sidecar"]).read_text(encoding="utf-8"))["records"][0]
        self.assertEqual([t["run"] for t in unit["trail"]], ["t-base-r1"])
        self.assertEqual(out["data"]["status"], "FAIL")
        code, out = self.quality_report("--record", "REQ-T-9999")
        self.assertEqual((code, out["error"]["code"]), (2, "REPORT.NO_RUNS"))

    def test_a_run_name_used_twice_is_two_runs_each_with_its_own_answers(self):
        self.judge("t-base-r1", INDEX, FAILING)
        self.judge("t-base-r1", edited_index(), PASSING)
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        unit = json.loads(Path(out["data"]["sidecar"]).read_text(encoding="utf-8"))["records"][0]
        self.assertEqual([(t["run"], t["verdict"], t["failing"]) for t in unit["trail"]],
                         [("t-base-r1", "no", 1), ("t-base-r1 (2)", "yes", 0)])
        self.assertEqual(len(unit["first_failing"]), 1)
        self.assertIn(EDITED, unit["changes"][0]["after"])

    def test_record_text_is_escaped(self):
        index = copy.deepcopy(INDEX)
        index["requirements"][0]["title"] = "<script>alert(1)</script>"
        self.judge("t-r1", index, PASSING)
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        page = Path(out["data"]["html"]).read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)", page)
        self.assertIn("&lt;script&gt;alert(1)", page)


class DriftReview(ReportCase):
    def test_kept_and_discarded_changes_are_in_the_panel(self):
        self.fix_loop()
        review = {"reviewed_at": "2026-11-10", "records": {
            RECORD: {"kept": [{"change": "missing file as a condition", "why": "testable", "authority": "docs/cli.md:12"}],
                     "discarded": [{"change": "dropped exit code", "why": "drift"}]},
            "REQ-T-0404": {"kept": []}}}
        code, out = self.quality_report("--review", write(self.d, "review.json", review))
        self.assertEqual(code, 0, out)
        text = Path(out["data"]["panels"][0]).read_text(encoding="utf-8")
        for expected in ("missing file as a condition", "docs/cli.md:12", "dropped exit code"):
            self.assertIn(expected, text)
        self.assertEqual(out["data"]["warnings"], ["review names REQ-T-0404, which no run in this report judged"])

    def test_a_review_off_contract_is_validation_input(self):
        self.fix_loop()
        bad = {"reviewed_at": "2026-11-10", "records": {RECORD: {"kept": [{"change": "x"}]}}}
        code, out = self.quality_report("--review", write(self.d, "review.json", bad))
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))
        self.assertIn("records.REQ-T-0001.kept.0.why", out["error"]["message"])


def answers(*fix):
    return [{"id": q, "text": f"Does it meet {q}?", "choice": "no" if q in fix else "yes", "confidence": 0.8,
             "criterion": f"Misses {q}. Fix: add it." if q in fix else "Meets it."} for q in ("covered", "contradicts")]


CHECK = {"run": "c1", "pairs": [
    {"record_id": "REQ-T-0001", "record_kind": "req", "record_title": "Exit codes", "location": "skills/x/SKILL.md#Exit",
     "mode": "skill", "requests": [{"request_id": "c1/a", "verdict": "yes", "text": "Exit 2 on error.", "reason": answers()}]},
    {"record_id": "REQ-T-0001", "record_kind": "req", "location": "templates/dev.md.j2", "mode": "task",
     "requests": [{"variant": "raw", "request_id": "c1/b", "verdict": "yes", "reason": answers()},
                  {"variant": "rendered", "request_id": "c1/c", "verdict": "no", "reason": answers("covered")}]},
    {"record_id": "ADR-T-0001", "record_kind": "adr", "location": "src/store.rs::open", "mode": "code",
     "requests": [{"request_id": "c1/d", "verdict": "yes", "text": "fn open() {}", "reason": answers()}]}]}


class CheckReport(ReportCase):
    def check(self, results):
        return report(["check", "--results", write(self.d, "check.json", results), "--out", str(self.d / "out")])

    def test_pairs_aggregate_per_record_and_per_location(self):
        code, out = self.check(CHECK)
        self.assertEqual(code, 0, out)
        self.assertEqual((out["data"]["status"], out["data"]["pairs"], out["data"]["met"], out["data"]["units"]), ("FAIL", 3, 2, 3))
        sidecar = json.loads(Path(out["data"]["sidecar"]).read_text(encoding="utf-8"))
        status = {u["id"]: (u["status"], u["target_class"]) for u in sidecar["locations"]}
        self.assertEqual(status, {"skills/x/SKILL.md#Exit": ("pass", "agent text"),
                                  "templates/dev.md.j2": ("fail", "agent text"), "src/store.rs::open": ("pass", "code")})
        for panel in out["data"]["panels"]:
            xml.dom.minidom.parse(panel)
        task = Path(out["data"]["panels"][-1]).read_text(encoding="utf-8")
        self.assertIn("the raw template, then the rendered assignment", task)
        self.assertIn("Misses covered. Fix: add it.", task)

    def test_task_mode_needs_raw_then_rendered(self):
        bad = copy.deepcopy(CHECK)
        bad["pairs"][1]["requests"].pop()
        code, out = self.check(bad)
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))
        self.assertIn("raw then rendered", out["error"]["message"])

    def test_missing_sc_compose_is_a_typed_error(self):
        with mock.patch.object(jev_report.shutil, "which", return_value=None):
            code, out = self.check(CHECK)
        self.assertEqual((code, out["error"]["code"]), (2, "DEPENDENCY.SC_COMPOSE"))


if __name__ == "__main__":
    unittest.main()
