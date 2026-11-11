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


ORIGINAL_MD = """# Requirements

## REQ-T-0001: Exit codes

The CLI MUST exit 2 on a missing input file.

- The CLI SHOULD be quick.

## REQ-T-0002: Other

Untouched by this run.
"""
FINAL_MD = ORIGINAL_MD.replace("on a missing input file.", "when the input file is missing.").replace(
    "Untouched by this run.", "Edited by another run.")


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
        self.w = self.d / "fix" / RECORD
        self.w.mkdir(parents=True)
        (self.w / "env").write_text(f"ID={RECORD}\nKIND=req\nF=docs/req.md\nW=.sc/judge-jev/fix/{RECORD}\n", encoding="utf-8")
        (self.w / "original.md").write_text(ORIGINAL_MD, encoding="utf-8")
        (self.w / "current.md").write_text(FINAL_MD, encoding="utf-8")

    def judge(self, variant, n, index, answers):
        """One real ``quality`` run, its envelope saved as the fix loop saves it: ``<variant>-r<n>.json``."""
        with env(), mock.patch.object(jj, "call_jev", never_called):
            code, out = run_cli(["quality", "--req", RECORD, "--index", write(self.d, f"{variant}.index.json", index),
                                 "--run-dir", str(self.d / "runs"), "--run-name", f"{RECORD}-{variant}-r{n}",
                                 "--answers-file", write(self.d, f"{variant}-{n}.answers.json", answers)])
        self.assertEqual(code, 0, out)
        (self.w / f"{variant}-r{n}.json").write_text(json.dumps(out), encoding="utf-8")
        return out["data"]["results"][0]["verdict"]

    def fix_loop(self):
        """Two base runs fail s1 on its check; candidate c1 and final pass."""
        verdicts = [self.judge("base", 1, INDEX, FAILING), self.judge("base", 2, INDEX, FAILING),
                    self.judge("c1", 1, edited_index(), PASSING), self.judge("final", 1, edited_index(), PASSING)]
        self.assertEqual(verdicts, ["no", "no", "yes", "yes"])

    def quality_report(self, *extra):
        return report(["quality", "--fix-dir", str(self.w), "--out", str(self.d / "out"), *extra])

    def sidecar(self, out):
        return json.loads(Path(out["data"]["sidecar"]).read_text(encoding="utf-8"))["record"]


