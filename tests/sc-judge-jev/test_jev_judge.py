"""Unit tests for scripts/jev_judge.py's Jev layer. Standard library only; no network is ever touched.

Ported from plan-anchor's tests/sc-plan-anchor/test_jev_judge.py: the credential lookup, the gating
table (decide), response validation, HTTP error mapping, redaction and CLI error handling. The Jev
transport (`decidr_client.call_batch_results`) is replaced with a stub where a call would happen.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from jev_support import SCRIPTS, SKILL, read_log  # noqa: F401 - renders the scripts and puts them on sys.path
import jev_judge as jj  # noqa: E402

PLAN_ROLES = {"relevance": "relevant", "compliance": "addressed", "conflict": "contradicted"}
DEV_ROLES = {"relevance": "relevant", "compliance": "implemented", "conflict": "violated", "evidence": "evidenced"}
OPTIONS = ("yes", "no", "unclear")
STATEMENT = "The runtime crates are created by copying the legacy repo's runtime crates and deleting the legacy-specific modules; no runtime crate is written from scratch."
LIVE_ENV = {"TYPESAFE_API_KEY": "sk-test-0001"}


def answer(choice, p=0.9, options=OPTIONS):
    rest = round((1 - p) / (len(options) - 1), 4)
    probs = {o: (p if o == choice else rest) for o in options}
    return {"type": "choice", "choice": choice, "confidence": p, "probabilities": probs}


def plan_answers(rel="yes", comp="yes", conf="no", p=0.9, rel_p=None, comp_p=None, conf_p=None):
    return {"relevant": answer(rel, rel_p if rel_p is not None else p),
            "addressed": answer(comp, comp_p if comp_p is not None else p),
            "contradicted": answer(conf, conf_p if conf_p is not None else p)}


def typed_answers(answers):
    """Use the shared fixture answer form without importing the optional wheel."""
    return {key: jj.decidr_client.typed_answer(value) for key, value in answers.items()}


def dev_answers(rel="yes", comp="yes", conf="no", evid="yes", p=0.9, evid_p=None):
    return {"relevant": answer(rel, p), "implemented": answer(comp, p), "violated": answer(conf, p),
            "evidenced": answer(evid, evid_p if evid_p is not None else p)}


def write(d, name, value):
    path = Path(d) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) if not isinstance(value, str) else value, encoding="utf-8")
    return str(path)


def run_cli(argv):
    """Run main() in-process; returns (exit code, parsed JSON or raw text)."""
    buf = io.StringIO()
    with contextlib.ExitStack() as controlled:
        api = sys.modules.get("sc_agent")
        native = getattr(api, "_native", None)
        if native is not None:
            for operation in ("send", "send_batch"):
                if hasattr(api, operation) and getattr(api, operation) is getattr(native, operation, None):
                    controlled.enter_context(mock.patch.object(api, operation,
                        side_effect=AssertionError("unit test reached an uncontrolled native decision call")))
        send_name = "_call_batch_results" if hasattr(jj.decidr_client, "_call_batch_results") else "call_batch_results"
        if not isinstance(getattr(jj.decidr_client, send_name), mock.Mock):
            controlled.enter_context(mock.patch.object(jj.decidr_client, send_name,
                side_effect=AssertionError("unit test reached an uncontrolled native decision call")))
        controlled.enter_context(contextlib.redirect_stdout(buf))
        code = jj.main(argv)
    out = buf.getvalue()
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        return code, out


@contextlib.contextmanager
def env(**values):
    # Unit fixtures control the environment; sc-agent owns credential resolution.
    values.setdefault("JUDGE_JEV_LOG_ROOT", os.environ["JUDGE_JEV_LOG_ROOT"])
    with mock.patch.dict(os.environ, values, clear=True):
        yield


def consented():
    """The repository's allow_remote_judge is true (the real lookup is tested in test_jev_remote_judge_setting)."""
    stack = contextlib.ExitStack()
    stack.enter_context(mock.patch.object(jj.decidr_client, "remote_judge_consent", return_value={"ok": True, "value": None}))
    return stack


