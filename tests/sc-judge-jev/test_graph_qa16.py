"""Hostile and malformed tree inputs never crash the graph layer (ADR-JEV-0006, ADR-JEV-0007; qa16 findings F1 to F9).

The ontology defines the graph and validates its edges (closed shapes); the pydantic models verify the body of a node.
Every bad input is a typed error. Every case is enumerated: no sleeps, no timing, no randomness. The slow cases of the
reviewer's probes (a 20000-deep blank-node chain, a 900 KiB wide wave) are asserted as refusals, never run to completion.
"""
import contextlib
import io
import json
import logging
import os
import re
import unittest
from pathlib import Path
from unittest import mock

import pyoxigraph as ox

from jev_support import SKILL  # noqa: F401,E402
import jev_graph  # noqa: E402
import jev_ports  # noqa: E402
import jev_runs  # noqa: E402
from result import Err, Ok  # noqa: E402

from test_graph_tree import ADR_JSON, ADR_TTL, BRANCH_TTL, GraphCase, write  # noqa: E402

XSD = "http://www.w3.org/2001/XMLSchema#"
BLANK_LABEL = re.compile(r"_:|\b[0-9a-f]{16,}\b")


def chain(depth: int) -> str:
    return "<urn:a> jj:x " + "[ jj:x " * depth + "1" + " ]" * depth + " .\n"


