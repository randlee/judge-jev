"""A quality run as triples (ADR-JEV-0006 run vocabulary) and the Transport / GraphStore ports (ADR-JEV-0007).

Jev is never called: ``call_jev`` is replaced with a stub that fails the test and every answer comes from an answers
fixture. The tree graph comes from the shipped JSON tree through ``tree_fixture`` (its triples minted with
``jev_runs.JsonIris``); once ``jev_graph.load_tree`` and the shipped TTL tree exist it loads that instead.
"""
import json
import unittest
from pathlib import Path
from unittest import mock

import pyoxigraph as ox

from jev_support import SKILL, read_log
import jev_graph  # noqa: E402
import jev_judge as jj  # noqa: E402
import jev_ports  # noqa: E402
import jev_runs  # noqa: E402

from test_jev_judge import answer, run_cli, write  # noqa: E402
from test_quality import INDEX, QualityCase, never_called, tree_answers  # noqa: E402
from test_graph_tree import ADR_JSON, ADR_TTL, BRANCH_TTL, write  # noqa: E402

QUESTIONS = SKILL / "assets" / "questions"
REPOSITORY = INDEX["metadata"]["repository"]
RDF_TYPE = ox.NamedNode(jev_runs.RDF_TYPE)


def jn(name):
    return ox.NamedNode(jev_runs.JJ + name)


def tree_json(kind):
    return json.loads((QUESTIONS / f"quality-{kind}.json").read_text(encoding="utf-8"))