def ok(result):
    """The value of an Ok result; any Err fails the test with the error it carries."""
    if not isinstance(result, jj.Ok):
        raise AssertionError(f"expected Ok, got {result!r}")
    return result.value


def failure(result):
    """The ClientError of an Err result; an Ok fails the test."""
    if not isinstance(result, jj.Err) or not isinstance(result.error, jj.ClientError):
        raise AssertionError(f"expected Err(ClientError), got {result!r}")
    return result.error


def wheel_record(result, position=0):
    """Build a controlled generated-client record from a wheel-shaped wire result."""
    line, mapped = result
    parsed = json.loads(line)
    attempts = parsed.get("sends")
    error = parsed.get("error")
    if isinstance(error, dict):
        category = error.get("category")
        code = mapped or {"auth": "AUTH.CREDENTIALS", "quota": "DECIDR.RATE_LIMITED", "busy": "DECIDR.OVERLOADED",
                          "network": "DECIDR.NETWORK", "response_invalid": "DECIDR.RESPONSE_INVALID",
                          "validation": "DECIDR.VALIDATION", "cancelled": "CANCELED"}.get(category, "DECIDR.ERROR")
        if error.get("id") == "decision.context_exceeded":
            code = "DECIDR.CONTEXT_EXCEEDED"
        detail = jj.ClientError(code, error.get("message", "wheel error"),
                                retryable=(error.get("id") == "decision.context_exceeded" or
                                           category in ("quota", "busy", "network", "response_invalid")),
                                action=error.get("recovery"), status=error.get("status"),
                                retry_after_ms=error.get("retry_after_ms"), attempts=attempts, data=error)
        return {"ok": False, "error": detail, "position": position, "line": line, "attempts": attempts}
    return {"ok": True, "value": typed_answers(parsed["response"]["answers"]),
            "model_answered": parsed["response"].get("model"), "usage": parsed["response"].get("usage", {}),
            "position": position, "line": line, "attempts": attempts}


class BatchTransport:
    """Stub sc-agent's wire results as generated-client records and invoke completion callbacks."""

    def __init__(self, *results):
        self.results = list(results)
        self.bodies = []

    def __call__(self, requests, **kwargs):
        self.bodies.extend(request if isinstance(request, dict) else json.loads(request) for request in requests)
        records = []
        for position, _request in enumerate(requests):
            result = self.results.pop(0) if self.results else (json.dumps({"response": {
                "model": "jev-1.13.0", "answers": plan_answers()}, "sends": 1}), None)
            records.append(wheel_record(result, position))
        for record in records:
            if kwargs.get("on_result") is not None:
                kwargs["on_result"](record)
        return {"ok": True, "value": records, "position": None, "line": None, "attempts": None}


def request_line(item_id="ex-42", text="Sprint 2 copies the legacy runtime crates.", candidate="cur", questions=None):
    """One batch request line with the shipped plan question set as its only candidate."""
    if questions is None:
        questions = ok(jj.load_question_set("plan")).questions
    return {"item": {"id": item_id, "title": "", "text": text},
            "anchor": {"id": "ANC-001", "statement": STATEMENT, "scope": "the runtime crates", "kind": "directive"},
            "questions": [{"candidate_id": candidate, "questions": questions}]}


def jsonl(lines):
    return "".join(json.dumps(x) + "\n" for x in lines)


def result_lines(text):
    return [json.loads(x) for x in text.splitlines() if x.strip()]


