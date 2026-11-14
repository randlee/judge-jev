"""Unit tests for scripts/jev_judge.py's Jev layer. Standard library only; no network is ever touched.

Ported from plan-anchor's tests/sc-plan-anchor/test_jev_judge.py: the credential lookup, the gating
table (decide), response validation, HTTP error mapping, redaction and CLI error handling. The Jev
transport (`jev_judge.call_jev`) is replaced with a stub where a call would happen.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import re
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
    with contextlib.redirect_stdout(buf):
        code = jj.main(argv)
    out = buf.getvalue()
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        return code, out


@contextlib.contextmanager
def env(**values):
    # Unit fixtures control both credential sources; never consult a developer's store.
    with mock.patch.dict(os.environ, values, clear=True):
        yield


def consented():
    """The repository's allow_remote_judge is true (the real lookup is tested in test_jev_remote_judge_setting)."""
    return mock.patch.object(jj, "remote_judge_consent", return_value=jj.Ok(None))


def ok(result):
    """The value of an Ok result; any Err fails the test with the error it carries."""
    if not isinstance(result, jj.Ok):
        raise AssertionError(f"expected Ok, got {result!r}")
    return result.value


def failure(result):
    """The JudgeError of an Err result; an Ok fails the test."""
    if not isinstance(result, jj.Err) or not isinstance(result.error, jj.JudgeError):
        raise AssertionError(f"expected Err(JudgeError), got {result!r}")
    return result.error


class Transport:
    """Stub for jev_judge.call_jev: a queue of responses (dicts, returned as Ok) or JudgeErrors (returned as Err), recorded per call."""

    def __init__(self, *script, gate="plan"):
        self.script = list(script)
        self.bodies = []
        self.gate = gate

    def __call__(self, body, api_key, timeout):
        self.bodies.append(json.loads(json.dumps(body)))
        step = self.script.pop(0) if self.script else self.default()
        if isinstance(step, jj.JudgeError):
            return jj.Err(step)
        if isinstance(step, Exception):
            raise step
        return jj.Ok(step)

    def default(self):
        return {"model": "jev-1.13.0", "answers": dev_answers() if self.gate == "dev" else plan_answers()}


class ScDecidrStub:
    """Deterministic wheel contract adapter for tests; no socket or wall-clock behavior."""

    def __init__(self, transport):
        self.transport = transport

    class CancelToken:
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    def send_batch(self, requests, *, model, project, agent_role, provider=None, cancel=None,
                   on_result=None, general_log=None, session_log=None, config_dir=None):
        results = []
        for position, raw in enumerate(requests):
            body = json.loads(raw)
            returned = self.transport(body, "", 0)
            if isinstance(returned, jj.Err):
                err = returned.error
                detail = {"id": {"AUTH.CREDENTIALS": "secrets.key_malformed", "JEV.NETWORK": "http.network",
                                 "JEV.RATE_LIMITED": "http.provider_busy", "JEV.OVERLOADED": "http.provider_busy",
                                 "JEV.VALIDATION": "decision.api_validation"}.get(err.code, "sc_agent.error"),
                          "message": str(err), "recovery": err.action}
                if err.status:
                    detail["message"] += f" HTTP {err.status}"
                result = {"position": position, "error": detail}
            else:
                result = {"position": position, "response": returned.value}
            results.append(result)
            if on_result:
                on_result(result)
        return results


def sc_decidr(transport):
    return jj.Ok(ScDecidrStub(transport))


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


# The credential entry plan-anchor reads (randlee/plan-anchor@d104c2d, scripts/jev_judge.py.j2). judge-jev must read
# the same entry so one stored key serves both. With PLAN_ANCHOR_ROOT set to a plan-anchor checkout the constants are
# parsed from that source instead of these recorded values.
PLAN_ANCHOR_JEV_JUDGE = "plugins/sc-plan-anchor/install/templates/skills/plan-anchoring/scripts/jev_judge.py.j2"
PLAN_ANCHOR_CREDENTIAL_CONSTANTS = {"TYPESAFE_KEY_ENV": "TYPESAFE_API_KEY", "CREDENTIAL_SERVICE": "plan-anchor",
                                    "CREDENTIAL_ACCOUNT": "typesafe-api-key"}


