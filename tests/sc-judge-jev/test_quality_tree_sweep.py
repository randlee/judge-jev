"""Every field of a quality tree replaced by each value of a fixed list of wrong values, deleted, or given an extra key;
the Raptor index and the answers file mutated the same way; and raw JSON text no value can express (NaN, a 5000-digit
integer, deep nesting, a lone surrogate): `quality` never crashes (no SCRIPT.INTERNAL, always one JSON object on a real
UTF-8 stdout) and refuses before any request is sent, in a dry run and in a live run alike. The mutations are enumerated,
not random, so each run checks the same inputs."""
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import test_quality as tq
from test_jev_judge import answer, env, run_cli, write

jj = tq.jj
WRONG = [None, 0, True, "", "x", [], [1], ["x", 1], {}, {"x": 1}, [{"x": 1}], "wave-1", "missing", float("nan"), "\ud800"]
DELETED = object()
EXTRA_KEYS = ["next", "verdict_rules", "questions", "per", "goto", "x"]
RAW = {"big int": "9" * 5000, "deep": "[" * 50000 + "]" * 50000, "Infinity": "Infinity"}


def two_wave_tree():
    """The shipped ADR wave 1 branching to a second wave, so next/goto, cycles and later-wave checks are swept too."""
    adr = json.loads((tq.QUESTIONS / "quality-adr.json").read_text(encoding="utf-8"))
    return {"schema": adr["schema"], "id": "two-wave", "kind": "adr", "start": "wave-1", "nodes": {
        "wave-1": {"questions": adr["nodes"]["wave-1"]["questions"],
                   "next": [{"when": {"context": "missing"}, "goto": "fail"}, {"goto": "wave-2"}]},
        "wave-2": {"questions": {"why": {"type": "choice", "instructions": "Why?", "criteria": {"a": "A.", "b": "B."}}},
                   "verdict_rules": [{"any": {"why": "b"}, "verdict": "no"}, {"verdict": "yes"}]},
        "fail": {"verdict": "no"}}}


def field_paths(value, path=()):
    yield path
    children = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
    for key, child in children:
        yield from field_paths(child, path + (key,))


def mutated(tree, path, value):
    tree = copy.deepcopy(tree)
    parent = tree
    for key in path[:-1]:
        parent = parent[key]
    if value is DELETED:
        del parent[path[-1]]
    else:
        parent[path[-1]] = value
    return tree


def first_option_answers(tree, record_id):
    """An answer (the first option) for every question the mutated tree still shapes as a choice question."""
    out = {}
    nodes = tree.get("nodes") if isinstance(tree, dict) else None
    for node_id, node in (nodes.items() if isinstance(nodes, dict) else ()):
        questions = node.get("questions") if isinstance(node, dict) else None
        if not isinstance(questions, dict):
            continue
        wave = {}
        for qid, q in questions.items():
            criteria = q.get("criteria") if isinstance(q, dict) else None
            options = list(criteria) if isinstance(criteria, dict) and len(criteria) >= 2 else ["yes", "no"]
            wave[qid] = answer(options[0], options=options)
        out[f"{record_id}/{node_id}"] = wave
        for index in range(1, 4):  # a per-statement wave's items are <record>.s<index>
            out[f"{record_id}.s{index}/{node_id}"] = wave
    return out