class ConsentBoundaryTests(unittest.TestCase):
    def test_remote_preflight_uses_the_shared_consent_gate(self):
        with mock.patch.object(jj.decidr_client, "remote_judge_consent", return_value={"ok": True, "value": None}) as consent:
            self.assertEqual(jj.decidr_client.remote_preflight("controlled-repository", "record text"), {"ok": True, "value": None})
        consent.assert_called_once_with("controlled-repository", "record text")
        self.assertFalse(hasattr(jj, "remote_judge_consent"))

    def test_remote_preflight_propagates_the_shared_refusal(self):
        refused = jj.ClientError("POLICY.REMOTE_JUDGE_DISABLED", "consent is absent")
        with mock.patch.object(jj.decidr_client, "remote_judge_consent", return_value={"ok": False, "error": refused}):
            got = jj.decidr_client.remote_preflight("controlled-repository", "record text")
        self.assertIs(got["error"], refused)


class DecideTests(unittest.TestCase):
    def decide(self, answers, roles=PLAN_ROLES, t=0.6):
        return jj.decide(typed_answers(answers), roles, t)

    def test_row1_not_applicable(self):
        self.assertEqual(self.decide(plan_answers(rel="no", comp="no", conf="no"))[0], "not_applicable")
        # relevance "no" below threshold falls through to underspecified
        self.assertEqual(self.decide(plan_answers(rel="no", rel_p=0.5))[0], "underspecified")

    def test_row2_contradicted_outranks_underspecification(self):
        self.assertEqual(self.decide(plan_answers(rel="yes", comp="no", conf="yes"))[0], "contradicted")
        self.assertEqual(self.decide(plan_answers(rel="unclear", comp="unclear", conf="yes"))[0], "contradicted")
        self.assertEqual(self.decide(plan_answers(rel="yes", comp="no", conf="yes", conf_p=0.55))[0], "not_addressed")

    def test_row3_underspecified(self):
        self.assertEqual(self.decide(plan_answers(rel="unclear"))[0], "underspecified")
        self.assertEqual(self.decide(plan_answers(rel_p=0.59))[0], "underspecified")
        self.assertEqual(self.decide(plan_answers(comp="unclear"))[0], "underspecified")
        # a low-confidence conflict yes (or unclear) never passes, even when compliance is a confident yes
        self.assertEqual(self.decide(plan_answers(conf="yes", conf_p=0.4)), ("underspecified", 0.4))
        self.assertEqual(self.decide(plan_answers(conf="unclear"))[0], "underspecified")
        self.assertEqual(self.decide(plan_answers(conf="no", conf_p=0.25))[0], "underspecified")
        verdict, min_conf = self.decide(plan_answers(comp_p=0.3))
        self.assertEqual((verdict, min_conf), ("underspecified", 0.3))

    def test_row4_not_addressed(self):
        self.assertEqual(self.decide(plan_answers(comp="no"))[0], "not_addressed")

    def test_row5_asserted_only_needs_evidence_role(self):
        self.assertEqual(self.decide(dev_answers(evid="no"), DEV_ROLES)[0], "asserted_only")
        self.assertEqual(self.decide(dev_answers(evid="no", evid_p=0.4), DEV_ROLES)[0], "satisfied")
        self.assertEqual(self.decide(dev_answers(evid="unclear"), DEV_ROLES)[0], "satisfied")
        no_evidence_role = {k: v for k, v in DEV_ROLES.items() if k != "evidence"}
        self.assertEqual(self.decide(dev_answers(evid="no"), no_evidence_role)[0], "satisfied")

    def test_row6_satisfied_and_min_confidence(self):
        verdict, min_conf = self.decide(plan_answers(rel_p=0.95, comp_p=0.7, conf_p=0.8))
        self.assertEqual((verdict, min_conf), ("satisfied", 0.7))

    def test_row7_fallthrough(self):
        answers = plan_answers()
        answers["addressed"]["choice"] = "maybe"
        self.assertEqual(self.decide(answers)[0], "underspecified")
        self.assertEqual(self.decide({}), ("underspecified", 0.0))

    def test_threshold_boundaries(self):
        self.assertEqual(self.decide(plan_answers(p=0.6), t=0.6)[0], "satisfied")
        self.assertEqual(self.decide(plan_answers(p=0.6), t=0.61)[0], "underspecified")
        self.assertEqual(self.decide(plan_answers(rel="no", p=0.1), t=0.0)[0], "not_applicable")

    def test_typed_noul_answers(self):
        self.assertEqual(jj.answer_choice(jj.decidr_client.NoulAnswer(0.8)), ("yes", 0.6000000000000001))
        self.assertEqual(jj.answer_choice(jj.decidr_client.NoulAnswer(0.2)), ("no", 0.6))
        self.assertEqual(jj.answer_choice(jj.decidr_client.NoulAnswer(0.5)), ("yes", 0.0))
        answers = plan_answers()
        answers["contradicted"] = {"type": "noul", "noul": 0.9}
        self.assertEqual(self.decide(answers)[0], "contradicted")

    def test_raw_answer_dicts_are_not_a_second_consumer_surface(self):
        for value in ({"type": "noul", "noul": 0.8}, {"probability": 0.2}, {"p": 0.5}, answer("yes")):
            with self.subTest(answer=value), self.assertRaises(AttributeError):
                jj.answer_choice(value)