def plan_anchor_credential_constants():
    root = os.environ.get("PLAN_ANCHOR_ROOT")
    if not root:
        return dict(PLAN_ANCHOR_CREDENTIAL_CONSTANTS), "recorded from plan-anchor@d104c2d"
    source = Path(root, PLAN_ANCHOR_JEV_JUDGE).read_text(encoding="utf-8")
    found = {}
    for name in PLAN_ANCHOR_CREDENTIAL_CONSTANTS:
        match = re.search(rf'^{name} = "([^"]*)"$', source, re.MULTILINE)
        if match is None:
            raise AssertionError(f"{name} not found in {root}/{PLAN_ANCHOR_JEV_JUDGE}")
        found[name] = match.group(1)
    return found, f"parsed from {root}/{PLAN_ANCHOR_JEV_JUDGE}"


class CredentialLookupTests(unittest.TestCase):
    def test_credentials_are_delegated_to_sc_decidr(self):
        source = (SKILL / "scripts" / "jev_judge.py").read_text(encoding="utf-8")
        self.assertIn('"sc-decidr==0.1.0"', source)
        self.assertFalse(hasattr(jj, "credential_store_api_key"))
        self.assertFalse(hasattr(jj, "resolved_api_key"))


class DecideTests(unittest.TestCase):
    def decide(self, answers, roles=PLAN_ROLES, t=0.6):
        return jj.decide(answers, roles, t)

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

    def test_noul_fallback(self):
        self.assertEqual(jj.answer_choice({"type": "noul", "noul": 0.8}), ("yes", 0.6000000000000001))
        self.assertEqual(jj.answer_choice({"type": "noul", "probability": 0.2}), ("no", 0.6))
        self.assertEqual(jj.answer_choice({"noul": 0.5}), ("yes", 0.0))
        answers = plan_answers()
        answers["contradicted"] = {"type": "noul", "noul": 0.9}
        self.assertEqual(self.decide(answers)[0], "contradicted")
        self.assertIsNone(jj.answer_problem({"type": "noul", "noul": 0.3}, {"criteria": {}}))
        self.assertIsNotNone(jj.answer_problem({"type": "noul"}, {"criteria": {}}))


class ResponseValidationTests(unittest.TestCase):
    question = {"type": "choice", "criteria": {"yes": "", "no": "", "unclear": ""}}

    def test_good_answer_passes_and_rounding_is_tolerated(self):
        self.assertIsNone(jj.answer_problem(answer("yes"), self.question))
        good = answer("yes")
        good["probabilities"] = {"yes": 0.94, "no": 0.05, "unclear": 0.0}
        self.assertIsNone(jj.answer_problem(good, self.question))

    def test_problems_named(self):
        bad = answer("yes")
        bad["probabilities"]["yes"] = 0.5
        self.assertRegex(jj.answer_problem(bad, self.question), "sum to")
        self.assertRegex(jj.answer_problem(answer("maybe"), self.question), "not one of")
        self.assertRegex(jj.answer_problem({"type": "choice", "choice": "yes", "confidence": "0.9", "probabilities": {}}, self.question), "confidence")
        self.assertRegex(jj.answer_problem({"type": "choice", "choice": "yes", "confidence": True, "probabilities": {}}, self.question), "confidence")
        extra = answer("yes")
        extra["probabilities"]["other"] = 0.0
        self.assertRegex(jj.answer_problem(extra, self.question), "keys differ")
        self.assertRegex(jj.answer_problem({"type": "score", "choice": "yes"}, self.question), "not choice or noul")
        self.assertRegex(jj.answer_problem("yes", self.question), "not an object")

    def test_validate_response_requires_exact_answer_ids(self):
        questions = {"relevant": self.question, "addressed": self.question, "contradicted": self.question}
        error = failure(jj.validate_response({"answers": {"relevant": answer("yes")}}, questions))
        self.assertEqual(error.code, "JEV.RESPONSE_INVALID")
        self.assertTrue(error.recoverable)
        extra = dict(plan_answers(), bonus=answer("yes"))
        failure(jj.validate_response({"answers": extra}, questions))
        failure(jj.validate_response({"answers": []}, questions))
        failure(jj.validate_response(["not", "a", "dict"], questions))
        self.assertIs(ok(jj.validate_response({"model": "x", "answers": plan_answers()}, questions))["answers"]["relevant"]["choice"], "yes")


