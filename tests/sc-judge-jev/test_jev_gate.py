"""jev_gate.py: the median confidence gate over repeated quality runs, run as installed and offline."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from layout_support import SCRIPTS  # noqa: E402 - the scripts as installed

GATE = SCRIPTS / "jev_gate.py"


def req(record_id, verdict, statements):
    """A quality result for a REQ: ``statements`` is ``[(index, text, {question: (choice, confidence)})]``."""
    reason = [{"statement": {"index": index, "modal": "Must", "text": text},
               "answers": [{"id": q, "choice": c, "confidence": conf} for q, (c, conf) in answers.items()]}
              for index, text, answers in statements]
    return {"record": {"id": record_id, "kind": "req"}, "verdict": verdict,
            "waves": [{"node": "wave-1", "per": "statement", "reason": reason, "verdict": verdict}]}


def adr(record_id, verdict, answers):
    return {"record": {"id": record_id, "kind": "adr"}, "verdict": verdict,
            "waves": [{"node": "wave-1", "verdict": verdict,
                       "reason": [{"id": q, "choice": c, "confidence": conf} for q, (c, conf) in answers.items()]}]}


class GateCase(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.d = Path(self.td.name)
        self.addCleanup(self.td.cleanup)

    def write(self, name, results, success=True, error=None):
        path = self.d / name
        envelope = {"success": success, "data": {"results": results} if success else None, "error": error}
        path.write_text(json.dumps(envelope), encoding="utf-8")
        return str(path)

    def run_gate(self, *argv):
        proc = subprocess.run([sys.executable, str(GATE), *argv], capture_output=True, text=True, encoding="utf-8")
        return proc.returncode, json.loads(proc.stdout), proc.stderr

    def gate(self, *argv):
        code, out, err = self.run_gate(*argv)
        self.assertEqual((code, out["success"], out["error"], err), (0, True, None, ""), out)
        return out["data"]

    def three(self, record_id, confidences, verdicts=("yes", "yes", "yes"), text="X MUST do A."):
        return [self.write(f"r{i}.json", [req(record_id, verdict, [(1, text, {"term": ("none", conf),
                                                                                "check": ("unit test", 0.9)})])])
                for i, (conf, verdict) in enumerate(zip(confidences, verdicts))]


class MedianGateTests(GateCase):
    def test_a_dip_below_the_gate_in_one_run_still_passes_on_the_median(self):
        data = self.gate(*self.three("REQ-A-0001", (0.64, 0.52, 0.66)))
        record = data["records"][0]
        self.assertEqual((data["runs"], data["passed"], data["failed"]), (3, 1, 0))
        self.assertTrue(record["pass"])
        self.assertEqual(record["low"], [])
        self.assertEqual((record["lowest"]["question"], record["lowest"]["median"]), ("term", 0.64))

    def test_a_median_below_the_gate_fails_and_names_the_answer(self):
        data = self.gate(*self.three("REQ-A-0001", (0.61, 0.52, 0.48)))
        record = data["records"][0]
        self.assertFalse(record["pass"])
        self.assertEqual(record["low"], [{"statement": 1, "question": "term", "choice": "none", "median": 0.52,
                                          "confidences": [0.61, 0.52, 0.48], "runner_up": None}])

    def test_the_threshold_is_inclusive_and_can_be_set(self):
        runs = self.three("REQ-A-0001", (0.6, 0.6, 0.7))
        self.assertTrue(self.gate(*runs)["records"][0]["pass"])
        self.assertFalse(self.gate("--threshold", "0.65", *runs)["records"][0]["pass"])

    def test_a_no_verdict_in_most_runs_fails_whatever_the_confidences(self):
        runs = self.three("REQ-A-0001", (0.9, 0.9, 0.9), verdicts=("no", "no", "yes"))
        record = self.gate(*runs)["records"][0]
        self.assertFalse(record["pass"])
        self.assertEqual(record["verdicts"], ["no", "no", "yes"])
        self.assertTrue(self.gate(*self.three("REQ-A-0001", (0.9, 0.9, 0.9), verdicts=("no", "yes", "yes")))
                        ["records"][0]["pass"])

    def test_diagnostic_answers_never_gate(self):
        runs = [self.write(f"r{i}.json", [req("REQ-A-0001", "yes", [(1, "X MUST do A.", {
            "term": ("none", 0.8), "d_term_where": ("reference", 0.1)})])]) for i in range(3)]
        record = self.gate(*runs)["records"][0]
        self.assertTrue(record["pass"])
        self.assertEqual(record["lowest"]["question"], "term")

    def test_an_adr_gates_on_its_record_level_answers(self):
        runs = [self.write(f"r{i}.json", [adr("ADR-A-0001", "yes", {"context": ("problem and forces", conf),
                                                                     "alternatives": ("named with reasons rejected", 1.0)})])
                for i, conf in enumerate((0.38, 0.41, 0.72))]
        record = self.gate(*runs)["records"][0]
        self.assertFalse(record["pass"])
        self.assertEqual((record["kind"], record["low"][0]["statement"], record["low"][0]["question"],
                          record["low"][0]["median"]), ("adr", None, "context", 0.41))

    def test_one_run_gates_on_that_run(self):
        data = self.gate(self.three("REQ-A-0001", (0.59,), verdicts=("yes",))[0])
        self.assertEqual((data["runs"], data["records"][0]["pass"]), (1, False))


class RunnerUpTests(GateCase):
    def entry(self, conf, probabilities, runner):
        return {"id": "obligations", "choice": "1", "confidence": conf, "probabilities": probabilities, "runner_up": runner}

    def run_file(self, name, conf, probabilities, runner):
        result = {"record": {"id": "REQ-A-0001", "kind": "req"}, "verdict": "yes", "waves": [{"node": "wave-1", "reason": [
            {"statement": {"index": 2, "text": "X MUST do A and B."}, "answers": [self.entry(conf, probabilities, runner)]}]}]}
        return self.write(name, [result])

    def test_a_low_answer_names_the_option_jev_nearly_chose_with_its_median_probability_and_criterion(self):
        two = {"choice": "2", "probability": 0.3, "criterion": "Two independent obligations."}
        runs = [self.run_file("a.json", 0.48, {"1": 0.61, "2": 0.30, "3": 0.09}, two),
                self.run_file("b.json", 0.41, {"1": 0.55, "2": 0.38, "3": 0.07}, {**two, "probability": 0.38}),
                self.run_file("c.json", 0.52, {"1": 0.64, "2": 0.26, "3": 0.10}, {**two, "probability": 0.26})]
        (low,) = self.gate(*runs)["records"][0]["low"]
        self.assertEqual((low["median"], low["runner_up"]),
                         (0.48, {"choice": "2", "probability": 0.3, "criterion": "Two independent obligations."}))

    def test_runs_without_probabilities_report_no_runner_up(self):
        (low,) = self.gate(*self.three("REQ-A-0001", (0.5, 0.5, 0.5)))["records"][0]["low"]
        self.assertIsNone(low["runner_up"])

    def test_no_runner_up_when_no_other_option_has_any_probability(self):
        runs = [self.run_file(f"{i}.json", 0.5, {"1": 1.0, "2": 0.0}, None) for i in range(3)]
        self.assertIsNone(self.gate(*runs)["records"][0]["low"][0]["runner_up"])


class ComparabilityTests(GateCase):
    def test_runs_of_different_text_are_not_comparable(self):
        a = self.write("a.json", [req("REQ-A-0001", "yes", [(1, "X MUST do A.", {"term": ("none", 0.9)})])])
        b = self.write("b.json", [req("REQ-A-0001", "yes", [(1, "X MUST do B.", {"term": ("none", 0.9)})])])
        record = self.gate(a, b, a)["records"][0]
        self.assertEqual((record["pass"], record["comparable"], record["low"]), (False, False, []))

    def test_a_record_missing_from_a_run_is_not_comparable(self):
        both = [req("REQ-A-0001", "yes", [(1, "X MUST do A.", {"term": ("none", 0.9)})]),
                req("REQ-A-0002", "yes", [(1, "Y MUST do B.", {"term": ("none", 0.9)})])]
        data = self.gate(self.write("a.json", both), self.write("b.json", both[:1]), self.write("c.json", both))
        by_id = {record["id"]: record for record in data["records"]}
        self.assertTrue(by_id["REQ-A-0001"]["pass"])
        self.assertEqual((by_id["REQ-A-0002"]["pass"], by_id["REQ-A-0002"]["comparable"]), (False, False))
        self.assertEqual((data["passed"], data["failed"]), (1, 1))


class ErrorTests(GateCase):
    def failed(self, code, *argv):
        rc, out, err = self.run_gate(*argv)
        self.assertEqual((rc, out["success"], out["data"], out["error"]["code"], err), (2, False, None, code, ""), out)
        self.assertEqual(set(out["error"]), {"code", "message", "recoverable", "suggested_action"})
        return out["error"]

    def test_a_failed_run_is_an_error_not_a_verdict(self):
        bad = self.write("bad.json", None, success=False, error={"code": "JEV.TIMEOUT", "message": "x"})
        error = self.failed("INPUT.RUN_FAILED", *self.three("REQ-A-0001", (0.9, 0.9, 0.9))[:2], bad)
        self.assertIn("JEV.TIMEOUT", error["message"])

    def test_unreadable_not_json_and_empty_run_files(self):
        self.failed("INPUT.RUN_UNREADABLE", str(self.d / "missing.json"))
        junk = self.d / "junk.json"
        junk.write_text("not json", encoding="utf-8")
        self.failed("INPUT.RUN_NOT_JSON", str(junk))
        self.failed("INPUT.RUN_EMPTY", self.write("empty.json", []))

    def test_usage_errors_are_validation_input(self):
        for argv in ([], ["--threshold", "2", "x.json"], ["--no-such-flag"]):
            with self.subTest(argv=argv):
                error = self.failed("VALIDATION.INPUT", *argv)
                self.assertTrue(error["message"].startswith("jev_gate.py"))
                self.assertIn("--help", error["suggested_action"])


if __name__ == "__main__":
    unittest.main()