class ClosedGraphTests(GraphCase):
    """F1: the graph is closed; nothing rides along outside the shapes."""

    def test_a_deep_blank_node_chain_beside_a_valid_tree_is_refused_not_canonicalised(self):
        tree = self.load(ADR_TTL + chain(10000))
        result = jev_graph.validate_tree(tree)
        self.assertEqual(result.error.code, "QUALITY.TREE")
        self.assertIn("jjs:AllSubjectsShaped", result.error.message)
        self.assertEqual(jev_graph.tree_digest(tree).error.code, "QUALITY.TREE")

    def test_the_digest_of_a_20000_deep_chain_in_memory_is_a_typed_error_not_a_segfault(self):
        store = ox.Store()
        store.load(input=ADR_TTL + chain(20000), format=ox.RdfFormat.TURTLE)
        tree = jev_graph.TreeGraph(store, "memory")
        self.assertEqual(jev_graph.tree_digest(tree).error.code, "QUALITY.TREE")
        with self.assertRaises(jev_graph.TreeInvalid):
            jev_graph.tree_to_quality_json(tree)
        with self.assertRaises(jev_graph.TreeInvalid):
            jev_graph.compile_wave(tree, "wave-1")
        with self.assertRaises(jev_graph.TreeInvalid):
            jev_graph.iri_index(tree)

    def test_the_reviewers_20000_deep_file_is_refused_by_the_size_limit_before_it_is_parsed(self):
        path = write(self.dir, ADR_TTL + chain(20000))
        self.assertGreater(os.path.getsize(path), jev_graph.MAX_TREE_BYTES)
        with mock.patch.object(jev_graph.ox.Store, "load", side_effect=AssertionError("parsed")):
            result = jev_graph.load_tree(path)
        self.assertEqual(result.error.code, "QUALITY.TREE")
        self.assertIn(str(jev_graph.MAX_TREE_BYTES), result.error.message)

    def test_a_file_of_exactly_the_limit_loads_and_one_byte_more_does_not(self):
        text = ADR_TTL + "\n#" + "x" * (jev_graph.MAX_TREE_BYTES - len(ADR_TTL.encode("utf-8")) - 2)
        self.assertEqual(len(text.encode("utf-8")), jev_graph.MAX_TREE_BYTES)
        self.assertIsInstance(jev_graph.load_tree(write(self.dir, text, "exact.ttl")), Ok)
        self.assertEqual(jev_graph.load_tree(write(self.dir, text + "x", "over.ttl")).error.code, "QUALITY.TREE")

    def test_a_subject_outside_the_shaped_classes_is_refused(self):
        for name, extra in (("untyped iri", "<urn:a> jj:x 1 .\n"),
                            ("other class", "<urn:a> a <urn:other:Thing> ; jj:id \"a\" .\n"),
                            ("untyped blank node", "[ jj:x 1 ] jj:y 2 .\n"),
                            ("condition-less blank", "<urn:a> a jj:Option ; jj:rank 9 ; jj:label \"l\" ; jj:criterion \"c\" ; jj:x [ jj:y 1 ] .\n")):
            with self.subTest(name):
                result = self.validate(ADR_TTL + extra)
                self.assertEqual(result.error.code, "QUALITY.TREE")

    def test_every_jj_node_shape_is_closed(self):
        cases = {
            "tree": (ADR_TTL.replace('    jj:id "quality-adr" ;', '    jj:id "quality-adr" ; jj:bogus 1 ;'), "jjs:TreeShape"),
            "wave": (ADR_TTL.replace('    jj:id "wave-1" ;', '    jj:id "wave-1" ; jj:bogus 1 ;'), "jjs:WaveShape"),
            "question": (ADR_TTL.replace('    jj:id "context" ;', '    jj:id "context" ; jj:bogus 1 ;'), "jjs:QuestionShape"),
            "option": (ADR_TTL.replace('jj:label "missing" ;', 'jj:label "missing" ; jj:bogus 1 ;', 1), "jjs:OptionShape"),
            "verdict rule": (ADR_TTL.replace('jj:rank 2 ;\n    jj:verdict "yes"', 'jj:rank 2 ; jj:bogus 1 ;\n    jj:verdict "yes"'), "jjs:VerdictRuleShape"),
            "condition": (ADR_TTL.replace("[ a jj:Condition ; jj:question q:adr.context ;", "[ a jj:Condition ; jj:bogus 1 ; jj:question q:adr.context ;"), "jjs:ConditionShape"),
            "branch rule": (BRANCH_TTL.replace("jj:rank 2 ; jj:goto t:b:done", "jj:rank 2 ; jj:bogus 1 ; jj:goto t:b:done"), "jjs:BranchRuleShape"),
            "leaf": (BRANCH_TTL.replace('jj:id "done" ;', 'jj:id "done" ; jj:bogus 1 ;'), "jjs:LeafShape"),
            "rdfs label on a leaf": (BRANCH_TTL.replace('jj:id "done" ;', 'jj:id "done" ; <http://www.w3.org/2000/01/rdf-schema#label> "x" ;'), "jjs:LeafShape"),
        }
        for name, (text, shape) in cases.items():
            with self.subTest(name):
                self.assertRefused(text, shape=shape)

    def test_blank_nodes_can_only_be_conditions(self):
        for name, text in (("tree", ADR_TTL.replace("t:quality-adr a jj:Tree ;", "_:t a jj:Tree ;")),
                           ("rule", ADR_TTL.replace("jj:rule t:quality-adr:wave-1:rule-1 , t:quality-adr:wave-1:rule-2 .",
                                                    'jj:rule t:quality-adr:wave-1:rule-1 , [ a jj:VerdictRule ; jj:rank 2 ; jj:verdict "yes" ] .')
                                      .replace('t:quality-adr:wave-1:rule-2 a jj:VerdictRule ;\n    jj:rank 2 ;\n    jj:verdict "yes" .', ""))):
            with self.subTest(name):
                self.assertEqual(self.validate(text).error.code, "QUALITY.TREE")

    def test_the_shipped_trees_still_validate_and_digest(self):
        for text in (ADR_TTL, BRANCH_TTL):
            tree = self.load(text)
            self.assertEqual(jev_graph.validate_tree(tree), Ok(None))
            self.assertRegex(jev_graph.tree_digest(tree).value, r"^[0-9a-f]{64}$")

    def test_duplicate_conditions_digest_without_blowing_up(self):
        same = '[ a jj:Condition ; jj:question q:adr.context ; jj:choice o:adr.context:missing ]'
        text = ADR_TTL.replace("jj:whenAny\n", "jj:whenAny\n        " + " ,\n        ".join([same] * 40) + " ,\n", 1)
        self.assertRegex(jev_graph.tree_digest(self.load(text)).value, r"^[0-9a-f]{64}$")


