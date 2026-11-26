"""No input crashes the script (REQ-JEV-0210, REQ-JEV-0211): arbitrarily deep nesting never reaches a recursion limit,
and the answers-file envelope is
checked before any request by `validate --answers` and by every command that reads --answers-file alike.
Every case is an enumerated input; nothing here sleeps or times."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
import os
from pathlib import Path
from unittest import mock

import test_quality as tq
from test_jev_judge import consented, env, jsonl, plan_answers, request_line, run_cli, write
from test_validate import validate

jj = tq.jj
ASTRAL = "\U0001F600"
DEPTHS = (40, 600, 900, 5000)  # beyond the logger's 32, beyond a recursion limit of 1000 in two frames per level, far beyond


def nested(depth, leaf="leaf", kind=list):
    value = leaf
    for _ in range(depth):
        value = [value] if kind is list else {"k": value} if kind is dict else (value,)
    return value


def depth_of(value):
    depth = 0
    while isinstance(value, (list, dict, tuple)):
        value = next(iter(value.values())) if isinstance(value, dict) else value[0]
        depth += 1
    return depth, value


class RedactionIsIterative(unittest.TestCase):
    def test_redact_sensitive_walks_any_depth_and_keeps_the_shape(self):
        key = "sk-secret-value"
        for kind in (list, dict, tuple):
            for depth in DEPTHS + (50000,):
                with self.subTest(kind=kind.__name__, depth=depth), mock.patch.dict("os.environ", {"TYPESAFE_API_KEY": key}):
                    out = jj.redact_sensitive(nested(depth, f"has {key} in it", kind))
                    self.assertIs(type(out), kind)
                    self.assertEqual(depth_of(out), (depth, "has <redacted> in it"))

    def test_redact_sensitive_keeps_order_types_and_scalars(self):
        value = {"b": (1, [2, {"c": "Bearer abc.def"}]), "a": None, "z": 1.5, "t": True}
        out = jj.redact_sensitive(value)
        self.assertEqual(list(out), ["b", "a", "z", "t"])
        self.assertEqual(out, {"b": (1, [2, {"c": "Bearer <redacted>"}]), "a": None, "z": 1.5, "t": True})
        self.assertIsInstance(out["b"], tuple)

    def test_bound_depth_keeps_the_limit_and_marks_what_is_deeper(self):
        limit = jj.EMIT_MAX_DEPTH
        for depth, marked in ((limit - 1, False), (limit, False), (limit + 1, True), (limit + 600, True)):
            with self.subTest(depth=depth):
                out = jj.bound_depth(nested(depth))
                reached, leaf = depth_of(out)
                if marked:
                    self.assertEqual((reached, leaf), (limit, jj.EMIT_TRUNCATED))
                else:
                    self.assertEqual((reached, leaf), (depth, "leaf"))

    def test_emit_prints_json_for_any_depth(self):
        for kind in (list, dict):
            for depth in DEPTHS + (50000,):
                with self.subTest(kind=kind.__name__, depth=depth):
                    buf = io.StringIO()
                    with contextlib.redirect_stdout(buf):
                        jj.emit({"success": False, "data": nested(depth, kind=kind), "error": {"code": "X"}})
                    out = json.loads(buf.getvalue())
                    self.assertEqual(out["error"], {"code": "X"})
                    self.assertLessEqual(depth_of(out["data"])[0], jj.EMIT_MAX_DEPTH)

    def test_a_judge_error_with_deep_data_serialises(self):
        error = jj.ClientError("PLAN.TOO_LARGE", "big")
        error.data = nested(5000)
        self.assertEqual(depth_of(error.to_json()["data"])[0], 5000)


class DeepInputIsATypedError(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        _log_environment = mock.patch.dict(os.environ, {"JUDGE_JEV_LOG_ROOT": str(self.d / "logs")})
        _log_environment.start()
        self.addCleanup(_log_environment.stop)

    def request_with(self, deep):
        line = request_line(questions={"q": {"type": "choice", "instructions": "i", "criteria": {"a": "A", "b": "B"}, "x": deep}})
        del line["anchor"]
        return write(self.d, "r.jsonl", jsonl([line]))



    def test_validate_requests_and_batch_dry_run_refuse_a_deep_request_before_any_call(self):
        # Past JSON_MAX_DEPTH the line is INPUT.MALFORMED at parse, on every Python.
        for depth, expected in ((600, "INPUT.MALFORMED"), (900, "INPUT.MALFORMED")):
            src = self.request_with(nested(depth))
            with self.subTest(command="validate", depth=depth):
                code, out = validate("--requests", src)
                self.assertEqual((code, out["error"]["code"]), (2, expected), out)
                self.assertIn("maximum container depth is 32" if expected == "VALIDATION.INPUT" else str(jj.JSON_MAX_DEPTH),
                              out["error"]["message"])
            with self.subTest(command="batch", depth=depth), env(), mock.patch.multiple(jj.decidr_client, call_result=tq.never_called, call_batch_results=tq.never_called):
                code, out = run_cli(["batch", "--input", src, "--dry-run"])
                self.assertEqual((code, out["error"]["code"]), (2, expected), out)

    def test_a_record_diagnostic_with_a_deep_field_still_prints_json(self):
        # 450 reaches emit with an issue nested past EMIT_MAX_DEPTH; 600 and 900 are past JSON_MAX_DEPTH, refused at parse.
        for depth, expected in ((300, "RECORD.DIAGNOSTICS"), (450, "RECORD.DIAGNOSTICS"), (600, "INPUT.MALFORMED"), (900, "INPUT.MALFORMED")):
            index = copy.deepcopy(tq.INDEX)
            index["diagnostics"]["issues"].append({"id": "ADR-T-0001", "rule": "X", "extra": nested(depth)})
            with self.subTest(depth=depth), env(), mock.patch.multiple(jj.decidr_client, call_result=tq.never_called, call_batch_results=tq.never_called):
                code, out = run_cli(["quality", "--adr", "ADR-T-0001", "--index", write(self.d, "i.json", index), "--dry-run"])
                self.assertIsInstance(out, dict, out)
                self.assertEqual((code, out["error"]["code"]), (2, expected), out)



    def test_a_deep_record_field_is_composed_or_typed_refusal(self):
        # judge-jev sets no request size limit (ANC-004): a deep-but-parseable field is composed; one too deep to parse is a typed refusal
        for depth, expected in ((300, 0), (900, 2)):
            index = copy.deepcopy(tq.INDEX)
            index["decisions"][0]["x"] = nested(depth)
            with self.subTest(depth=depth), env(), mock.patch.multiple(jj.decidr_client, call_result=tq.never_called, call_batch_results=tq.never_called):
                code, out = run_cli(["quality", "--adr", "ADR-T-0001", "--index", write(self.d, "i.json", index), "--dry-run"])
                self.assertIsInstance(out, dict, out)
                self.assertEqual(code, expected, out)
                if expected:
                    self.assertNotEqual(out["error"]["code"], "SCRIPT.INTERNAL")


def counting_pump(sent):
    real = jj.judge_batch

    def counting(lines, *args, **kwargs):
        sent.extend(lines)
        return real(lines, *args, **kwargs)
    return counting


class JsonDepthIsTheSameOnEveryPython(unittest.TestCase):
    """CI: Python 3.14's json parser accepts any depth where 3.11-3.13 raise RecursionError, so strict_loads states the
    limit itself; the refusal must not depend on the interpreter."""

    def test_the_depth_limit_is_inclusive_and_one_more_is_a_value_error(self):
        limit = jj.JSON_MAX_DEPTH
        self.assertEqual(jj.strict_loads("[" * limit + "]" * limit), jj.strict_loads("[" * limit + "]" * limit))
        for text in ("[" * (limit + 1) + "]" * (limit + 1), '{"a":' * (limit + 1) + "1" + "}" * (limit + 1)):
            with self.assertRaises(ValueError) as caught:
                jj.strict_loads(text)
            self.assertIn(str(limit), str(caught.exception))

    def test_a_deep_value_whatever_the_parser_does_is_value_error_or_recursion_error(self):
        with mock.patch.object(jj.json, "loads", return_value=[[[[[]]]]]), mock.patch.object(jj, "JSON_MAX_DEPTH", 3):
            with self.assertRaises(ValueError):
                jj.strict_loads("ignored")





class AnswersEnvelope(unittest.TestCase):
    """The answers file stands in for Jev's response. Its envelope is decided before any request, by one model, for
    `validate --answers`, `batch` and `quality` alike; an answer's body may be invalid on purpose and stays a post-send check."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        _log_environment = mock.patch.dict(os.environ, {"JUDGE_JEV_LOG_ROOT": str(self.d / "logs")})
        _log_environment.start()
        self.addCleanup(_log_environment.stop)
        self.good = tq.tree_answers("quality-adr.json")
        self.tree = json.loads((tq.QUESTIONS / "quality-adr.json").read_text(encoding="utf-8"))

    def with_context(self, **changes):
        answers = copy.deepcopy(self.good)
        answers["context"].update(changes)
        return {"ADR-T-0001/wave-1": answers}

    def quality(self, fixture):
        sent = []
        argv = ["quality", "--adr", "ADR-T-0001", "--index", write(self.d, "index.json", tq.INDEX), "--questions", write(self.d, "tree.json", self.tree), "--run-name", "p", "--answers-file", write(self.d, "a.json", fixture)]
        with env(), mock.patch.multiple(jj.decidr_client, call_result=tq.never_called, call_batch_results=tq.never_called), mock.patch.object(jj, "judge_batch", counting_pump(sent)):
            code, out = run_cli(argv)
        return code, out, len(sent)

    def batch(self, fixture):
        sent = []
        src = write(self.d, "r.jsonl", jsonl([request_line()]))
        with env(), mock.patch.multiple(jj.decidr_client, call_result=tq.never_called, call_batch_results=tq.never_called), mock.patch.object(jj, "judge_batch", counting_pump(sent)):
            code, out = run_cli(["batch", "--input", src, "--answers-file", write(self.d, "b.json", fixture)])
        return code, out, len(sent)

    ENVELOPE_REFUSED = {
        "error code is an int": {"*": {"__error__": 5}},
        "error code is null": {"*": {"__error__": None}},
        "error code is a list": {"*": {"__error__": ["X"]}},
        "error with another field": {"*": {"__error__": "X", "why": 1}},
        "error code is empty": {"*": {"__error__": ""}},
        "empty error code in a list": {"*": [{"__error__": "DECIDR.NETWORK"}, {"__error__": ""}]},
        "entry is a string": {"*": "x"},
        "entry is a number": {"*": 3},
        "entry is null": {"*": None},
        "list of strings": {"*": ["x"]},
        "list holding a list": {"*": [[]]},
        "empty list": {"*": []},
        "list with a bad error entry": {"*": [{"__error__": "DECIDR.NETWORK"}, {"__error__": 7}]},
    }
    ENVELOPE_ACCEPTED = {
        "error of one character": {"*": {"__error__": "J"}},
        "short error": {"*": {"__error__": "DECIDR.NETWORK"}},
        "empty answers object": {"*": {}},
        "list of errors": {"*": [{"__error__": "DECIDR.NETWORK"}, {"__error__": "DECIDR.OVERLOADED"}]},
    }

    def test_validate_quality_and_batch_refuse_the_same_envelopes_before_any_send(self):
        for name, fixture in self.ENVELOPE_REFUSED.items():
            with self.subTest(name):
                vcode, vout = validate("--answers", write(self.d, "v.json", fixture))
                qcode, qout, qsent = self.quality(fixture)
                bcode, bout, bsent = self.batch(fixture)
                self.assertEqual((vcode, vout["error"]["code"]), (2, "INPUT.MALFORMED"), vout)
                self.assertEqual((qcode, qout["error"]["code"], qsent), (2, "INPUT.MALFORMED", 0), qout)
                self.assertEqual((bcode, bout["error"]["code"], bsent), (2, "INPUT.MALFORMED", 0), bout)
                strip = lambda m: m.split(": ", 1)[1]  # the file path differs; the field path and rule do not
                self.assertEqual(strip(vout["error"]["message"]).split(": ", 1)[1], strip(qout["error"]["message"]).split(": ", 1)[1])

    def test_validate_and_the_commands_accept_the_same_envelopes(self):
        for name, fixture in self.ENVELOPE_ACCEPTED.items():
            with self.subTest(name):
                self.assertEqual(validate("--answers", write(self.d, "v.json", fixture))[0], 0)
                qout = self.quality(fixture)
                self.assertNotEqual(qout[1]["error"]["code"] if qout[0] else None, "INPUT.MALFORMED", qout[1])

    def test_a_top_level_that_is_not_an_object_is_refused_by_all(self):
        for name, raw in (("list", "[]"), ("string", '"x"'), ("null", "null"), ("number", "3")):
            with self.subTest(name):
                self.assertEqual(validate("--answers", write(self.d, "v.json", raw))[1]["error"]["code"], "INPUT.MALFORMED")
                code, out, sent = self.quality(raw)
                self.assertEqual((code, out["error"]["code"], sent), (2, "INPUT.MALFORMED", 0))

    def test_an_invalid_answer_body_passes_the_envelope_and_fails_after_the_send(self):
        bodies = {"choice is a list": self.with_context(choice=["x"]),
                  "wrong answer type": self.with_context(type="score"),
                  "choice is not an option": self.with_context(choice="nope"),
                  "confidence out of range": self.with_context(confidence=2)}
        for name, fixture in bodies.items():
            with self.subTest(name):
                self.assertEqual(validate("--answers", write(self.d, "v.json", fixture))[0], 0, name)
                code, out, sent = self.quality(fixture)
                self.assertEqual((code, out["error"]["code"], sent), (2, "DECIDR.RESPONSE_INVALID", 1), out)

    def test_a_noul_probability_above_one_passes_the_envelope_and_fails_after_the_send(self):
        for key, value in (("noul", 1.5), ("probability", 1.5), ("noul", 1.0000001)):
            with self.subTest(f"{key}={value}"):
                answers = copy.deepcopy(self.good)
                answers["context"] = {"type": "noul", key: value}
                fixture = {"ADR-T-0001/wave-1": answers}
                self.assertEqual(validate("--answers", write(self.d, "v.json", fixture))[0], 0)
                code, out, sent = self.quality(fixture)
                self.assertEqual((code, out["error"]["code"], sent), (2, "DECIDR.RESPONSE_INVALID", 1), out)
                self.assertIn("context", out["error"]["message"])

    def test_a_fixture_without_an_entry_for_a_request_is_fixture_missing_before_any_send(self):
        elsewhere = {"OTHER-0001/wave-1": self.good}  # no entry for ADR-T-0001/wave-1 and no '*'
        code, out, sent = self.quality(elsewhere)
        self.assertEqual((code, out["error"]["code"], sent), (2, "FIXTURE.MISSING", 0), out)
        self.assertIn("ADR-T-0001/wave-1/r1", out["error"]["message"])
        code, out, sent = self.batch({"other-item/cur": plan_answers()})
        self.assertEqual((code, out["error"]["code"], sent), (2, "FIXTURE.MISSING", 0), out)
        self.assertIn("ex-42/cur/r1", out["error"]["message"])

    def test_fixture_attempt_uses_the_shared_key_and_missing_helpers(self):
        job = jj.BatchJob("item", None, "candidate", 2, "request", {}, {"answer": {"type": "noul"}}, {}, "directive")
        keys = ("delegated/r2", "delegated", "candidate", "*")
        with mock.patch.object(jj.decidr_client, "_fixture_keys", return_value=keys) as get_keys:
            result = jj.decidr_client.fixture_attempt(job,
                {"delegated/r2": {"answer": {"type": "noul", "noul": 0.75}}}, 1)
        self.assertEqual(result["value"]["answers"]["answer"].noul, 0.75)
        get_keys.assert_called_once_with(job)
        missing = jj.ClientError("TEST.MISSING", "shared helper result")
        with mock.patch.object(jj.decidr_client, "_fixture_keys", return_value=keys) as get_keys, \
                mock.patch.object(jj.decidr_client, "_fixture_missing", return_value=missing) as get_missing:
            result = jj.decidr_client.fixture_attempt(job, {}, 1)
        self.assertFalse(result["ok"])
        self.assertIs(result["error"], missing)
        get_keys.assert_called_once_with(job)
        get_missing.assert_called_once_with(keys)

    def test_batch_checks_every_line_of_the_stream_before_sending_the_first(self):
        sent = []
        lines = [request_line("covered"), request_line("uncovered")]
        src = write(self.d, "r2.jsonl", jsonl(lines))
        fixture = write(self.d, "b2.json", {"covered/cur": plan_answers()})
        with env(), mock.patch.multiple(jj.decidr_client, call_result=tq.never_called, call_batch_results=tq.never_called), mock.patch.object(jj, "judge_batch", counting_pump(sent)):
            code, out = run_cli(["batch", "--input", src, "--answers-file", fixture])
        self.assertEqual((code, out["error"]["code"], len(sent)), (2, "FIXTURE.MISSING", 0), out)
        self.assertFalse((self.d / "blogs2").exists())

    def test_a_star_entry_or_any_key_form_covers_the_request(self):
        for key in ("ex-42/cur/r1", "ex-42/cur", "cur", "*"):
            with self.subTest(key):
                code, out, sent = self.batch({key: plan_answers()})
                self.assertEqual((code, sent), (0, 1), out)

    def test_a_request_over_64000_bytes_is_sent_whole(self):
        """No --answers-file: the live path runs to sc_agent.send_batch (stubbed), which must receive the whole item text."""
        import sc_agent
        text = "x" * 70000
        captured = []

        def send_batch(requests, **kwargs):
            captured.extend(json.loads(request) for request in requests)
            lines = [{"ok": True, "value": {"answers": plan_answers(), "session_id": f"s{i}"}} for i in range(len(requests))]
            for index, line in enumerate(lines):
                kwargs["on_result"](index, line)
            return {"ok": True, "value": [{"index": i, "result": line} for i, line in enumerate(lines)]}

        src = write(self.d, "big.jsonl", jsonl([request_line(text=text)]))
        with env(), consented(), mock.patch.object(sc_agent, "send_batch", send_batch):
            code, out = run_cli(["batch", "--input", src])
        self.assertEqual(code, 0, out)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["state"]["item"]["text"], text)

    def test_an_error_fails_the_wave_with_its_code_and_logs_cleanly(self):
        code_text = "J"
        code, out, sent = self.quality({"*": {"__error__": code_text}})
        self.assertEqual((code, out["error"]["code"], sent), (2, code_text, 1), out)
        events = tq.read_log(self.d / "logs")
        self.assertEqual([event["action"] for event in events], ["request", "answer", "result"])
        self.assertEqual((events[-1]["fields"]["ok"], events[-1]["fields"]["error"]["code"]), (False, code_text))


if __name__ == "__main__":
    unittest.main()