class RedactionTests(unittest.TestCase):
    def test_every_emitted_value_redacts_the_live_key_and_bearer_tokens(self):
        buf = io.StringIO()
        with env(TYPESAFE_API_KEY="ts-secret-123456"), contextlib.redirect_stdout(buf):
            jj.emit({"message": "key=ts-secret-123456", "header": "Bearer another-secret"})
        rendered = buf.getvalue()
        self.assertNotIn("ts-secret-123456", rendered)
        self.assertNotIn("another-secret", rendered)
        self.assertEqual(json.loads(rendered), {"message": "key=<redacted>", "header": "Bearer <redacted>"})

    def test_batch_result_lines_never_carry_the_key(self):
        with tempfile.TemporaryDirectory() as d:
            src = write(d, "in.jsonl", jsonl([request_line(text="token ts-secret-123456 in the item")]))
            fixture = write(d, "answers.json", {"*": plan_answers()})
            log_root = Path(d) / "logs"
            with env(TYPESAFE_API_KEY="ts-secret-123456", JUDGE_JEV_LOG_ROOT=str(log_root)):
                code, out = run_cli(["batch", "--input", src, "--run-name", "r1", "--answers-file", fixture])
            events = read_log(log_root)
            self.assertTrue(events, "batch log must contain events before checking redaction")
            log = json.dumps(events, ensure_ascii=False)
        self.assertEqual(code, 0, out)
        self.assertNotIn("ts-secret-123456", json.dumps(out))
        self.assertNotIn("ts-secret-123456", log)
        self.assertEqual(out["request"]["state"]["item"]["text"], "token <redacted> in the item")


