"""The rule that decides a verdict is recorded with its rank, and the record by its Raptor IRI, in the log and in the triples.

Jev is never called: every answer comes from an answers fixture (``--answers-file``). The wave and verdict events carry
``rule_rank`` (the 1-based rank of the rule that fired, the tree's ``jj:rank``); every event carries ``record_iri``; the run
triples rebuilt from the log (``check_projection`` compares them with the in-memory ones) carry that IRI as ``jj:record`` and the fired rule's ``jj:rank``.
"""
import unittest

import pyoxigraph as ox

from jev_support import read_log
from test_graph_runs import REPOSITORY, RunCase, jn  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
