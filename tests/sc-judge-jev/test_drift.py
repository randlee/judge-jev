"""`jev_judge.py drift`: one Jev request per changed record (the original's normative text plus a unified diff to the
rewrite), a keep question per original obligation, plus `added` and `verification`; controls check Jev reads it.

Answers come from answers files keyed '<item>/drift' (or '*'); Jev is never called.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jev_support  # noqa: F401  (renders the scripts and puts them on sys.path)
import jev_judge as jj  # noqa: E402

from test_jev_judge import answer, env, run_cli, write  # noqa: E402
from test_quality import never_called, requirement  # noqa: E402

KEEP = list(jj.DRIFT_KEEP_CRITERIA)
YN = ["no", "yes"]

OLD = {
    "metadata": {"repository": "urn:raptor:repo:test", "files": 1, "records": 4},
    "requirements": [requirement("REQ-T-0001", "The CLI MUST exit 2 on a missing file.", "MustNot: The CLI MUST NOT write outside the worktree."),
                     requirement("REQ-T-0002", "A run MUST log its name."),
                     requirement("REQ-T-0003", "Gone MUST stay gone.")],
    "decisions": [{"id": "ADR-T-0001", "title": "Use SQLite", "decision": {"text": "1. Records MUST be stored in SQLite.\n\n2. Writes MUST use one connection."}}],
    "diagnostics": {"issues": [], "summary": {"records": 4}},
}
NEW = copy.deepcopy(OLD)
NEW["requirements"][0]["requirement_statement"]["statements"][0]["text"] = "On a missing file the CLI MUST exit with code 2."
NEW["requirements"] = NEW["requirements"][:2] + [requirement("REQ-T-0004", "New MUST appear.")]
NEW["decisions"][0]["decision"]["text"] = "1. Records MUST be stored in SQLite.\n\n2. Writes MUST use one connection within 5 ms."


def answers(n, p=0.9, adr=False, **choices):
    out = {f"keep_{i}": answer(choices.get(f"keep_{i}", "same"), p=p, options=KEEP) for i in range(1, n + 1)}
    out["added"] = answer(choices.get("added", "no"), p=p, options=YN)
    if not adr:
        out["verification"] = answer(choices.get("verification", "no"), p=p, options=YN)
    return out


class DriftCase(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        self.old, self.new = write(self.d, "old.json", OLD), write(self.d, "new.json", NEW)

    def drift(self, *argv, answers=None):
        extra = ["--answers-file", write(self.d, "answers.json", answers)] if answers is not None else []
        with env(), mock.patch.object(jj, "call_jev", never_called):
            return run_cli(["drift", "--old-index", self.old, "--new-index", self.new, *argv,
                            "--run-dir", str(self.d / "logs"), "--run-name", "d1", *extra])


class Selection(DriftCase):
    def test_changed_compares_only_records_whose_normative_text_differs_and_lists_deleted_and_added(self):
        code, out = self.drift("--changed", "--controls", "0", "--dry-run")
        self.assertEqual(code, 0, out)
        data = out["data"]
        self.assertEqual([r["item"]["id"] for r in data["requests"]], ["ADR-T-0001", "REQ-T-0001"])
        self.assertEqual(data["unchanged"], ["REQ-T-0002"])
        self.assertEqual(data["deleted"], ["REQ-T-0003"])
        self.assertEqual(data["added"], ["REQ-T-0004"])

    def test_the_request_holds_the_original_and_a_diff_not_the_whole_rewrite(self):
        _code, out = self.drift("--req", "REQ-T-0001", "--controls", "0", "--dry-run")
        text = json.loads(out["data"]["requests"][0]["item"]["text"])
        self.assertEqual(set(text), {"original", "diff"})
        self.assertIn("- The CLI MUST exit 2 on a missing file.", text["original"])
        self.assertIn("+- On a missing file the CLI MUST exit with code 2.", text["diff"])
        self.assertIn("--- original", text["diff"])

    def test_full_form_sends_both_texts_whole_and_no_diff(self):
        _code, out = self.drift("--req", "REQ-T-0001", "--controls", "0", "--form", "full", "--dry-run")
        self.assertEqual(out["data"]["form"], "full")
        text = json.loads(out["data"]["requests"][0]["item"]["text"])
        self.assertEqual(set(text), {"original", "candidate"})
        self.assertIn("- On a missing file the CLI MUST exit with code 2.", text["candidate"])

    def test_one_keep_question_per_original_obligation_and_no_verification_for_an_adr(self):
        _code, out = self.drift("--req", "REQ-T-0001", "--adr", "ADR-T-0001", "--controls", "0", "--dry-run")
        qs = {r["item"]["id"]: r["questions"][0]["questions"] for r in out["data"]["requests"]}
        self.assertEqual(sorted(qs["REQ-T-0001"]), ["added", "keep_1", "keep_2", "verification"])
        self.assertEqual(sorted(qs["ADR-T-0001"]), ["added", "keep_1", "keep_2"])
        self.assertIn("Writes MUST use one connection.", qs["ADR-T-0001"]["keep_2"]["instructions"])

    def test_ids_or_changed_but_not_both_or_neither(self):
        for argv in ([], ["--changed", "--req", "REQ-T-0001"]):
            code, out = self.drift(*argv, "--dry-run")
            self.assertEqual(code, 2)
            self.assertEqual(out["error"]["code"], "VALIDATION.INPUT")


class Verdicts(DriftCase):
    def test_all_pass_answers_are_no_drift(self):
        code, out = self.drift("--req", "REQ-T-0001", "--controls", "0", answers={"REQ-T-0001/drift": answers(2)})
        self.assertEqual(code, 0, out)
        rec = out["data"]["records"][0]
        self.assertEqual((rec["verdict"], rec["findings"]), ("no-drift", []))
        self.assertTrue(out["data"]["valid"])

    def test_a_dropped_obligation_is_drift_and_names_the_obligation(self):
        _code, out = self.drift("--req", "REQ-T-0001", "--controls", "0", answers={"REQ-T-0001/drift": answers(2, keep_2="dropped")})
        rec = out["data"]["records"][0]
        self.assertEqual(rec["verdict"], "drift")
        self.assertEqual(rec["findings"][0]["obligation"], "The CLI MUST NOT write outside the worktree.")

    def test_an_added_threshold_is_drift(self):
        _code, out = self.drift("--adr", "ADR-T-0001", "--controls", "0", answers={"ADR-T-0001/drift": answers(2, adr=True, added="yes")})
        self.assertEqual(out["data"]["records"][0]["verdict"], "drift")

    def test_a_low_confidence_pass_is_uncertain_not_no_drift(self):
        _code, out = self.drift("--req", "REQ-T-0001", "--controls", "0", answers={"REQ-T-0001/drift": answers(2, p=0.4)})
        self.assertEqual(out["data"]["records"][0]["verdict"], "uncertain")


class Controls(DriftCase):
    def fixture(self, same, drop):
        return {"REQ-T-0001/drift": answers(2), "REQ-T-0001.ctl-same/drift": same, "REQ-T-0001.ctl-drop-1/drift": drop}

    def test_controls_that_read_correctly_keep_the_run_valid(self):
        code, out = self.drift("--req", "REQ-T-0001", "--controls", "1", answers=self.fixture(answers(2), answers(2, keep_1="dropped")))
        self.assertEqual(code, 0, out)
        self.assertEqual([c["ok"] for c in out["data"]["controls"]], [True, True])
        self.assertTrue(out["data"]["valid"])

    def test_identity_judged_as_drift_makes_the_run_invalid(self):
        _code, out = self.drift("--req", "REQ-T-0001", "--controls", "1", answers=self.fixture(answers(2, added="yes"), answers(2, keep_1="dropped")))
        self.assertFalse(out["data"]["valid"])

    def test_a_drop_control_must_find_the_removed_obligation_itself(self):
        _code, out = self.drift("--req", "REQ-T-0001", "--controls", "1", answers=self.fixture(answers(2), answers(2, keep_2="dropped")))
        self.assertFalse(out["data"]["controls"][1]["ok"])
        self.assertFalse(out["data"]["valid"])

    def test_the_drop_control_removes_one_statement_from_the_diffed_text(self):
        _code, out = self.drift("--req", "REQ-T-0001", "--controls", "1", "--dry-run")
        drop = next(r for r in out["data"]["requests"] if r["item"]["id"] == "REQ-T-0001.ctl-drop-1")
        diff = json.loads(drop["item"]["text"])["diff"]
        self.assertIn("-- The CLI MUST exit 2 on a missing file.", diff)
        same = next(r for r in out["data"]["requests"] if r["item"]["id"] == "REQ-T-0001.ctl-same")
        self.assertEqual(json.loads(same["item"]["text"])["diff"], "")


if __name__ == "__main__":
    unittest.main()
