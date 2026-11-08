"""Every field of a quality tree replaced by each value of a fixed list of wrong values, or deleted: `quality` never
crashes (no SCRIPT.INTERNAL) and a tree it refuses is refused before any request is sent, in a dry run and in a live run
alike. The mutations are enumerated, not random, so each run checks the same inputs."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import test_quality as tq
from test_jev_judge import answer, env, run_cli, write

jj = tq.jj
WRONG = [None, 0, True, "", "x", [], [1], ["x", 1], {}, {"x": 1}, [{"x": 1}], "wave-1", "missing"]
DELETED = object()


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
            for path in field_paths(base):
                if not path:
                    continue
                for value in [*WRONG, DELETED]:
                    tree = mutated(base, path, value)
                    tree_file = write(d, "tree.json", tree)
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

    def test_req_tree(self):
        self.sweep(json.loads((tq.QUESTIONS / "quality-req.json").read_text(encoding="utf-8")), "--req", "REQ-T-0001")

    def test_two_wave_tree(self):
        self.sweep(two_wave_tree(), "--adr", "ADR-T-0001")


if __name__ == "__main__":
    unittest.main()