class TreeSweep(unittest.TestCase):
    def sweep(self, base, flag, record_id):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            index = write(d, "index.json", tq.INDEX)
            cases = [(path, value, mutated(base, path, value)) for path in field_paths(base) if path for value in [*WRONG, DELETED]]
            for path in field_paths(base):  # an extra key on every object: a leaf with next, a rule with questions, ...
                parent = base
                for key in path:
                    parent = parent[key]
                if isinstance(parent, dict):
                    cases += [(path + (key,), value, mutated(base, path + (key,), value)) for key in EXTRA_KEYS
                              if key not in parent for value in ([[{"goto": "wave-1"}], 5] if key == "next" else WRONG[:6])]
            for path, value, tree in cases:
                tree_file = write(d, "tree.json", tree)
                if True:
                    answers = write(d, "answers.json", first_option_answers(tree, record_id) or {"*": {}})
                    outcomes = []
                    for mode in (["--dry-run"], ["--answers-file", answers]):
                        sent = []
                        real = jj.pump_batch

                        def counting(lines, *args, **kwargs):
                            sent.extend(lines)
                            return real(lines, *args, **kwargs)

                        with env(), mock.patch.object(jj, "call_jev", tq.never_called), \
                                mock.patch.object(jj, "pump_batch", counting):
                            code, out = run_cli(["quality", flag, record_id, "--index", index, "--questions", tree_file,
                                                 "--run-dir", str(d / "logs"), "--run-name", "sweep", *mode])
                        where = f"{path} = {'<deleted>' if value is DELETED else repr(value)} ({mode[0]})"
                        self.assertIsInstance(out, dict, where)
                        error = out.get("error") or {}
                        self.assertNotEqual(error.get("code"), "SCRIPT.INTERNAL", f"{where}: {error}")
                        if error and mode[0] != "--dry-run":
                            self.assertFalse(sent, f"{where}: refused after {len(sent)} request(s) were sent: {error}")
                        outcomes.append(error.get("code"))
                    self.assertEqual(outcomes[0], outcomes[1], f"{path} = {value!r}: dry run and live run disagree")

    def run_quality(self, d, argv, answer_side=False):
        """``answer_side``: the mutation is in Jev's answers (the answers file stands in for the response), so it can only
        be refused after the request; the check is then only that nothing crashes."""
        sent = []
        real = jj.pump_batch

        def counting(lines, *args, **kwargs):
            sent.extend(lines)
            return real(lines, *args, **kwargs)

        with env(), mock.patch.object(jj, "call_jev", tq.never_called), mock.patch.object(jj, "pump_batch", counting):
            code, out = run_cli([*argv, "--run-dir", str(d / "logs"), "--run-name", "sweep"])
        self.assertIsInstance(out, dict, argv)
        error = out.get("error") or {}
        self.assertNotEqual(error.get("code"), "SCRIPT.INTERNAL", f"{argv}: {error}")
        if error and "--dry-run" not in argv and not answer_side:
            self.assertFalse(sent, f"{argv}: refused after {len(sent)} request(s) were sent: {error}")
        return error.get("code")

    def test_index_and_answers_mutations(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            answers = {"ADR-T-0001/wave-1": tq.tree_answers("quality-adr.json")}
            for path in field_paths(tq.INDEX):
                for value in ([*WRONG, DELETED] if path else []):
                    index = write(d, "index.json", mutated(tq.INDEX, path, value))
                    for flag, rid in (("--req", "REQ-T-0001"), ("--adr", "ADR-T-0001")):
                        self.run_quality(d, ["quality", flag, rid, "--index", index, "--dry-run"])
            index = write(d, "index.json", tq.INDEX)
            for path in field_paths(answers):
                for value in ([*WRONG, DELETED] if path else []):
                    afile = write(d, "answers.json", mutated(answers, path, value))
                    self.run_quality(d, ["quality", "--adr", "ADR-T-0001", "--index", index, "--answers-file", afile], answer_side=True)

    def test_raw_json_no_value_can_express(self):
        """NaN/Infinity, oversized integers, deep nesting and a lone surrogate escape, in the tree, index and answers."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            index = write(d, "index.json", tq.INDEX)
            answers = write(d, "answers.json", {"ADR-T-0001/wave-1": tq.tree_answers("quality-adr.json")})
            tree_text = (tq.QUESTIONS / "quality-adr.json").read_text(encoding="utf-8")
            index_text = json.dumps(tq.INDEX)
            for name, raw in [*RAW.items(), ("lone surrogate", '"\\ud800"')]:
                bad_tree = write(d, "tree.json", tree_text.replace('"approved": false', f'"approved": {raw}', 1))
                bad_index = write(d, "bad-index.json", index_text.replace('"Because."', raw, 1))
                bad_answers = write(d, "bad-answers.json", '{"ADR-T-0001/wave-1": ' + raw + "}")
                for argv in (["--questions", bad_tree, "--index", index, "--dry-run"],
                             ["--questions", bad_tree, "--index", index, "--answers-file", answers],
                             ["--index", bad_index, "--dry-run"],
                             ["--index", index, "--answers-file", bad_answers]):
                    with self.subTest(name=name, argv=argv[0]):
                        self.assertEqual(self.run_quality(d, ["quality", "--adr", "ADR-T-0001", *argv]), "INPUT.MALFORMED")

    def test_unwritable_run_dir_is_refused_before_any_call(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            index = write(d, "index.json", tq.INDEX)
            answers = write(d, "answers.json", {"ADR-T-0001/wave-1": tq.tree_answers("quality-adr.json")})
            not_a_dir = write(d, "file", "x")
            with env(), mock.patch.object(jj, "call_jev", tq.never_called), \
                    mock.patch.object(jj, "pump_batch", side_effect=AssertionError("sent before the log was checked")):
                code, out = run_cli(["quality", "--adr", "ADR-T-0001", "--index", index, "--answers-file", answers,
                                     "--run-dir", not_a_dir])
            self.assertEqual((code, out["error"]["code"]), (2, "LOG.WRITE"), out)

    def test_stdout_is_json_on_a_real_utf8_stream(self):
        """emit never fails on a lone surrogate (here, from a non-UTF-8 argument) when stdout is a strict UTF-8 stream."""
        stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        with mock.patch.object(sys, "stdout", stream):
            code = jj.main(["quality", "--adr", "ADR-\udcff", "--index", "x", "--dry-run"])
            stream.flush()
            out = json.loads(stream.buffer.getvalue().decode("utf-8"))
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), out)
        stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        with mock.patch.object(sys, "stdout", stream):
            jj.emit({"success": False, "error": {"message": "\ud800"}})
            stream.flush()
        self.assertEqual(json.loads(stream.buffer.getvalue().decode("utf-8"))["error"]["message"], "\ud800")

    def test_req_tree(self):
        self.sweep(json.loads((tq.QUESTIONS / "quality-req.json").read_text(encoding="utf-8")), "--req", "REQ-T-0001")

    def test_two_wave_tree(self):
        self.sweep(two_wave_tree(), "--adr", "ADR-T-0001")


if __name__ == "__main__":
    unittest.main()