class ErrorHandlingTests(unittest.TestCase):
    def test_load_json_rejects_non_files(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("", d, str(Path(d) / "missing.json")):
                self.assertEqual(failure(jj.load_json(bad, "thing")).code, "INPUT.MISSING", bad)
            bad_json = write(d, "bad.json", "{")
            self.assertEqual(failure(jj.load_json(bad_json, "thing")).code, "INPUT.MALFORMED")
            good = write(d, "good.json", {"a": 1})
            self.assertEqual(ok(jj.load_json(good, "thing")), {"a": 1})

    def test_every_file_argument_yields_json_errors(self):
        with tempfile.TemporaryDirectory() as d:
            missing = str(Path(d) / "none.jsonl")
            code, out = run_cli(["batch", "--input", missing, "--dry-run"])
            self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MISSING"))
            src = write(d, "in.jsonl", jsonl([request_line()]))
            code, out = run_cli(["batch", "--input", src, "--answers-file", missing])
            self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MISSING"))
            self.assertFalse((Path(d) / "runs").exists())

    def test_missing_sc_decidr_is_a_typed_dependency_error(self):
        with tempfile.TemporaryDirectory() as d:
            src = write(d, "in.jsonl", jsonl([request_line()]))
            with mock.patch.dict(sys.modules, {"sc_agent": None}):
                code, out = run_cli(["batch", "--input", src, "--dry-run"])
        self.assertEqual((code, out["error"]["code"]), (2, "DEPENDENCY.SC_DECIDR"))
        self.assertIn("Install sc-decidr", out["error"]["suggested_action"])

    def test_unexpected_exceptions_become_script_internal(self):
        with mock.patch.object(jj, "cmd_batch", side_effect=RuntimeError("boom")):
            code, out = run_cli(["batch", "--input", "x"])
        self.assertEqual((code, out["error"]["code"], out["error"]["message"]), (2, "SCRIPT.INTERNAL", "RuntimeError: boom"))
        with mock.patch.object(jj, "cmd_batch", side_effect=KeyboardInterrupt):
            code, out = run_cli(["batch", "--input", "x"])
        self.assertEqual((code, out["canceled"]), (130, True))

    def test_numeric_flags_are_checked(self):
        for flag, value in (("--threshold", "high"), ("--max-workers", "2.5"), ("--repeat", "lots"),
                            ("--timeout", "soon")):
            with env():
                code, out = run_cli(["batch", "--input", "x", "--dry-run", flag, value])
            self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), flag)
            self.assertIn(f"argument {flag}: invalid", out["error"]["message"])
        self.assertEqual((jj.DEFAULT_MODEL, jj.DEFAULT_THRESHOLD), ("jev-latest", 0.6))
        self.assertEqual(jj.BATCH_MAX_WORKERS, 4)

    def test_out_of_range_values_are_validation_input(self):
        with tempfile.TemporaryDirectory() as d:
            src = write(d, "in.jsonl", jsonl([request_line()]))
            for flag, value in (("--threshold", "1.5"), ("--max-workers", "0"), ("--repeat", "0"), ("--request-prefix", "a b")):
                code, out = run_cli(["batch", "--input", src, "--dry-run", flag, value])
                self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), flag)
            code, out = run_cli(["batch", "--input", src, "--dry-run", "--run-name", "bad name"])
            self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))
            self.assertFalse((Path(d) / "runs").exists())

    def test_exit_codes(self):
        # A command that ran exits 0; only a failure to run is nonzero, and never 1.
        self.assertFalse(hasattr(jj, "exit_code_for"))
        with tempfile.TemporaryDirectory() as d:
            src = write(d, "in.jsonl", jsonl([request_line()]))
            code, out = run_cli(["batch", "--input", src, "--dry-run"])
            self.assertEqual((code, out["dry_run"], out["ok"]), (0, True, False))
            code, out = run_cli(["batch", "--input", str(Path(d) / "missing.jsonl")])
            self.assertEqual((code, out["success"], out["data"]), (2, False, None))
            self.assertEqual(set(out["error"]), {"code", "message", "recoverable", "suggested_action"})

    def test_documented_question_sets_load(self):
        for gate in ("plan", "dev"):
            qs = ok(jj.load_question_set(gate))
            self.assertEqual(qs.gate, gate)
            for q in qs.questions.values():
                self.assertEqual(set(q["criteria"]), set(OPTIONS))
        self.assertEqual(set(ok(jj.load_question_set("dev")).roles), {"relevance", "compliance", "conflict", "evidence"})
        self.assertEqual(failure(jj.load_question_set("plan", str(Path(__file__)))).code, "INPUT.MALFORMED")

    def test_batch_and_quality_are_the_subcommands(self):
        parser = jj.build_parser()
        sub = next(a for a in parser._actions if a.dest == "cmd")
        self.assertEqual(sorted(sub.choices), ["batch", "compare-definition", "doctor", "drift", "quality", "validate"])


if __name__ == "__main__":
    unittest.main()