class ScDecidrErrorTests(unittest.TestCase):
    def test_typed_causes_map_to_consumer_errors_without_retrying(self):
        cases = [
            ({"id": "http.provider_busy", "status": 429, "message": "busy"}, "JEV.RATE_LIMITED"),
            ({"id": "http.network", "message": "offline"}, "JEV.NETWORK"),
            ({"id": "decision.api_validation", "message": "bad request"}, "JEV.VALIDATION"),
            ({"id": "secrets.key_missing", "message": "missing"}, "AUTH.CREDENTIALS"),
        ]
        for detail, expected in cases:
            with self.subTest(id=detail["id"]):
                error = jj.sc_agent_error(detail)
                self.assertEqual(error.code, expected)
                self.assertFalse(error.recoverable)

    def test_cause_chain_is_preserved(self):
        detail = {"id": "http.network", "message": "failed", "cause": {"id": "io.error", "message": "reset"}}
        line = {"request_id": "r", "run_id": "0000000000000000", "item_id": "i", "anchor_id": None,
                "candidate_id": "c", "repeat": 1, "request_sha256": "0" * 64, "questions_sha256": "0" * 64,
                "request": {}, "roles": {}, "kind": "directive", "dry_run": False, "ok": False,
                "raw_response": None, "answers": None, "model_answered": None, "threshold": 0.6,
                "verdict": None, "min_confidence": None, "leaning": None, "retry_count": 0,
                "attempts": [], "error": {"code": "JEV.NETWORK", "message": "failed", "recoverable": False, "detail": detail}}
        self.assertEqual(line["error"]["detail"]["cause"]["id"], "io.error")


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
            with env(TYPESAFE_API_KEY="ts-secret-123456"), consented(), mock.patch.object(jj, "sc_agent_module", side_effect=lambda: sc_decidr(Transport())):
                code, out = run_cli(["batch", "--input", src, "--run-dir", str(Path(d) / "runs"), "--run-name", "r1"])
            log = json.dumps(read_log(Path(d) / "runs"), ensure_ascii=False)
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
            code, out = run_cli(["batch", "--input", missing, "--run-dir", str(Path(d) / "runs"), "--dry-run"])
            self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MISSING"))
            src = write(d, "in.jsonl", jsonl([request_line()]))
            code, out = run_cli(["batch", "--input", src, "--run-dir", str(Path(d) / "runs"), "--answers-file", missing])
            self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MISSING"))
            self.assertFalse((Path(d) / "runs").exists())

    def test_missing_sc_observability_is_a_typed_dependency_error(self):
        with tempfile.TemporaryDirectory() as d:
            src = write(d, "in.jsonl", jsonl([request_line()]))
            with mock.patch.dict(sys.modules, {"sc_observability": None}):
                code, out = run_cli(["batch", "--input", src, "--run-dir", str(Path(d) / "runs"), "--dry-run"])
        self.assertEqual((code, out["error"]["code"]), (2, "DEPENDENCY.SC_OBSERVABILITY"))
        self.assertIn("uv run --script", out["error"]["suggested_action"])

    def test_unexpected_exceptions_become_script_internal(self):
        with mock.patch.object(jj, "cmd_batch", side_effect=RuntimeError("boom")):
            code, out = run_cli(["batch", "--input", "x"])
        self.assertEqual((code, out["error"]["code"], out["error"]["message"]), (2, "SCRIPT.INTERNAL", "RuntimeError: boom"))
        with mock.patch.object(jj, "cmd_batch", side_effect=KeyboardInterrupt):
            code, out = run_cli(["batch", "--input", "x"])
        self.assertEqual((code, out["canceled"]), (130, True))

    def test_numeric_flags_are_checked(self):
        for flag, value in (("--threshold", "high"), ("--max-workers", "2.5"), ("--repeat", "lots"),
                            ("--max-request-bytes", "big"), ("--timeout", "soon")):
            with env():
                code, out = run_cli(["batch", "--input", "x", "--dry-run", flag, value])
            self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), flag)
            self.assertIn(f"argument {flag}: invalid", out["error"]["message"])
        self.assertEqual((jj.DEFAULT_MODEL, jj.DEFAULT_THRESHOLD, jj.DEFAULT_MAX_REQUEST_BYTES, jj.DEFAULT_MAX_REQUEST_BYTES_DEV),
                         ("jev-latest", 0.6, 24000, 64000))
        self.assertEqual((jj.BATCH_MAX_WORKERS, jj.MAX_RESPONSE_BYTES), (4, 1048576))
        self.assertFalse(hasattr(jj, "JEV_URL"))

    def test_out_of_range_values_are_validation_input(self):
        with tempfile.TemporaryDirectory() as d:
            src = write(d, "in.jsonl", jsonl([request_line()]))
            for flag, value in (("--threshold", "1.5"), ("--max-workers", "0"), ("--repeat", "0"), ("--request-prefix", "a b")):
                code, out = run_cli(["batch", "--input", src, "--run-dir", str(Path(d) / "runs"), "--dry-run", flag, value])
                self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), flag)
            code, out = run_cli(["batch", "--input", src, "--run-dir", str(Path(d) / "runs"), "--dry-run", "--run-name", "bad name"])
            self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"))
            self.assertFalse((Path(d) / "runs").exists())

    def test_request_over_the_cap_is_refused_before_any_call(self):
        with tempfile.TemporaryDirectory() as d:
            src = write(d, "in.jsonl", jsonl([request_line(text="x" * 30000)]))
            t = Transport()
            with env(**LIVE_ENV), consented(), mock.patch.object(jj, "sc_agent_module", side_effect=lambda: sc_decidr(t)):
                code, out = run_cli(["batch", "--input", src, "--run-dir", str(Path(d) / "runs")])
                self.assertEqual((code, out["error"]["code"]), (2, "JEV.CONTEXT_EXCEEDED"))
                self.assertIn("over --max-request-bytes 24000", out["error"]["message"])
            self.assertEqual(t.bodies, [])
            self.assertFalse((Path(d) / "runs").exists())
            # the dev gate's default cap is 64000 bytes: the same item fits there
            dev = write(d, "dev.jsonl", jsonl([request_line(text="x" * 30000, questions=ok(jj.load_question_set("dev")).questions)]))
            code, out = run_cli(["batch", "--input", dev, "--run-dir", str(Path(d) / "runs"), "--gate", "dev", "--dry-run"])
            self.assertEqual((code, out["dry_run"]), (0, True))

    def test_exit_codes(self):
        # A command that ran exits 0; only a failure to run is nonzero, and never 1.
        self.assertFalse(hasattr(jj, "exit_code_for"))
        with tempfile.TemporaryDirectory() as d:
            src = write(d, "in.jsonl", jsonl([request_line()]))
            code, out = run_cli(["batch", "--input", src, "--run-dir", str(Path(d) / "runs"), "--dry-run"])
            self.assertEqual((code, out["dry_run"], out["ok"]), (0, True, False))
            code, out = run_cli(["batch", "--input", str(Path(d) / "missing.jsonl"), "--run-dir", str(Path(d) / "runs")])
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
        self.assertEqual(sorted(sub.choices), ["batch", "compare-definition", "doctor", "quality", "validate"])


if __name__ == "__main__":
    unittest.main()