def json_tree_quads(tree):
    """The tree's question, option and rule triples (what a loaded tree graph holds), minted with JsonIris."""
    iris, out = jev_runs.JsonIris(tree), []

    def add(s, p, o):
        out.append(ox.Quad(ox.NamedNode(s), p, o, ox.DefaultGraph()))

    for node_id, node in tree["nodes"].items():
        for qid, question in node.get("questions", {}).items():
            add(iris.question(qid), RDF_TYPE, jn("Question"))
            add(iris.question(qid), jn("instructions"), ox.Literal(question["instructions"]))
            for label, criterion in question["criteria"].items():
                add(iris.question(qid), jn("option"), ox.NamedNode(iris.option(qid, label)))
                add(iris.option(qid, label), RDF_TYPE, jn("Option"))
                add(iris.option(qid, label), jn("label"), ox.Literal(label))
                add(iris.option(qid, label), jn("criterion"), ox.Literal(criterion))
        for rank, rule in enumerate(node.get("next") or node.get("verdict_rules") or [], 1):
            add(iris.rule(node_id, rank), RDF_TYPE, jn("BranchRule" if "next" in node else "VerdictRule"))
            add(iris.rule(node_id, rank), jn("rank"), ox.Literal(str(rank), datatype=ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer")))
    return out


def tree_fixture(kind):
    """(tree argument for jev_runs, quads of the tree graph): load_tree's TreeGraph when jev_graph has it, else the JSON tree."""
    ttl = QUESTIONS / f"quality-{kind}.ttl"
    try:
        import jev_graph
        load = jev_graph.load_tree
    except (ImportError, AttributeError):
        load = None
    if load is None or not ttl.is_file():
        return tree_json(kind), json_tree_quads(tree_json(kind))
    loaded = load(str(ttl))
    if isinstance(loaded, jj.Err):
        raise AssertionError(loaded.error)
    return loaded.value, list(loaded.value.store)


class RunCase(QualityCase):
    def run_quality(self, flag, record_id, answers):
        """Run ``quality`` once; (the results[] entry, the result lines pump_batch returned, the run dict)."""
        pumped = []
        real = jj.pump_batch

        def spy(*args, **kwargs):
            got = real(*args, **kwargs)
            pumped.extend(got.value)
            return got

        with mock.patch.object(jj, "pump_batch", spy):
            code, out = self.quality(flag, record_id, answers=answers)
        self.assertEqual(code, 0, out)
        (result,) = out["data"]["results"]
        run = {"name": "q1", "tree_sha256": result["tree"]["sha256"], "record_id": record_id, "repository": REPOSITORY}
        return result, pumped, run

    def check_projection(self, kind, flag, record_id, answers):
        """run_triples from the in-memory results equals the triples rebuilt from the log alone; returns (run IRI, store)."""
        result, lines, run = self.run_quality(flag, record_id, answers)
        tree, tree_quads = tree_fixture(kind)
        built = jev_runs.run_triples(tree, run, lines, result)
        rebuilt = jev_runs.rebuild_from_log(self.d / "logs", "q1", tree, repository=REPOSITORY)
        self.assertIsInstance(rebuilt, jj.Ok, rebuilt)
        self.assertTrue(built)
        self.assertEqual(built, rebuilt.value)
        store = ox.Store()
        store.extend(tree_quads + built)
        return jev_runs.run_iri(run), store, result

    def trace(self, store, run_iri, record_id):
        query = jev_runs.trace_query(run_iri, f"{REPOSITORY}#{record_id}")
        return sorted((str(r["verdict"].value), r["rule"].value, r["question"].value, r["optionLabel"].value, r["criterion"].value)
                      for r in store.query(query))


class AdrRun(RunCase):
    def adr_rows(self, **choices):
        questions = tree_json("adr")["nodes"]["wave-1"]["questions"]
        answers = {"ADR-T-0001/wave-1": tree_answers("quality-adr.json", **choices)}
        run_iri, store, result = self.check_projection("adr", "--adr", "ADR-T-0001", answers)
        rows = self.trace(store, run_iri, "ADR-T-0001")
        return questions, result, rows

    def test_a_passing_adr_traces_yes_through_the_default_rule_to_each_option(self):
        questions, result, rows = self.adr_rows()
        self.assertEqual(result["verdict"], "yes")
        rule = "urn:judge-jev:tree:quality-adr:wave-1:rule-2"
        want = []
        for qid, q in questions.items():
            label = next(iter(q["criteria"]))
            want.append(("yes", rule, f"urn:judge-jev:question:adr.{qid}", label, q["criteria"][label]))
        self.assertEqual(rows, sorted(want))

    def test_a_failing_adr_traces_no_through_rule_1_to_the_failing_option_and_its_fix_hint(self):
        questions, result, rows = self.adr_rows(consequences="missing", alternatives="none")
        self.assertEqual(result["verdict"], "no")
        rule = "urn:judge-jev:tree:quality-adr:wave-1:rule-1"
        chosen = {qid: next(iter(q["criteria"])) for qid, q in questions.items()}
        chosen.update(consequences="missing", alternatives="none")
        want = [("no", rule, f"urn:judge-jev:question:adr.{qid}", label, questions[qid]["criteria"][label]) for qid, label in chosen.items()]
        self.assertEqual(rows, sorted(want))
        self.assertTrue(any("Fix: add alternatives." in criterion for *_, criterion in rows))

    def test_run_terms_record_digest_and_probabilities(self):
        result, lines, run = self.run_quality("--adr", "ADR-T-0001", {"ADR-T-0001/wave-1": tree_answers("quality-adr.json", p=0.8)})
        tree, _ = tree_fixture("adr")
        quads = jev_runs.run_triples(tree, run, lines, result)
        store = ox.Store()
        store.extend(quads)
        run_node = ox.NamedNode("urn:judge-jev:run:q1:ADR-T-0001")
        one = lambda s, p: [q.object for q in store.quads_for_pattern(s, jn(p), None)]  # noqa: E731
        self.assertEqual(one(run_node, "record"), [ox.NamedNode("urn:raptor:repo:test#ADR-T-0001")])
        digest = run["tree_sha256"] if isinstance(tree, dict) else jev_graph.tree_digest(tree).value
        self.assertEqual(one(run_node, "treeDigest"), [ox.Literal(digest)])
        self.assertEqual(one(run_node, "verdictValue"), [ox.Literal("yes")])
        (wave_run,) = [q.subject for q in store.quads_for_pattern(None, jn("inRun"), run_node)]
        self.assertEqual(one(wave_run, "requestId"), [ox.Literal(lines[0]["request_id"])])
        self.assertEqual(one(wave_run, "statement"), [])
        answers = [q.subject for q in store.quads_for_pattern(None, jn("ofWaveRun"), wave_run)]
        self.assertEqual(len(answers), 3)
        for a in answers:
            self.assertEqual(float(one(a, "confidence")[0].value), 0.8)
            self.assertEqual(len(one(a, "probability")), 3)
        total = sum(float(q.object.value) for q in store.quads_for_pattern(None, jn("p"), None))
        self.assertAlmostEqual(total, 3.0, places=3)

    def test_a_rebuild_without_the_repository_uses_the_unknown_repository(self):
        _iri, _store, _result = self.check_projection("adr", "--adr", "ADR-T-0001", {"ADR-T-0001/wave-1": tree_answers("quality-adr.json")})
        tree, _ = tree_fixture("adr")
        rebuilt = jev_runs.rebuild_from_log(self.d / "logs", "q1", tree)
        records = [q.object.value for q in rebuilt.value if q.predicate == jn("record")]
        self.assertEqual(records, ["urn:raptor:repo:unknown#ADR-T-0001"])


class ReqRun(RunCase):
    def test_a_per_statement_run_has_one_wave_run_per_judged_statement(self):
        answers = {"*": tree_answers("quality-req.json"),
                   "REQ-T-0001.s3/wave-1": tree_answers("quality-req.json", term="vague qualifier")}
        run_iri, store, result = self.check_projection("req", "--req", "REQ-T-0001", answers)
        self.assertEqual(result["verdict"], "no")
        run_node = ox.NamedNode(run_iri)
        wave_runs = [q.subject for q in store.quads_for_pattern(None, jn("inRun"), run_node)]
        statements = sorted(q.object.value for w in wave_runs for q in store.quads_for_pattern(w, jn("statement"), None))
        self.assertEqual(statements, sorted(["The CLI MUST exit 2 on a missing file.", "The CLI MUST NOT write outside the worktree."]))
        self.assertEqual(len(wave_runs), 2)  # the SHOULD statement is not judged
        # a rule fires only on the statements it matched: rule 2 matched the vague statement; the other matched nothing in the first-match rule
        fired = {next(q.object.value for q in store.quads_for_pattern(w, jn("statement"), None)):
                 [q.object.value for q in store.quads_for_pattern(w, jn("fired"), None)] for w in wave_runs}
        self.assertEqual(fired, {"The CLI MUST exit 2 on a missing file.": [],
                                 "The CLI MUST NOT write outside the worktree.": ["urn:judge-jev:tree:quality-req:wave-1:rule-2"]})
        rows = self.trace(store, run_iri, "REQ-T-0001")
        self.assertIn(("no", "urn:judge-jev:tree:quality-req:wave-1:rule-2", "urn:judge-jev:question:req.term", "vague qualifier"),
                      {r[:4] for r in rows})
        self.assertEqual(len(rows), 4)  # four questions, answered for the one statement that fired

    def test_a_passing_per_statement_run_fires_the_default_rule_for_every_statement(self):
        run_iri, store, result = self.check_projection("req", "--req", "REQ-T-0001", {"*": tree_answers("quality-req.json")})
        self.assertEqual(result["verdict"], "yes")
        rows = self.trace(store, run_iri, "REQ-T-0001")
        self.assertEqual({r[1] for r in rows}, {"urn:judge-jev:tree:quality-req:wave-1:rule-3"})
        self.assertEqual(len(rows), 8)  # four answers for each of two statements


def loaded(text, directory):
    """A tree graph from TTL text, checked against the shapes."""
    tree = jev_graph.load_tree(write(directory, text))
    assert isinstance(tree, jj.Ok), tree
    assert jev_graph.validate_tree(tree.value) == jj.Ok(None)
    return tree.value


def choice(label, confidence=0.9):
    return {"type": "choice", "choice": label, "confidence": confidence}


BRANCH_RUN = {"name": "q1", "tree_sha256": "-", "record_id": "REQ-X-0001", "repository": REPOSITORY}
BRANCH_LINES = [
    {"request_id": "rq1", "candidate_id": "wave-1", "answers": {"size": choice("big")}},
    {"request_id": "s1", "candidate_id": "wave-2", "answers": {"size": choice("huge")}},
    {"request_id": "s2", "candidate_id": "wave-2", "answers": {"size": choice("small")}},
]
BRANCH_WALK = {"verdict": "no", "waves": [
    {"node": "wave-1", "request_id": "rq1"},
    {"node": "wave-2", "per": "statement", "request_ids": ["s1", "s2"],
     "reason": [{"statement": {"text": "The CLI MUST fail."}}, {"statement": {"text": "The CLI MUST log."}}]}]}


class GraphIriRuns(unittest.TestCase):
    """F3: run triples use the tree graph's own IRIs, whatever they are, so TRACE_QUERY finds the rows."""

    def setUp(self):
        import tempfile
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.dir = scratch.name

    def trace(self, text, lines=BRANCH_LINES, walk=BRANCH_WALK):
        tree = loaded(text, self.dir)
        built = jev_runs.run_triples(tree, BRANCH_RUN, lines, walk)
        store = ox.Store()
        store.extend(list(tree.store) + built)
        rows = store.query(jev_runs.trace_query(jev_runs.run_iri(BRANCH_RUN), f"{REPOSITORY}#REQ-X-0001"))
        return tree, built, sorted((r["verdict"].value, r["rule"].value, r["question"].value, r["optionLabel"].value, r["criterion"].value)
                                   for r in rows)

    def test_branch_tree_with_kind_req_and_rules_r1_r2_traces_to_its_own_iris(self):
        _tree, built, rows = self.trace(BRANCH_TTL)
        self.assertEqual(rows, [
            ("no", "urn:judge-jev:tree:b:wave-1:r1", "urn:judge-jev:question:b.size", "big", "Big."),
            ("no", "urn:judge-jev:tree:b:wave-2:r1", "urn:judge-jev:question:b.size", "huge", "Huge."),
        ])
        fired = sorted(q.object.value for q in built if q.predicate == jn("fired"))
        self.assertEqual(fired, ["urn:judge-jev:tree:b:wave-1:r1", "urn:judge-jev:tree:b:wave-2:r1"])

    def test_a_tree_whose_iris_follow_no_naming_scheme_traces_to_those_iris(self):
        renamed = (BRANCH_TTL.replace("urn:judge-jev:tree:", "https://example.org/trees/")
                   .replace("urn:judge-jev:question:", "https://example.org/q#")
                   .replace("urn:judge-jev:option:", "https://example.org/o#"))
        _tree, built, rows = self.trace(renamed)
        self.assertEqual(rows, [
            ("no", "https://example.org/trees/b:wave-1:r1", "https://example.org/q#b.size", "big", "Big."),
            ("no", "https://example.org/trees/b:wave-2:r1", "https://example.org/q#b.size", "huge", "Huge."),
        ])
        minted = [t.value for q in built for t in (q.subject, q.object) if isinstance(t, ox.NamedNode) and t.value.startswith("urn:judge-jev:question:")]
        self.assertEqual(minted, [])
        digest = [q.object.value for q in built if q.predicate == jn("treeDigest")]
        self.assertEqual(digest, [jev_graph.tree_digest(_tree).value])

    def test_a_rule_position_is_its_rank_order_not_its_iri(self):
        # the rule IRIs sort the other way round from their ranks: position 1 is the lowest rank
        swapped = (BRANCH_TTL.replace("t:b:wave-2:r1", "t:b:wave-2:zzz").replace("t:b:wave-2:r2", "t:b:wave-2:aaa"))
        _tree, _built, rows = self.trace(swapped)
        self.assertIn(("no", "urn:judge-jev:tree:b:wave-2:zzz", "urn:judge-jev:question:b.size", "huge", "Huge."), rows)

    def test_labels_whose_slugs_collide_get_distinct_option_iris(self):
        text = BRANCH_TTL.replace('jj:label "big"', 'jj:label "A/B"').replace('jj:label "huge"', 'jj:label "a b"')
        self.assertEqual(jev_runs.slug("A/B"), jev_runs.slug("a b"))
        lines = [{"request_id": "rq1", "candidate_id": "wave-1", "answers": {"size": choice("A/B")}},
                 {"request_id": "s1", "candidate_id": "wave-2", "answers": {"size": choice("a b")}},
                 {"request_id": "s2", "candidate_id": "wave-2", "answers": {"size": choice("A/B")}}]
        _tree, built, rows = self.trace(text, lines)
        chosen = {q.subject.value: q.object.value for q in built if q.predicate == jn("chose")}
        self.assertEqual(chosen["urn:judge-jev:answer:q1:s1:size"], "urn:judge-jev:option:b.size:huge")
        self.assertEqual(chosen["urn:judge-jev:answer:q1:s2:size"], "urn:judge-jev:option:b.size:big")
        self.assertEqual(chosen["urn:judge-jev:answer:q1:rq1:size"], "urn:judge-jev:option:b.size:big")
        labels = {r[3] for r in rows}
        self.assertEqual(labels, {"A/B", "a b"})

    def test_two_waves_may_ask_distinct_questions_with_the_same_id(self):
        text = BRANCH_TTL.replace("t:b:wave-2 a jj:Wave ; jj:id \"wave-2\" ; jj:asks q:b.size ;", "t:b:wave-2 a jj:Wave ; jj:id \"wave-2\" ; jj:asks q:b.other ;") \
            .replace("jj:whenAll [ a jj:Condition ; jj:question q:b.size ; jj:choice o:b.size:huge ] .",
                     "jj:whenAll [ a jj:Condition ; jj:question q:b.other ; jj:choice o:b.other:huge ] .") + """
q:b.other a jj:Question ; jj:id "size" ; jj:rank 1 ; jj:instructions "Other?" ; jj:option o:b.other:small , o:b.other:huge .
o:b.other:small a jj:Option ; jj:rank 1 ; jj:label "small" ; jj:criterion "Other small." .
o:b.other:huge a jj:Option ; jj:rank 2 ; jj:label "huge" ; jj:criterion "Other huge." .
"""
        _tree, _built, rows = self.trace(text)
        self.assertIn(("no", "urn:judge-jev:tree:b:wave-2:r1", "urn:judge-jev:question:b.other", "huge", "Other huge."), rows)
        self.assertIn(("no", "urn:judge-jev:tree:b:wave-1:r1", "urn:judge-jev:question:b.size", "big", "Big."), rows)


class RenamedAdrRun(RunCase):
    def test_a_renamed_adr_tree_traces_and_rebuilds_from_the_log(self):
        import tempfile
        renamed = (ADR_TTL.replace("@prefix q:  <urn:judge-jev:question:>", "@prefix q:  <urn:example:q:>")
                   .replace("t:quality-adr:wave-1:rule-1", "t:quality-adr:wave-1:fail").replace("t:quality-adr:wave-1:rule-2", "t:quality-adr:wave-1:pass")
                   .replace('jj:rank 1 ;\n    jj:verdict "no"', 'jj:rank 10 ;\n    jj:verdict "no"')
                   .replace('jj:rank 2 ;\n    jj:verdict "yes"', 'jj:rank 20 ;\n    jj:verdict "yes"'))
        with tempfile.TemporaryDirectory() as scratch:
            tree = loaded(renamed, scratch)
        result, lines, run = self.run_quality("--adr", "ADR-T-0001", {"ADR-T-0001/wave-1": tree_answers("quality-adr.json", alternatives="none")})
        built = jev_runs.run_triples(tree, run, lines, result)
        rebuilt = jev_runs.rebuild_from_log(self.d / "logs", "q1", tree, repository=REPOSITORY)
        self.assertEqual(rebuilt.value, built)
        store = ox.Store()
        store.extend(list(tree.store) + built)
        rows = self.trace(store, jev_runs.run_iri(run), "ADR-T-0001")
        self.assertEqual(len(rows), 3)
        self.assertEqual({r[1] for r in rows}, {"urn:judge-jev:tree:quality-adr:wave-1:fail"})
        self.assertTrue(all(r[2].startswith("urn:example:q:adr.") for r in rows))
        self.assertIn("alternatives", {r[2].rsplit(".", 1)[1] for r in rows})


class RebuildMismatch(unittest.TestCase):
    """F5: a log that does not fit the tree, or lacks a field, is LOG.READ, never a KeyError."""

    def setUp(self):
        import tempfile
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.tree = loaded(BRANCH_TTL, scratch.name)

    @staticmethod
    def events(**overrides):
        base = {
            "result": [{"record_id": "R1", "request_id": "rq1", "candidate_id": "wave-1", "tree_sha256": "-", "answers": {"size": choice("big")}}],
            "statement": [],
            "wave": [{"record_id": "R1", "node": "wave-1", "request_id": "rq1"}],
            "verdict": [{"record_id": "R1", "verdict": "yes"}],
        }
        base.update(overrides)
        return base

    def rebuild(self, events, tree=None):
        with mock.patch.object(jev_runs, "read_run_events", return_value=jj.Ok(events)):
            return jev_runs.rebuild_from_log("unused", "q1", tree if tree is not None else self.tree, repository=REPOSITORY)

    def test_matching_events_rebuild(self):
        self.assertIsInstance(self.rebuild(self.events()), jj.Ok)

    def test_a_log_that_does_not_match_the_tree_is_log_read(self):
        ev = self.events
        cases = {
            "unknown node": ev(wave=[{"record_id": "R1", "node": "nope", "request_id": "rq1"}]),
            "unknown question": ev(result=[{"record_id": "R1", "request_id": "rq1", "answers": {"zzz": choice("big")}}]),
            "unknown choice": ev(result=[{"record_id": "R1", "request_id": "rq1", "answers": {"size": choice("bogus")}}]),
            "unlogged request": ev(wave=[{"record_id": "R1", "node": "wave-1", "request_id": "rq9"}]),
            "choice not a string": ev(result=[{"record_id": "R1", "request_id": "rq1", "answers": {"size": {"choice": ["big"]}}}]),
            "answers not an object": ev(result=[{"record_id": "R1", "request_id": "rq1", "answers": []}]),
        }
        for name, events in cases.items():
            with self.subTest(name):
                got = self.rebuild(events)
                self.assertEqual(got.error.code, "LOG.READ", got)
                self.assertIn("R1", got.error.message)

    def test_a_log_line_missing_a_field_is_log_read(self):
        ev = self.events()
        cases = {
            "result without answers": {"result": [{"record_id": "R1", "request_id": "rq1"}]},
            "result without request_id": {"result": [{"record_id": "R1", "answers": {"size": choice("big")}}]},
            "wave without request_id": {"wave": [{"record_id": "R1", "node": "wave-1"}]},
            "wave without node": {"wave": [{"record_id": "R1", "request_id": "rq1"}]},
            "verdict event without verdict": {"verdict": [{"record_id": "R1"}]},
            "statement without request_id": {"statement": [{"record_id": "R1", "statement": {"text": "x"}}]},
            "per-statement wave without request_ids": {"wave": [{"record_id": "R1", "node": "wave-2", "per": "statement"}]},
            "per-statement wave with an unlogged statement": {"wave": [{"record_id": "R1", "node": "wave-2", "per": "statement", "request_ids": ["s1"]}]},
        }
        for name, change in cases.items():
            with self.subTest(name):
                got = self.rebuild({**ev, **change})
                self.assertEqual(got.error.code, "LOG.READ", got)

    def test_a_json_tree_with_a_different_node_is_log_read(self):
        other = dict(ADR_JSON, nodes={"zzz": ADR_JSON["nodes"]["wave-1"]})
        events = self.events(result=[{"record_id": "R1", "request_id": "rq1", "tree_sha256": "-", "answers": {"context": choice("missing")}}])
        self.assertEqual(self.rebuild(events, other).error.code, "LOG.READ")

    def test_a_tree_that_does_not_validate_is_its_own_error_not_a_crash(self):
        store = ox.Store()
        store.load(input=BRANCH_TTL + "<urn:a> jj:x 1 .\n", format=ox.RdfFormat.TURTLE)
        got = self.rebuild(self.events(), jev_graph.TreeGraph(store, "memory"))
        self.assertEqual(got.error.code, "LOG.READ")
        self.assertIn("AllSubjectsShaped", got.error.message)


class Ports(unittest.TestCase):
    def test_transports_satisfy_the_port(self):
        self.assertIsInstance(jev_ports.FixtureTransport({}), jev_ports.Transport)
        self.assertIsInstance(jev_ports.PythonCoreTransport(jj.pump_batch, None, "", None, None), jev_ports.Transport)
        self.assertNotIsInstance(object(), jev_ports.Transport)

    def test_fixture_transport_returns_its_lines_in_request_order_and_records_calls(self):
        line = {"request_id": "p/x/c/r1", "answers": {}}
        fixture = jev_ports.FixtureTransport({"p/x/c/r1": line})
        got = fixture.send([{"request_id": "p/x/c/r1"}])
        self.assertEqual((got.value, fixture.calls), ([line], [[{"request_id": "p/x/c/r1"}]]))
        missing = jev_ports.FixtureTransport({}).send([{"request_id": "nope"}])
        self.assertEqual(missing.error.code, "INPUT.MISSING")
        self.assertEqual(jev_ports.FixtureTransport(lambda lines: [{"n": len(lines)}]).send([{}, {}]).value, [{"n": 2}])

    def test_python_core_transport_delegates_to_the_injected_pump(self):
        seen = []

        def pump(*args):
            seen.append(args)
            return jj.Ok(["line"])

        transport = jev_ports.PythonCoreTransport(pump, "settings", "key", "fixture", "log", True, {"f": 1})
        self.assertEqual(transport.send([{"a": 1}]).value, ["line"])
        self.assertEqual(seen, [([{"a": 1}], "settings", "key", "fixture", "log", True, {"f": 1})])

    def test_oxigraph_store_round_trips_record_run_and_query(self):
        store = jev_ports.OxigraphGraphStore()
        self.assertIsInstance(store, jev_ports.GraphStore)
        quad = ox.Quad(ox.NamedNode("urn:a"), jn("verdictValue"), ox.Literal("yes"), ox.DefaultGraph())
        self.assertEqual(store.record_run([quad]).value, 1)
        self.assertEqual(store.record_run([quad]).value, 0)  # a rebuild adds nothing new
        rows = store.query("PREFIX jj: <urn:judge-jev:ontology#> SELECT ?s ?v WHERE { ?s jj:verdictValue ?v }")
        self.assertEqual(rows.value, [{"s": "urn:a", "v": "yes"}])
        self.assertEqual(store.query("SELEKT").error.code, "VALIDATION.INPUT")

    def test_oxigraph_store_persists_at_a_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            first = jev_ports.OxigraphGraphStore(str(Path(td) / "g"))
            first.record_run([ox.Quad(ox.NamedNode("urn:a"), jn("verdictValue"), ox.Literal("no"), ox.DefaultGraph())])
            first.store.flush()
            del first
            again = jev_ports.OxigraphGraphStore(str(Path(td) / "g"))
            self.assertEqual(len(again.store), 1)
            del again  # close the RocksDB store before the directory is removed, or its files may still be written


if __name__ == "__main__":
    unittest.main()
