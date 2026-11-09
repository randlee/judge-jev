"""The rule that decides a verdict is recorded with its rank, and the record by its Raptor IRI, in the log and in the triples.

Jev is never called: every answer comes from an answers fixture (``--answers-file``). The wave and verdict events carry
``rule_rank`` (the 1-based rank of the rule that fired, the tree's ``jj:rank``); every event carries ``record_iri``; the run
triples rebuilt from the log (``check_projection`` compares them with the in-memory ones) carry that IRI as ``jj:record`` and the fired rule's ``jj:rank``.
"""
import unittest
from unittest import mock

import pyoxigraph as ox

from jev_support import read_log
import jev_graph  # noqa: E402
import jev_judge as jj  # noqa: E402
import jev_runs  # noqa: E402
from test_graph_runs import REPOSITORY, RunCase, jn  # noqa: E402
from test_graph_tree import ADR_TTL, BRANCH_TTL  # noqa: E402
from test_jev_judge import answer  # noqa: E402
from test_quality import tree_answers  # noqa: E402

RECORD_IRI = f"{REPOSITORY}#ADR-T-0001"
XSD_INTEGER = ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer")


class RuleRankAndRecordIri(RunCase):
    def run_case(self, **choices):
        answers = {"ADR-T-0001/wave-1": tree_answers("quality-adr.json", **choices)}
        run_iri, store, result = self.check_projection("adr", "--adr", "ADR-T-0001", answers)
        events = read_log(self.d / "logs")
        return run_iri, store, result, events

    def assert_recorded(self, rank, verdict):
        run_iri, store, result, events = self.run_case(**({} if rank == 2 else {"consequences": "missing", "alternatives": "none"}))
        self.assertEqual(result["verdict"], verdict)
        wave_events = [e for e in events if e["action"] == "wave"]
        verdict_events = [e for e in events if e["action"] == "verdict"]
        self.assertEqual([e["fields"]["rule_rank"] for e in wave_events], [rank])
        self.assertEqual([e["fields"]["rule_rank"] for e in verdict_events], [rank])
        self.assertEqual(verdict_events[0]["fields"]["verdict"], verdict)
        for event in events:
            self.assertEqual(event["fields"]["record_iri"], RECORD_IRI, event["action"])
        run_node = ox.NamedNode(run_iri)
        self.assertEqual([q.object for q in store.quads_for_pattern(run_node, jn("record"), None)], [ox.NamedNode(RECORD_IRI)])
        (wave_run,) = [q.subject for q in store.quads_for_pattern(None, jn("inRun"), run_node)]
        (fired,) = [q.object for q in store.quads_for_pattern(wave_run, jn("fired"), None)]
        self.assertTrue(fired.value.endswith(f":rule-{rank}"), fired.value)
        self.assertEqual([q.object for q in store.quads_for_pattern(fired, jn("rank"), None)],
                         [ox.Literal(str(rank), datatype=XSD_INTEGER)])

    def test_a_passing_record_logs_the_default_rule_rank_and_its_iri(self):
        self.assert_recorded(2, "yes")

    def test_a_failing_record_logs_the_firing_rule_rank_and_its_iri(self):
        self.assert_recorded(1, "no")


class NonConsecutiveRanks(RunCase):
    """The SHACL shapes require rule ranks to be unique, not consecutive: with ranks 1 and 7, the second rule's rank is 7,
    not its position 2, in the log and in the run triples."""

    def run_ttl(self, ttl, flag, record_id, answers):
        path = self.d / "tree.ttl"
        path.write_bytes(ttl.encode("utf-8"))
        pumped, real = [], jj.pump_batch

        def spy(*args, **kwargs):
            got = real(*args, **kwargs)
            pumped.extend(got.value)
            return got

        with mock.patch.object(jj, "pump_batch", spy):
            code, out = self.quality(flag, record_id, "--questions", str(path), answers=answers)
        self.assertEqual(code, 0, out)
        (result,) = out["data"]["results"]
        tree = jev_graph.load_tree(str(path)).value
        run = {"name": "q1", "tree_sha256": result["tree"]["sha256"], "record_id": record_id, "repository": REPOSITORY}
        built = jev_runs.run_triples(tree, run, pumped, result)
        rebuilt = jev_runs.rebuild_from_log(self.d / "logs", "q1", tree, repository=REPOSITORY)
        self.assertIsInstance(rebuilt, jj.Ok, rebuilt)
        self.assertEqual(built, rebuilt.value)
        store = ox.Store()
        store.extend(list(tree.store) + built)
        return result, read_log(self.d / "logs"), store

    def assert_fired(self, store, rule_iri, rank):
        (fired,) = {q.object for q in store.quads_for_pattern(None, jn("fired"), None)}
        self.assertEqual(fired, ox.NamedNode(rule_iri))
        self.assertEqual([q.object for q in store.quads_for_pattern(fired, jn("rank"), None)],
                         [ox.Literal(str(rank), datatype=XSD_INTEGER)])

    def test_a_verdict_rule_ranked_7_logs_rank_7(self):
        ttl = ADR_TTL.replace('t:quality-adr:wave-1:rule-2 a jj:VerdictRule ;\n    jj:rank 2 ;',
                              't:quality-adr:wave-1:rule-2 a jj:VerdictRule ;\n    jj:rank 7 ;')
        self.assertNotEqual(ttl, ADR_TTL)
        answers = {"ADR-T-0001/wave-1": tree_answers("quality-adr.json")}
        result, events, store = self.run_ttl(ttl, "--adr", "ADR-T-0001", answers)
        self.assertEqual(result["verdict"], "yes")
        self.assertEqual([e["fields"]["rule_rank"] for e in events if e["action"] in ("wave", "verdict")], [7, 7])
        self.assert_fired(store, "urn:judge-jev:tree:quality-adr:wave-1:rule-2", 7)

    def test_a_branch_rule_ranked_7_logs_rank_7(self):
        ttl = BRANCH_TTL.replace("t:b:wave-1:r2 a jj:BranchRule ; jj:rank 2", "t:b:wave-1:r2 a jj:BranchRule ; jj:rank 7")
        self.assertNotEqual(ttl, BRANCH_TTL)
        answers = {"*": {"size": answer("small", p=0.9, options=["small", "big", "huge"])}}
        result, events, store = self.run_ttl(ttl, "--req", "REQ-T-0001", answers)
        self.assertEqual((result["verdict"], result["path"]), ("yes", ["wave-1", "done"]))
        self.assertEqual([e["fields"]["rule_rank"] for e in events if e["action"] == "wave"], [7])
        self.assert_fired(store, "urn:judge-jev:tree:b:wave-1:r2", 7)


if __name__ == "__main__":
    unittest.main()