class DatatypeTests(GraphCase):
    """F2: every literal property has a datatype, so a conversion cannot yield a mixed or wrong type."""

    def test_modal_of_mixed_types_is_refused_before_it_can_reach_sorted(self):
        for name, modal in (("string and integer", '"Must" , 5'), ("iri", "<urn:x> , \"Must\""), ("language tag", '"Must"@en'),
                            ("typed", f'"Must"^^<{XSD}token>')):
            with self.subTest(name):
                text = BRANCH_TTL.replace('jj:modal "MustNot" , "Must"', f"jj:modal {modal}")
                hits = self.assertRefused(text, path="jj:modal")
                self.assertTrue(any(h["component"] == "DatatypeConstraintComponent" for h in hits))

    def test_every_literal_property_refuses_a_wrong_datatype(self):
        cases = {
            "tree kind": (ADR_TTL.replace('jj:kind "adr"', "jj:kind 5"), "jj:kind"),
            "tree note": (ADR_TTL.replace('jj:note "draft, pending Rand approval"', "jj:note 5"), "jj:note"),
            "tree version": (ADR_TTL.replace("jj:version 3", 'jj:version "3"'), "jj:version"),
            "tree approved": (ADR_TTL.replace("jj:approved false", 'jj:approved "false"'), "jj:approved"),
            "tree id": (ADR_TTL.replace('jj:id "quality-adr"', "jj:id 7"), "jj:id"),
            "wave per": (BRANCH_TTL.replace('jj:per "statement"', "jj:per 1"), "jj:per"),
            "wave statements": (BRANCH_TTL.replace('jj:statements "requirement_statement.statements"', "jj:statements 1"), "jj:statements"),
            "question id": (ADR_TTL.replace('jj:id "context"', "jj:id 1"), "jj:id"),
            "question instructions": (BRANCH_TTL.replace('jj:instructions "How big?"', "jj:instructions 1"), "jj:instructions"),
            "option label": (BRANCH_TTL.replace('jj:label "small"', "jj:label 1"), "jj:label"),
            "option criterion": (BRANCH_TTL.replace('jj:criterion "Small."', "jj:criterion 1"), "jj:criterion"),
            "leaf verdict": (BRANCH_TTL.replace('t:b:done a jj:Leaf ; jj:id "done" ; jj:verdict "yes"', 't:b:done a jj:Leaf ; jj:id "done" ; jj:verdict 1'), "jj:verdict"),
            "rule rank": (BRANCH_TTL.replace("jj:rank 2 ; jj:goto t:b:done", 'jj:rank "2" ; jj:goto t:b:done'), "jj:rank"),
        }
        for name, (text, path) in cases.items():
            with self.subTest(name):
                self.assertRefused(text, path=path)

    def test_a_valid_tree_with_two_modals_converts_to_sorted_strings(self):
        tree = self.load(BRANCH_TTL)
        self.assertEqual(jev_graph.tree_to_quality_json(tree)["nodes"]["wave-2"]["modals"], ["Must", "MustNot"])


class ViolationTextTests(GraphCase):
    """F6: violation text and order are the same on every run, and never print a blank node label."""

    TEXTS = {
        "choice not an option (blank condition)": ADR_TTL.replace("jj:choice o:adr.context:background-only , o:adr.context:missing",
                                                                  "jj:choice o:adr.context:background-only , o:adr.alternatives:none"),
        "closed condition": ADR_TTL.replace("[ a jj:Condition ; jj:question q:adr.context ;", "[ a jj:Condition ; jj:bogus 1 ; jj:question q:adr.context ;"),
        "untyped blank condition": ADR_TTL.replace("[ a jj:Condition ; jj:question q:adr.context ;", "[ jj:question q:adr.context ;"),
        "property shape (missing label)": ADR_TTL.replace('    jj:label "problem and forces" ;\n', ""),
        "two conditions with the same problem": ADR_TTL.replace("jj:choice o:adr.context:background-only , o:adr.context:missing",
                                                                "jj:choice o:adr.alternatives:none").replace(
            "jj:choice o:adr.alternatives:named-only , o:adr.alternatives:none", "jj:choice o:adr.context:missing"),
    }

    def test_text_is_identical_across_loads_and_has_no_blank_node_labels(self):
        for name, text in self.TEXTS.items():
            with self.subTest(name):
                runs = [self.validate(text).error for _ in range(3)]
                self.assertEqual(len({e.message for e in runs}), 1, runs[0].message)
                self.assertEqual(len({json.dumps(e.data["violations"]) for e in runs}), 1)
                self.assertIsNone(BLANK_LABEL.search(runs[0].message), runs[0].message)
                for violation in runs[0].data["violations"]:
                    self.assertIsNone(BLANK_LABEL.search(json.dumps(violation)), violation)

    def test_violations_are_sorted(self):
        error = self.validate(self.TEXTS["two conditions with the same problem"]).error
        keys = [(v["focus"], v["path"], v["component"], v["constraint"], v["shape"], v["value"], v["message"]) for v in error.data["violations"]]
        self.assertEqual(keys, sorted(keys))


