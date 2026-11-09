"""Definitions (ADR-JEV-0008; REQ-JEV-0212, REQ-JEV-0213): a definition is data attached to a record, or to a record and a
location, carried in the request state of every request it reaches. Jev is never called (call_jev fails the test); answers
come from fixture files; the run log is read back through sc-observability.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pyoxigraph as ox

from jev_support import SKILL, read_log
import jev_definitions  # noqa: E402
import jev_graph  # noqa: E402
import jev_judge as jj  # noqa: E402
import jev_ports  # noqa: E402
import jev_runs  # noqa: E402
from result import Err, Ok  # noqa: E402

from test_graph_tree import ADR_TTL, BRANCH_TTL  # noqa: E402
from test_graph_runs import tree_fixture  # noqa: E402
from test_jev_judge import answer, run_cli, write  # noqa: E402
from test_quality import INDEX, QualityCase, tree_answers  # noqa: E402

PREFIXES = """\
@prefix jj: <urn:judge-jev:ontology#> .
@prefix d: <urn:judge-jev:definition:> .
@prefix a: <urn:judge-jev:attachment:> .
"""
ADR = "urn:raptor:repo:test#ADR-T-0001"
REQ = "urn:raptor:repo:test#REQ-T-0001"
OTHER = "urn:raptor:repo:test#ADR-T-0009"


def definition(name, term, text="Means something.", source="docs/r.md", *attachments):
    """Turtle for one definition ``d:<name>`` with its attachments, each ``(record IRI, location or None)``."""
    names = [f"a:{name}{i}" for i, _ in enumerate(attachments)]
    out = f'd:{name} a jj:Definition ; jj:term "{term}" ; jj:text "{text}" ; jj:source "{source}"'
    out += f" ; jj:attachedTo {' , '.join(names)} .\n" if names else " .\n"
    for n, (record, location) in zip(names, attachments):
        out += f"{n} a jj:Attachment ; jj:record <{record}>" + (f' ; jj:location "{location}"' if location else "") + " .\n"
    return out


def ttl(*definitions):
    return PREFIXES + "".join(definitions)


def iri(name):
    return f"urn:judge-jev:definition:{name}"


def ref(name, term, text="Means something.", source="docs/r.md"):
    return {"iri": iri(name), "term": term, "digest": jev_definitions.digest(term, text, source)}


class DefinitionCase(QualityCase):
    def definitions(self, *definitions, name="defs.definitions.ttl"):
        return write(self.d, name, ttl(*definitions))

    def adr_state(self, *argv):
        """(exit code, the one request's state) of a dry run on the ADR record."""
        code, out = self.quality("--adr", "ADR-T-0001", "--dry-run", *argv)
        self.assertEqual(code, 0, out)
        return out["data"]["results"][0]["wave"]["request"], out["data"]["results"][0]


class Shapes(unittest.TestCase):
    """The closed shapes of definitions.shacl.ttl, through jev_graph.validate_definitions."""

    def check(self, text):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.definitions.ttl"
            path.write_bytes(text.encode("utf-8"))
            loaded = jev_graph.load_definitions(str(path))
            return jev_graph.validate_definitions(loaded.value) if isinstance(loaded, Ok) else loaded

    def test_a_definition_with_one_attachment_is_valid(self):
        self.assertEqual(self.check(ttl(definition("x", "fast", "Under 5 s.", "docs/r.md", (ADR, None)))), Ok([]))

    def test_a_definition_with_no_attachment_is_a_warning_not_a_violation(self):
        got = self.check(ttl(definition("x", "fast")))
        self.assertIsInstance(got, Ok)
        self.assertEqual(len(got.value), 1)
        self.assertIn(iri("x"), json.dumps(got.value))

    def test_an_attachment_takes_a_record_and_at_most_one_location(self):
        self.assertIsInstance(self.check(ttl(definition("x", "fast", "t", "docs/r.md", (ADR, "docs/r.md#H")))), Ok)
        two = ttl(definition("x", "fast", "t", "docs/r.md", (ADR, "docs/r.md"))) + 'a:x0 jj:location "docs/b.md" .\n'
        self.assertIsInstance(self.check(two), Err)

    def test_every_hostile_shape_is_a_typed_error(self):
        bad = {
            "blank-node definition": PREFIXES + '[] a jj:Definition ; jj:term "t" ; jj:text "x" ; jj:source "s" .\n',
            "literal record": PREFIXES + definition("x", "t", "x", "s", (ADR, None)).replace(f"<{ADR}>", '"ADR-T-0001"'),
            "two records": ttl(definition("x", "t", "x", "s", (ADR, None))) + f"a:x0 jj:record <{OTHER}> .\n",
            "no record": ttl(definition("x", "t", "x", "s", (ADR, None))).replace(f"jj:record <{ADR}>", ""),
            "stray subject": ttl(definition("x", "t", "x", "s", (ADR, None))) + "d:zz a jj:Other .\n",
            "extra property": ttl(definition("x", "t", "x", "s", (ADR, None))) + 'd:x jj:foo "bar" .\n',
            "no term": ttl(definition("x", "t", "x", "s", (ADR, None))).replace('jj:term "t" ;', ""),
            "two texts": ttl(definition("x", "t", "x", "s", (ADR, None))) + 'd:x jj:text "y" .\n',
        }
        for name, text in bad.items():
            with self.subTest(name):
                got = self.check(text)
                self.assertIsInstance(got, Err, got)
                self.assertEqual(got.error.code, "DEFINITIONS.INVALID")


class HostileFiles(DefinitionCase):
    """Every bad definitions file is a typed JSON error before any request, never a traceback."""

    def refused(self, data, code):
        path = Path(self.d) / "h.definitions.ttl"
        path.write_bytes(data)
        for flags in (("--dry-run",), ()):
            got, out = self.quality("--adr", "ADR-T-0001", "--definitions", str(path), *flags, answers=None if flags else {"*": tree_answers("quality-adr.json")})
            self.assertEqual((got, out["success"], out["error"]["code"]), (2, False, code), out)
            self.assertTrue(out["error"]["message"] and out["error"]["suggested_action"], out)
        self.assertFalse((self.d / "logs").exists())  # refused before the first request: nothing was logged
        return out["error"]["message"]

    def test_malformed_turtle(self):
        self.refused(b"d:one a jj:Definition ; ;; .", "INPUT.MALFORMED")

    def test_non_utf8(self):
        self.refused(b"\xff\xfe\x00 not utf-8", "INPUT.MALFORMED")

    def test_oversized_file(self):
        message = self.refused(b"#" + b"x" * (jev_graph.MAX_DEFINITIONS_BYTES + 1), "DEFINITIONS.INVALID")
        self.assertIn(str(jev_graph.MAX_DEFINITIONS_BYTES), message)

    def test_blank_node_definition(self):
        self.refused((PREFIXES + '[] a jj:Definition ; jj:term "t" ; jj:text "x" ; jj:source "docs/r.md" .\n').encode(), "DEFINITIONS.INVALID")

    def test_literal_record(self):
        text = ttl(definition("x", "t", "x", "docs/r.md", (ADR, None))).replace(f"<{ADR}>", '"ADR-T-0001"')
        self.refused(text.encode(), "DEFINITIONS.INVALID")

    def test_attachment_with_two_records(self):
        self.refused((ttl(definition("x", "t", "x", "docs/r.md", (ADR, None))) + f"a:x0 jj:record <{OTHER}> .\n").encode(), "DEFINITIONS.INVALID")

    def test_values_the_body_model_refuses(self):
        base = definition("x", "t", "x", "docs/r.md", (ADR, None))
        cases = {"term too long": base.replace('jj:term "t"', 'jj:term "' + "t" * 200 + '"'),
                 "absolute source": base.replace("docs/r.md", "/etc/passwd"),
                 "parent source": base.replace("docs/r.md", "../x.md"),
                 "multi-line term": base.replace('jj:term "t"', 'jj:term """a\nb"""'),
                 "record not a Raptor IRI": base.replace(f"<{ADR}>", "<urn:other>"),
                 "absolute location": base.replace(f"<{ADR}>", f'<{ADR}> ; jj:location "/abs"')}
        for name, text in cases.items():
            with self.subTest(name):
                self.refused(ttl(text).encode(), "DEFINITIONS.INVALID")

    def test_a_missing_file_and_a_directory(self):
        for target in (str(self.d / "nope.ttl"), str(self.d)):
            got, out = self.quality("--adr", "ADR-T-0001", "--definitions", target, "--dry-run")
            self.assertEqual((got, out["error"]["code"]), (2, "INPUT.MISSING"), out)

    def test_one_definition_iri_in_two_files_is_refused_naming_both(self):
        a = self.definitions(definition("x", "fast", "t", "docs/r.md", (ADR, None)), name="a.definitions.ttl")
        b = self.definitions(definition("x", "slow", "t", "docs/r.md", (ADR, None)), name="b.definitions.ttl")
        got, out = self.quality("--adr", "ADR-T-0001", "--definitions", a, "--definitions", b, "--dry-run")
        self.assertEqual((got, out["error"]["code"]), (2, "DEFINITIONS.INVALID"), out)
        self.assertIn(iri("x"), out["error"]["message"])
        self.assertTrue(a in out["error"]["message"] and b in out["error"]["message"], out)


class Digest(unittest.TestCase):
    def test_a_trees_digest_does_not_change_when_definitions_are_loaded_beside_it(self):
        with tempfile.TemporaryDirectory() as d:
            tree = Path(d) / "tree.ttl"
            tree.write_bytes(ADR_TTL.encode("utf-8"))
            defs = Path(d) / "x.definitions.ttl"
            defs.write_bytes(ttl(definition("x", "fast", "t", "docs/r.md", (ADR, None))).encode("utf-8"))
            loaded = jev_graph.load_tree(str(tree)).value
            before = jev_graph.tree_digest(loaded)
            store = jev_ports.OxigraphGraphStore()
            self.assertGreater(store.load_definitions([str(defs)]).value, 0)
            self.assertEqual(jev_graph.tree_digest(jev_graph.load_tree(str(tree)).value), before)
            # and the same store holding both: definitions sit in a named graph, outside the tree's default graph
            loaded.store.load(defs.read_bytes(), format=ox.RdfFormat.TURTLE, to_graph=ox.NamedNode("urn:judge-jev:definitions:x"))
            self.assertEqual(jev_graph.tree_digest(loaded), before)

    def test_a_definitions_digest_is_its_term_text_and_source_only(self):
        d = jev_definitions.digest("fast", "Under 5 s.", "docs/r.md")
        self.assertEqual(d, jev_definitions.digest("fast", "Under 5 s.", "docs/r.md"))
        self.assertEqual(len(d), 64)
        for changed in (("slow", "Under 5 s.", "docs/r.md"), ("fast", "Under 6 s.", "docs/r.md"), ("fast", "Under 5 s.", "docs/o.md")):
            self.assertNotEqual(jev_definitions.digest(*changed), d)


class Composition(DefinitionCase):
    def test_no_definitions_leaves_the_request_byte_identical(self):
        plain, _ = self.adr_state()
        for name, text in (("other record", definition("o", "x", "t", "docs/r.md", (OTHER, None))),
                           ("only at a location", definition("l", "x", "t", "docs/r.md", (ADR, "docs/r.md")))):
            with self.subTest(name):
                request, result = self.adr_state("--definitions", self.definitions(text))
                self.assertEqual(jj.encode_body(request), jj.encode_body(plain))
                self.assertNotIn("definitions", request["state"])
                self.assertNotIn("definitions", result)
        self.assertNotIn("definitions", plain["state"])

    def test_a_record_gets_exactly_its_definitions_sorted_by_term(self):
        path = self.definitions(definition("z", "zeta", "Last.", "docs/r.md", (ADR, None)),
                                definition("a", "alpha", "First.", "docs/r.md", (ADR, None)),
                                definition("m", "mid", "Other record.", "docs/r.md", (OTHER, None)))
        request, result = self.adr_state("--definitions", path)
        self.assertEqual(request["state"]["definitions"], [{"term": "alpha", "text": "First."}, {"term": "zeta", "text": "Last."}])
        self.assertEqual(result["definitions"], [ref("a", "alpha", "First."), ref("z", "zeta", "Last.")])
        self.assertEqual(request["state"]["item"], self.adr_state()[0]["state"]["item"])

    def test_a_definition_with_two_attachments_is_carried_once(self):
        path = self.definitions(definition("x", "fast", "t", "docs/r.md", (ADR, None), (ADR, None)))
        # two attachment nodes naming the same record: one entry in the request
        request, _ = self.adr_state("--definitions", path)
        self.assertEqual(request["state"]["definitions"], [{"term": "fast", "text": "t"}])

    def test_the_repository_definitions_are_the_default(self):
        folder = self.d / "repo" / ".sc" / "judge-jev"
        folder.mkdir(parents=True)
        (folder / "definitions.ttl").write_bytes(ttl(definition("x", "fast", "t", "docs/r.md", (ADR, None))).encode())
        request, _ = self.adr_state("--repository-root", str(self.d / "repo"))
        self.assertEqual(request["state"]["definitions"], [{"term": "fast", "text": "t"}])

    def test_an_explicit_definitions_file_replaces_the_repository_default(self):
        folder = self.d / "repo" / ".sc" / "judge-jev"
        folder.mkdir(parents=True)
        (folder / "definitions.ttl").write_bytes(ttl(definition("x", "fast", "t", "docs/r.md", (ADR, None))).encode())
        mine = self.definitions(definition("y", "slow", "s", "docs/r.md", (ADR, None)))
        request, _ = self.adr_state("--repository-root", str(self.d / "repo"), "--definitions", mine)
        self.assertEqual(request["state"]["definitions"], [{"term": "slow", "text": "s"}])

    def test_a_per_statement_wave_carries_the_definitions_in_every_request(self):
        path = self.definitions(definition("x", "fast", "t", "docs/r.md", (REQ, None)))
        code, out = self.quality("--req", "REQ-T-0001", "--definitions", path, "--dry-run")
        self.assertEqual(code, 0, out)
        requests = out["data"]["results"][0]["wave"]["requests"]
        self.assertEqual(len(requests), 2)
        for r in requests:
            self.assertEqual(r["request"]["state"]["definitions"], [{"term": "fast", "text": "t"}])

    def test_definitions_are_never_truncated_and_count_toward_the_size_limit(self):
        text = "w" * 1900
        many = [definition(f"d{i:02d}", f"term{i:02d}", text, "docs/r.md", (ADR, None)) for i in range(12)]
        path = self.definitions(*many)
        for flags in (("--dry-run",), ()):
            code, out = self.quality("--adr", "ADR-T-0001", "--definitions", path, *flags, answers=None if flags else {"*": tree_answers("quality-adr.json")})
            self.assertEqual((code, out["error"]["code"]), (2, "JEV.CONTEXT_EXCEEDED"), out)
        self.assertFalse((self.d / "logs").exists())
        # under the limit every definition is whole in the request
        path = self.definitions(*many[:3])
        request, _ = self.adr_state("--definitions", path)
        self.assertEqual([d["text"] for d in request["state"]["definitions"]], [text] * 3)

    def test_the_request_events_hold_each_definitions_digest(self):
        path = self.definitions(definition("b", "beta", "Second.", "docs/b.md", (ADR, None)),
                                definition("a", "alpha", "First.", "docs/a.md", (ADR, None)))
        code, out = self.quality("--adr", "ADR-T-0001", "--definitions", path, answers={"*": tree_answers("quality-adr.json")})
        self.assertEqual(code, 0, out)
        expected = [ref("a", "alpha", "First.", "docs/a.md"), ref("b", "beta", "Second.", "docs/b.md")]
        self.assertEqual(out["data"]["results"][0]["definitions"], expected)
        events = read_log(self.d / "logs")
        for action in ("request", "answer", "result", "wave", "verdict"):
            (event,) = [e for e in events if e["action"] == action]
            self.assertEqual(event["fields"]["definitions"], expected, action)
        sent = [e for e in events if e["action"] == "request"][0]["fields"]["request"]
        self.assertEqual(sent["state"]["definitions"], [{"term": "alpha", "text": "First."}, {"term": "beta", "text": "Second."}])

    def test_a_run_without_definitions_logs_none(self):
        code, out = self.quality("--adr", "ADR-T-0001", answers={"*": tree_answers("quality-adr.json")})
        self.assertEqual(code, 0, out)
        for e in read_log(self.d / "logs"):
            self.assertNotIn("definitions", e["fields"], e["action"])

    def test_the_run_triples_link_the_run_to_each_definition(self):
        path = self.definitions(definition("b", "beta", "Second.", "docs/b.md", (ADR, None)),
                                definition("a", "alpha", "First.", "docs/a.md", (ADR, None)))
        code, out = self.quality("--adr", "ADR-T-0001", "--definitions", path, answers={"*": tree_answers("quality-adr.json")})
        self.assertEqual(code, 0, out)
        tree, _quads = tree_fixture("adr")
        rebuilt = jev_runs.rebuild_from_log(self.d / "logs", "q1", tree, repository="urn:raptor:repo:test")
        self.assertIsInstance(rebuilt, Ok, rebuilt)
        linked = sorted(q.object.value for q in rebuilt.value if q.predicate.value.endswith("#carriedDefinition"))
        self.assertEqual(linked, [iri("a"), iri("b")])
        run_subjects = {q.subject.value for q in rebuilt.value if q.predicate.value.endswith("#carriedDefinition")}
        self.assertEqual(len(run_subjects), 1)

    def test_a_run_without_definitions_has_no_carried_definition_triple(self):
        code, out = self.quality("--adr", "ADR-T-0001", answers={"*": tree_answers("quality-adr.json")})
        self.assertEqual(code, 0, out)
        tree, _quads = tree_fixture("adr")
        rebuilt = jev_runs.rebuild_from_log(self.d / "logs", "q1", tree, repository="urn:raptor:repo:test")
        self.assertFalse([q for q in rebuilt.value if q.predicate.value.endswith("#carriedDefinition")])

    def test_the_shipped_question_wording_is_unchanged(self):
        path = self.definitions(definition("x", "fast", "t", "docs/r.md", (ADR, None)))
        request, _ = self.adr_state("--definitions", path)
        plain, _ = self.adr_state()
        self.assertEqual(request["questions"], plain["questions"])
        shipped = json.loads((SKILL / "assets" / "questions" / "quality-adr.json").read_text(encoding="utf-8"))
        self.assertEqual(request["questions"], shipped["nodes"]["wave-1"]["questions"])


class Compare(DefinitionCase):
    def compare(self, *argv, answers=None, run="c1"):
        extra = ["--answers-file", write(self.d, "answers.json", answers)] if answers is not None else []
        return run_cli(["compare-definition", "--index", self.index, "--run-dir", str(self.d / "logs"), "--run-name", run,
                        *argv, *extra])

    def adr(self, *argv, **kw):
        return self.compare("--adr", "ADR-T-0001", *argv, **kw)

    def setUp(self):
        super().setUp()
        self.defs = self.definitions(definition("fast", "fast", "Under 5 s.", "docs/r.md", (ADR, None)),
                                     definition("other", "other", "Kept in both arms.", "docs/r.md", (ADR, None)),
                                     definition("loc", "alpha", "Only here.", "docs/r.md", (ADR, "docs/r.md#H")),
                                     definition("lone", "lone", "Never attached.", "docs/r.md"))

    def fixture(self, with_choice=None, with_p=0.9, without_p=0.9, base=None):
        base = base or {}
        options = list(tree_answers("quality-adr.json"))
        questions = json.loads((SKILL / "assets" / "questions" / "quality-adr.json").read_text(encoding="utf-8"))["nodes"]["wave-1"]["questions"]
        arm = lambda p, choices: {q: answer(choices.get(q, next(iter(c["criteria"]))), p=p, options=list(c["criteria"])) for q, c in questions.items()}  # noqa: E731
        self.assertTrue(options)
        return {"without/ADR-T-0001/wave-1": arm(without_p, base), "with/ADR-T-0001/wave-1": arm(with_p, {**base, **(with_choice or {})})}

    def test_a_flipped_choice_is_material(self):
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), answers=self.fixture(with_choice={"context": "background only"}))
        self.assertEqual(code, 0, out)
        data = out["data"]
        self.assertTrue(data["material"])
        flips = [a for a in data["answers"] if a["choice_changed"]]
        self.assertEqual([(a["question"], a["without"]["choice"], a["with"]["choice"]) for a in flips], [("context", "problem and forces", "background only")])

    def test_identical_answers_are_not_material(self):
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), answers=self.fixture())
        self.assertEqual((code, out["data"]["material"], out["data"]["answers_material"]), (0, False, 0), out)

    def test_a_move_on_the_same_side_of_the_threshold_is_not_material(self):
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), answers=self.fixture(without_p=0.90, with_p=0.95))
        self.assertEqual(code, 0, out)
        self.assertFalse(out["data"]["material"])
        self.assertTrue(all(a["confidence_change"] == 0.05 or abs(a["confidence_change"] - 0.05) < 1e-9 for a in out["data"]["answers"]))
        self.assertFalse(any(a["crosses_threshold"] for a in out["data"]["answers"]))

    def test_a_move_across_the_threshold_is_material(self):
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), answers=self.fixture(without_p=0.70, with_p=0.50))
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["material"])
        self.assertTrue(all(a["crosses_threshold"] and a["material"] for a in out["data"]["answers"]))

    def test_the_threshold_applied_is_recorded_and_a_different_one_changes_the_ruling(self):
        answers = self.fixture(without_p=0.70, with_p=0.50)
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), "--threshold", "0.4", answers=answers, run="c2")
        self.assertEqual((code, out["data"]["threshold"], out["data"]["material"]), (0, 0.4, False), out)
        (event,) = [e for e in read_log(self.d / "logs", action="compare") if e["fields"]["threshold"] == 0.4]
        self.assertEqual(event["fields"]["material"], False)
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), answers=answers, run="c3")
        self.assertEqual(out["data"]["threshold"], jj.DEFAULT_THRESHOLD)

    def test_two_candidates_that_each_move_part_of_the_way_are_material_together(self):
        # none: 0.70; with fast: 0.65; with other: 0.65; with both: 0.55. Each candidate alone stays above the 0.6 threshold;
        # together they cross it. The arms hold only the named candidates (the files hold nothing else), so they are exactly
        # the states above.
        one = self.definitions(definition("fast", "fast", "Under 5 s.", "docs/r.md", (ADR, None)), name="one.definitions.ttl")
        two = self.definitions(definition("other", "other", "Kept.", "docs/r.md", (ADR, None)), name="two.definitions.ttl")
        both = self.definitions(definition("fast", "fast", "Under 5 s.", "docs/r.md", (ADR, None)),
                                definition("other", "other", "Kept.", "docs/r.md", (ADR, None)), name="both.definitions.ttl")
        for name, path, flags, p_with, material in (
                ("fast alone", one, ("--definition", iri("fast")), 0.65, False),
                ("other alone", two, ("--definition", iri("other")), 0.65, False),
                ("together", both, ("--definition", iri("fast"), "--definition", iri("other")), 0.55, True)):
            with self.subTest(name):
                code, out = self.adr("--definitions", path, *flags, answers=self.fixture(without_p=0.70, with_p=p_with), run=name.replace(" ", ""))
                self.assertEqual((code, out["data"]["material"]), (0, material), out)
                self.assertEqual(out["data"]["threshold"], 0.6)
        self.assertEqual(out["data"]["arms"]["without"]["definitions"], [])
        self.assertEqual([d["iri"] for d in out["data"]["definitions"]], [iri("fast"), iri("other")])

    def test_the_arms_drop_only_the_candidates_and_run_under_their_own_names(self):
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), answers=self.fixture())
        self.assertEqual(code, 0, out)
        arms = out["data"]["arms"]
        self.assertEqual(arms["without"]["definitions"], [ref("other", "other", "Kept in both arms.")])
        self.assertEqual(arms["with"]["definitions"], [ref("fast", "fast", "Under 5 s."), ref("other", "other", "Kept in both arms.")])
        self.assertEqual((arms["without"]["run"], arms["with"]["run"]), ("c1.without", "c1.with"))
        for arm in ("without", "with"):
            requests = [e["fields"] for e in read_log(self.d / "logs", action="request") if e["fields"]["run"] == f"c1.{arm}"]
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0]["definitions"], arms[arm]["definitions"])
        (summary,) = read_log(self.d / "logs", action="compare")
        self.assertEqual(summary["fields"]["runs"], {"without": "c1.without", "with": "c1.with"})

    def test_fixture_keys_tell_the_arms_apart(self):
        # 'with/<record>/<node>' and 'without/<record>/<node>' are one arm's alone and win; unprefixed keys serve both arms
        shared = {"ADR-T-0001/wave-1": tree_answers("quality-adr.json")}
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), answers=shared)
        self.assertEqual((code, out["data"]["material"]), (0, False), out)
        only_with = {**shared, "with/ADR-T-0001/wave-1": tree_answers("quality-adr.json", context="background only")}
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), answers=only_with, run="c4")
        self.assertEqual((code, out["data"]["material"]), (0, True), out)
        wildcard = {"*": tree_answers("quality-adr.json"), "without/*": tree_answers("quality-adr.json", context="background only")}
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), answers=wildcard, run="c5")
        self.assertEqual((code, out["data"]["material"]), (0, True), out)

    def test_dry_run_shows_both_arms_requests_and_writes_nothing(self):
        code, out = self.adr("--definitions", self.defs, "--definition", iri("fast"), "--dry-run")
        self.assertEqual(code, 0, out)
        arms = out["data"]["arms"]
        self.assertEqual(arms["without"]["wave"]["request"]["state"]["definitions"], [{"term": "other", "text": "Kept in both arms."}])
        self.assertEqual(arms["with"]["wave"]["request"]["state"]["definitions"],
                         [{"term": "fast", "text": "Under 5 s."}, {"term": "other", "text": "Kept in both arms."}])
        self.assertEqual(out["data"]["threshold"], jj.DEFAULT_THRESHOLD)
        self.assertFalse((self.d / "logs").exists())

    def test_a_dry_run_without_other_definitions_has_no_key_in_the_without_arm(self):
        only = self.definitions(definition("fast", "fast", "t", "docs/r.md", (ADR, None)), name="one.definitions.ttl")
        code, out = self.adr("--definitions", only, "--definition", iri("fast"), "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertNotIn("definitions", out["data"]["arms"]["without"]["wave"]["request"]["state"])

    def test_a_record_and_location_definition_compares_at_its_location_only(self):
        code, out = self.adr("--definitions", self.defs, "--definition", iri("loc"), "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "DEFINITIONS.NOT_ATTACHED"), out)
        code, out = self.adr("--definitions", self.defs, "--definition", iri("loc"), "--location", "docs/r.md#Other", "--dry-run")
        self.assertEqual((code, out["error"]["code"]), (2, "DEFINITIONS.NOT_ATTACHED"), out)
        code, out = self.adr("--definitions", self.defs, "--definition", iri("loc"), "--location", "docs/r.md#H", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["location"], "docs/r.md#H")
        with_arm = out["data"]["arms"]["with"]["wave"]["request"]["state"]
        self.assertEqual(with_arm["location"], "docs/r.md#H")
        self.assertEqual([d["term"] for d in with_arm["definitions"]], ["alpha", "fast", "other"])
        without = out["data"]["arms"]["without"]["wave"]["request"]["state"]
        self.assertEqual([d["term"] for d in without["definitions"]], ["fast", "other"])

    def test_a_location_run_logs_the_location(self):
        code, out = self.adr("--definitions", self.defs, "--definition", iri("loc"), "--location", "docs/r.md#H", answers=self.fixture())
        self.assertEqual(code, 0, out)
        (summary,) = read_log(self.d / "logs", action="compare")
        self.assertEqual(summary["fields"]["location"], "docs/r.md#H")

    def test_typed_errors(self):
        cases = [
            (("--definition", iri("lone")), "DEFINITIONS.NOT_ATTACHED"),
            (("--definition", iri("nothing")), "DEFINITIONS.NOT_FOUND"),
            (("--definition", iri("fast"), "--threshold", "1.5"), "VALIDATION.INPUT"),
            (("--definition", iri("fast"), "--threshold", "nan"), "VALIDATION.INPUT"),
            (("--definition", iri("fast"), "--location", "/abs"), "VALIDATION.INPUT"),
        ]
        for argv, code in cases:
            with self.subTest(argv):
                got, out = self.adr("--definitions", self.defs, *argv, "--dry-run")
                self.assertEqual((got, out["success"], out["error"]["code"]), (2, False, code), out)
        got, out = self.compare("--adr", "ADR-T-0001", "--req", "REQ-T-0001", "--definitions", self.defs, "--definition", iri("fast"), "--dry-run")
        self.assertEqual((got, out["error"]["code"]), (2, "VALIDATION.INPUT"), out)
        got, out = self.adr("--definition", iri("fast"), "--dry-run")
        self.assertEqual((got, out["error"]["code"]), (2, "DEFINITIONS.NOT_FOUND"), out)

    def test_a_live_comparison_without_an_answers_file_needs_consent_before_any_call(self):
        got, out = self.adr("--definitions", self.defs, "--definition", iri("fast"))
        self.assertEqual(got, 2, out)
        self.assertFalse(out["success"])


if __name__ == "__main__":
    unittest.main()