class QualityReport(ReportCase):
    def test_the_report_names_what_improved_why_and_which_step_cleared_it(self):
        self.fix_loop()
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        data = out["data"]
        self.assertEqual((data["status"], data["before"], data["after"], data["fixed"], data["regressed"]),
                         ("PASS", "no 2/2", "yes 1/1", 1, 0))
        rec = self.sidecar(out)
        self.assertEqual([(s["step"], s["runs"], s["tally"], s["fired"], s["clears"]) for s in rec["steps"]],
                         [("base", 2, "no 2/2", "s1", "-"), ("c1", 1, "yes 1/1", "-", "s1"),
                          ("final", 1, "yes 1/1", "-", "s1")])
        (o,) = rec["outcomes"]
        self.assertEqual((o["key"], o["before"], o["after"], o["state"], o["fixed_by"]),
                         ("wave-1 · s1", "2/2", "0/1", "fixed", "c1"))
        (why,) = o["why"]
        self.assertEqual((why["question"], why["before"]["choice"], why["before"]["count"], why["before"]["of"]),
                         ("check", "none", 2, 2))
        self.assertIn("Fix:", why["before"]["criterion"])
        self.assertFalse(why["after"]["failing"])

    def test_the_panel_is_xhtml_with_the_record_section_diff_and_a_tab_per_question(self):
        self.fix_loop()
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        (panel,) = out["data"]["panels"]
        dom = xml.dom.minidom.parse(panel)
        self.assertEqual(dom.documentElement.getAttribute("id"), f"record-{RECORD}")
        text = Path(panel).read_text(encoding="utf-8")
        for fragment in ("<del>on</del><ins>when</ins>", "<del>file.</del><ins>file is missing.</ins>",
                         '<div class="md md-li eq lv0">The CLI SHOULD be quick.</div>'):
            self.assertIn(fragment, text)
        self.assertNotIn("Edited by another run", text)  # only the record's own section is diffed
        chart = json.loads([d for d in dom.getElementsByTagName("div") if d.getAttribute("class") == "conf-chart"][0]
                           .getAttribute("data-chart"))
        questions = json.loads((SKILL / "assets" / "questions" / "quality-req.json").read_text(encoding="utf-8"))[
            "nodes"]["wave-1"]["questions"]
        self.assertEqual(len(chart["groups"]), len(questions))
        self.assertEqual(len(chart["rows"]), 2 * len(questions))  # REQ-T-0001's MUST and MUST NOT statements
        for row in chart["rows"]:
            self.assertEqual([d["series"] for d in row["dots"]], ["before", "before", "after"])  # 2 base, 1 final run
        check = next(g for g in chart["groups"] if g["id"] == "check")
        self.assertEqual((check["fix_before"], check["fix_after"]), (2, 0))
        page = Path(out["data"]["html"]).read_text(encoding="utf-8")
        self.assertIn(text.strip()[:200], page)  # the page embeds the panel as rendered

    def test_a_statement_that_starts_failing_is_a_regression(self):
        self.judge("base", 1, INDEX, PASSING)
        self.judge("final", 1, INDEX, FAILING)
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        self.assertEqual((out["data"]["status"], out["data"]["regressed"]), ("FAIL", 1))
        self.assertEqual(self.sidecar(out)["outcomes"][0]["state"], "regressed")

    def test_a_run_without_final_compares_base_with_its_latest_step(self):
        self.judge("base", 1, INDEX, FAILING)
        self.judge("c1", 1, edited_index(), PASSING)
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        rec = self.sidecar(out)
        self.assertEqual((rec["finished"], rec["after_step"], out["data"]["status"]), (False, "c1", "FAIL"))
        self.assertIn("has no <span class=\"mono\">final</span> step yet", Path(out["data"]["panels"][0]).read_text(encoding="utf-8"))

    def test_a_failed_run_is_an_error_row_not_a_verdict(self):
        self.fix_loop()
        (self.w / "final-r2.json").write_text(json.dumps({"success": False, "data": None, "error": {
            "code": "JEV.HTTP", "message": "503"}}), encoding="utf-8")
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        final = self.sidecar(out)["steps"][-1]
        self.assertEqual((final["tally"], final["status"], final["errors"]), ("yes 1/1, 1 error", "flaky",
                                                                                ["final-r2: JEV.HTTP: 503"]))
        self.assertEqual(out["data"]["status"], "FAIL")

    def test_what_is_not_a_fix_workspace_is_refused(self):
        code, out = report(["quality", "--fix-dir", str(self.d), "--out", str(self.d / "out")])
        self.assertEqual((code, out["error"]["code"]), (2, "REPORT.NO_RUNS"))
        code, out = self.quality_report()  # a workspace with no base run
        self.assertEqual((code, out["error"]["code"]), (2, "REPORT.NO_RUNS"))
        self.judge("base", 1, INDEX, FAILING)
        other = json.loads((self.w / "base-r1.json").read_text(encoding="utf-8"))
        other["data"]["results"][0]["record"]["id"] = "REQ-T-0404"
        (self.w / "c1-r1.json").write_text(json.dumps(other), encoding="utf-8")
        code, out = self.quality_report()
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))
        self.assertIn("REQ-T-0404", out["error"]["message"])

    def test_record_text_is_escaped(self):
        self.judge("base", 1, INDEX, PASSING)
        (self.w / "current.md").write_text(ORIGINAL_MD.replace("Exit codes", "<script>alert(1)</script>"), encoding="utf-8")
        code, out = self.quality_report()
        self.assertEqual(code, 0, out)
        page = Path(out["data"]["html"]).read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)", page)
        self.assertIn("&lt;script&gt;alert(1)", page)


class DriftReview(ReportCase):
    def test_kept_and_discarded_changes_are_in_the_panel(self):
        self.fix_loop()
        review = {"reviewed_at": "2026-11-10",
                  "kept": [{"change": "missing file as a condition", "why": "testable", "authority": "docs/cli.md:12"}],
                  "discarded": [{"change": "dropped exit code", "why": "drift"}]}
        code, out = self.quality_report("--review", write(self.d, "review.json", review))
        self.assertEqual(code, 0, out)
        text = Path(out["data"]["panels"][0]).read_text(encoding="utf-8")
        for expected in ("missing file as a condition", "docs/cli.md:12", "dropped exit code"):
            self.assertIn(expected, text)

    def test_a_review_off_contract_is_validation_input(self):
        self.fix_loop()
        bad = {"reviewed_at": "2026-11-10", "kept": [{"change": "x"}]}
        code, out = self.quality_report("--review", write(self.d, "review.json", bad))
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))
        self.assertIn("kept.0.why", out["error"]["message"])


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
        dom = xml.dom.minidom.parse(out["data"]["panels"][-1])
        chart = json.loads([d for d in dom.getElementsByTagName("div") if d.getAttribute("class") == "conf-chart"][0]
                           .getAttribute("data-chart"))
        self.assertEqual([(g["id"], g["fix_before"], g["fix_after"]) for g in chart["groups"]],
                         [("contradicts", 0, 0), ("covered", 0, 1)])
        self.assertEqual([[d["series"] for d in r["dots"]] for r in chart["rows"]], [["before", "after"]] * 2)

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