class LoggedInputTests(GraphCase):
    """F7: what rdflib logs about an ill-typed literal is kept in the error, not printed."""

    def test_an_ill_typed_integer_leaves_stderr_clean_and_the_log_in_the_error(self):
        text = ADR_TTL.replace('jj:rank 2 ;\n    jj:verdict "yes"', f'jj:rank "abc"^^<{XSD}integer> ;\n    jj:verdict "yes"')
        tree = self.load(text)
        rdflib_logger = logging.getLogger("rdflib")
        before = (list(rdflib_logger.handlers), rdflib_logger.propagate, rdflib_logger.level)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = jev_graph.validate_tree(tree)
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(result.error.code, "QUALITY.TREE")
        self.assertTrue(result.error.data["log"])
        self.assertIn("abc", " ".join(result.error.data["log"]))
        self.assertIn("rdflib reported", result.error.message)
        self.assertEqual((list(rdflib_logger.handlers), rdflib_logger.propagate, rdflib_logger.level), before)

    def test_an_ill_typed_boolean_warning_is_kept_not_printed(self):
        tree = self.load(ADR_TTL.replace("jj:approved false", f'jj:approved "maybe"^^<{XSD}boolean>'))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = jev_graph.validate_tree(tree)
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(result.error.code, "QUALITY.TREE")
        self.assertIn("maybe", " ".join(result.error.data["log"]))


class LoadArgumentTests(GraphCase):
    """F9: a non-path argument is a typed error."""

    def test_non_path_arguments_are_input_missing(self):
        for name, value in (("None", None), ("int", 5), ("bytes", b"tree.ttl"), ("object", object()), ("list", ["a"]),
                            ("empty", ""), ("blank", "  "), ("nul byte", "a\0b"), ("directory", self.dir)):
            with self.subTest(name):
                result = jev_graph.load_tree(value)
                self.assertIsInstance(result, Err)
                self.assertEqual(result.error.code, "INPUT.MISSING")
                self.assertTrue(result.error.message)

    def test_a_pathlib_path_loads(self):
        self.assertIsInstance(jev_graph.load_tree(Path(write(self.dir, ADR_TTL))), Ok)


class PortTests(unittest.TestCase):
    """F4: compile_wave and query return typed results for every input."""

    def setUp(self):
        self.store = jev_ports.OxigraphGraphStore()
        self.tree = self.store.load_tree(str(Path(jev_graph.SHAPES_PATH).parent.parent / "questions" / "quality-adr.ttl")).value

    def test_compile_wave_is_a_result(self):
        got = self.store.compile_wave(self.tree, "wave-1")
        self.assertIsInstance(got, Ok)
        self.assertEqual(list(got.value), ["context", "alternatives", "consequences"])

    def test_an_unknown_wave_is_a_typed_err(self):
        for node_id in ("nope", "", None, 5):
            with self.subTest(node_id):
                got = self.store.compile_wave(self.tree, node_id)
                self.assertEqual(got.error.code, "VALIDATION.INPUT")

    def test_compile_wave_of_an_invalid_tree_is_the_trees_error(self):
        store = ox.Store()
        store.load(input=ADR_TTL + chain(100), format=ox.RdfFormat.TURTLE)
        self.assertEqual(self.store.compile_wave(jev_graph.TreeGraph(store, "memory"), "wave-1").error.code, "QUALITY.TREE")

    def test_query_answers_select_and_refuses_everything_else_as_a_typed_err(self):
        self.assertEqual(self.store.query("SELECT ?s WHERE { ?s ?p ?o }").value, [])
        for name, query in (("ASK", "ASK { ?s ?p ?o }"), ("CONSTRUCT", "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"),
                            ("DESCRIBE", "DESCRIBE <urn:a>"), ("syntax", "SELEKT"), ("empty", ""), ("None", None), ("int", 5),
                            ("update", "INSERT DATA { <urn:a> <urn:b> <urn:c> }")):
            with self.subTest(name):
                got = self.store.query(query)
                self.assertIsInstance(got, Err)
                self.assertEqual(got.error.code, "VALIDATION.INPUT")

    def test_record_run_refuses_what_is_not_a_quad(self):
        self.assertEqual(self.store.record_run([1]).error.code, "VALIDATION.INPUT")
        self.assertEqual(self.store.record_run(None).error.code, "VALIDATION.INPUT")


if __name__ == "__main__":
    unittest.main()
