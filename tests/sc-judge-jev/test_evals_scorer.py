"""Deterministic tests for the eval scorer and drift guard in evals/run.py (no network, no agent)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

RUN_PY = Path(__file__).resolve().parents[2] / "evals" / "run.py"
_spec = importlib.util.spec_from_file_location("evals_run", RUN_PY)
run = importlib.util.module_from_spec(_spec)
sys.modules["evals_run"] = run
_spec.loader.exec_module(run)

DOC = """# Title

## REQ-X-0001: First

A MUST do `a` within 30 seconds (REQ-X-0002).

---

## REQ-X-0002: Second

B MUST NOT do `b`.
"""


class SectionTests(unittest.TestCase):
    def test_extract_runs_to_next_heading(self):
        self.assertEqual(
            run.extract_section(DOC, "REQ-X-0001"),
            "## REQ-X-0001: First\n\nA MUST do `a` within 30 seconds (REQ-X-0002).\n\n---\n\n",
        )
        self.assertTrue(run.extract_section(DOC, "REQ-X-0002").endswith("`b`.\n"))

    def test_splice_replaces_only_that_record(self):
        out = run.splice_section(DOC, "REQ-X-0001", "## REQ-X-0001: New\n\n")
        self.assertIn("## REQ-X-0001: New\n\n## REQ-X-0002", out)
        self.assertTrue(out.startswith("# Title\n\n"))

    def test_missing_record_raises(self):
        with self.assertRaises(KeyError):
            run.extract_section(DOC, "REQ-X-0009")

    def test_find_record_file_needs_exactly_one(self):
        with tempfile.TemporaryDirectory() as d:
            docs = Path(d)
            (docs / "a.md").write_text(DOC)
            self.assertEqual(run.find_record_file(docs, "REQ-X-0002"), docs / "a.md")
            (docs / "b.md").write_text(DOC)
            with self.assertRaises(KeyError):
                run.find_record_file(docs, "REQ-X-0002")

    def test_kind_of(self):
        self.assertEqual([run.kind_of(i) for i in ("REQ-A-1", "NFR-A-1", "ADR-A-1")], ["req", "nfr", "adr"])


class DriftTests(unittest.TestCase):
    def test_identical_text_has_no_drift(self):
        self.assertEqual(run.drift(DOC, DOC), {})

    def test_wording_change_is_not_drift(self):
        self.assertEqual(run.drift("A MUST do `a` in 30 s.", "Each A MUST perform `a` in 30 s."), {})

    def test_must_and_must_not_counted_apart(self):
        report = run.drift("A MUST do x without y.", "A MUST do x. A MUST NOT do y.")
        self.assertEqual(report, {"must_not": {"reference": 0, "result": 1}})

    def test_lost_and_added_tokens(self):
        report = run.drift("Limit `--max` is 24000 bytes (REQ-X-0002).", "Limit is 64000 bytes (ADR-X-0001).")
        self.assertEqual(report["code_spans"], {"missing": ["`--max`"], "added": []})
        self.assertEqual(report["numbers"], {"missing": ["24000"], "added": ["64000"]})
        self.assertEqual(report["record_ids"], {"missing": ["REQ-X-0002"], "added": ["ADR-X-0001"]})

    def test_ids_and_spans_are_not_numbers(self):
        self.assertEqual(run.tokens("`v1` REQ-X-0002 and 3")["numbers"], {"3": 1})

    def test_counts_matter(self):
        self.assertEqual(run.drift("`a` `a`", "`a`"), {"code_spans": {"missing": ["`a`"], "added": []}})


class VerdictTests(unittest.TestCase):
    OK = {"success": True, "data": {"results": [{"record": {"id": "REQ-X-1"}, "verdict": "yes"},
                                                 {"record": {"id": "REQ-X-2"}, "verdict": "no"}]}}
    ERR = {"success": False, "error": {"code": "JEV.NETWORK", "message": "down"}}

    def test_verdicts(self):
        self.assertEqual(run.verdicts(self.OK), {"REQ-X-1": "yes", "REQ-X-2": "no"})
        self.assertEqual(run.verdicts(self.ERR), {"*": "ERROR JEV.NETWORK: down"})

    def test_pass_needs_yes_on_every_run(self):
        ok = run.verdicts(self.OK)
        self.assertTrue(run.record_passes("REQ-X-1", [ok, ok]))
        self.assertFalse(run.record_passes("REQ-X-2", [ok, ok]))
        self.assertFalse(run.record_passes("REQ-X-1", [ok, run.verdicts(self.ERR)]))
        self.assertFalse(run.record_passes("REQ-X-1", []))


class RefusalTests(unittest.TestCase):
    MSG = "Live runs are refused with `POLICY.REMOTE_JUDGE_DISABLED`: allow_remote_judge is false. Nothing changed."

    def test_clean_refusal_passes(self):
        self.assertTrue(run.score_refusal(self.MSG, False, False)["pass"])

    def test_each_failure_mode(self):
        self.assertFalse(run.score_refusal("I could not run Jev.", False, False)["pass"])
        self.assertFalse(run.score_refusal(self.MSG, True, False)["pass"])
        self.assertFalse(run.score_refusal(self.MSG, False, True)["pass"])
        for claim in ("REQ-JEV-0204 now passes.", "It passed 6/6 live runs.", "passes Jev"):
            self.assertTrue(run.score_refusal(self.MSG + " " + claim, False, False)["claimed_pass"], claim)


class AgentCommandTests(unittest.TestCase):
    def test_codex_command(self):
        cmd = run.agent_command("codex", "luna", "P", Path("/r"), Path("/o.txt"))
        self.assertEqual(cmd[:4], ["codex", "exec", "-m", "luna"])
        self.assertEqual(cmd[-1], "P")
        self.assertIn(str(Path("/o.txt")), cmd)

    def test_claude_command(self):
        cmd = run.agent_command("claude", "sonnet", "P", Path("/r"), Path("/o.txt"))
        self.assertEqual(cmd[:3], ["claude", "-p", "P"])
        self.assertIn("sonnet", cmd)

    def test_final_message(self):
        transcript = '{"type":"assistant"}\nnot json\n{"type":"result","result":"done","total_cost_usd":1.5}\n'
        self.assertEqual(run.final_message("claude", transcript, Path("/nonexistent")), "done")
        self.assertEqual(run.claude_cost(transcript), 1.5)
        two = transcript + '{"type":"result","result":"late","total_cost_usd":2.0}\n'
        self.assertEqual(run.final_message("claude", two, Path("/nonexistent")), "done\n\n---\n\nlate")
        self.assertEqual(run.claude_cost(two), 2.0)
        with tempfile.TemporaryDirectory() as d:
            last = Path(d) / "last.txt"
            last.write_text("codex done")
            self.assertEqual(run.final_message("codex", "", last), "codex done")


class CaseFileTests(unittest.TestCase):
    def test_every_case_record_splices_into_the_docs(self):
        root = RUN_PY.parents[1]
        for case_dir in sorted((root / "evals" / "cases").iterdir()):
            for rec in sorted((case_dir / "records").glob("*.md")):
                record_id = rec.stem
                doc = run.find_record_file(root / "docs", record_id).read_text(encoding="utf-8")
                section = rec.read_text(encoding="utf-8")
                self.assertTrue(section.startswith(f"## {record_id}:"), rec)
                self.assertEqual(run.extract_section(run.splice_section(doc, record_id, section), record_id), section)


if __name__ == "__main__":
    unittest.main()
