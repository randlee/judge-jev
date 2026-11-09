"""The tree side of the graph store port (ADR-JEV-0006): a quality tree in Turtle, checked by SHACL and compiled to JSON.

No network and no Jev. ``jev_graph`` loads TTL with pyoxigraph and validates with pyshacl (a pyoxigraph store is
serialised to N-Triples and parsed into rdflib for validation only). The shipped ``quality-adr.ttl`` must say the same as
``quality-adr.json``; each SHACL rule has a failing TTL that is refused as ``QUALITY.TREE`` naming the violated
constraint, shape or path.
"""
import json
import tempfile
import unittest
from pathlib import Path

import pyoxigraph as ox

from jev_support import SKILL
import jev_graph  # noqa: E402
import jev_judge as jj  # noqa: E402
from result import Err, Ok  # noqa: E402

QUESTIONS = SKILL / "assets" / "questions"
ADR_TTL = (QUESTIONS / "quality-adr.ttl").read_text(encoding="utf-8")
ADR_JSON = json.loads((QUESTIONS / "quality-adr.json").read_text(encoding="utf-8"))

# A branch tree: wave-1 goes to wave-2 on "bad", to the leaf otherwise; wave-2 judges per statement.
BRANCH_TTL = """\
@prefix jj: <urn:judge-jev:ontology#> .
@prefix t:  <urn:judge-jev:tree:> .
@prefix q:  <urn:judge-jev:question:> .
@prefix o:  <urn:judge-jev:option:> .

t:b a jj:Tree ; jj:id "b" ; jj:kind "req" ; jj:start t:b:wave-1 ;
    jj:node t:b:wave-1 , t:b:wave-2 , t:b:done .

t:b:wave-1 a jj:Wave ; jj:id "wave-1" ; jj:asks q:b.size ;
    jj:rule t:b:wave-1:r1 , t:b:wave-1:r2 .
t:b:wave-1:r1 a jj:BranchRule ; jj:rank 1 ; jj:goto t:b:wave-2 ;
    jj:whenAll [ a jj:Condition ; jj:question q:b.size ; jj:choice o:b.size:big , o:b.size:huge ] .
t:b:wave-1:r2 a jj:BranchRule ; jj:rank 2 ; jj:goto t:b:done .

t:b:wave-2 a jj:Wave ; jj:id "wave-2" ; jj:asks q:b.size ;
    jj:per "statement" ; jj:statements "requirement_statement.statements" ; jj:modal "MustNot" , "Must" ;
    jj:rule t:b:wave-2:r1 , t:b:wave-2:r2 .
t:b:wave-2:r1 a jj:VerdictRule ; jj:rank 1 ; jj:verdict "no" ;
    jj:whenAll [ a jj:Condition ; jj:question q:b.size ; jj:choice o:b.size:huge ] .
t:b:wave-2:r2 a jj:VerdictRule ; jj:rank 2 ; jj:verdict "yes" .

t:b:done a jj:Leaf ; jj:id "done" ; jj:verdict "yes" .

q:b.size a jj:Question ; jj:id "size" ; jj:rank 1 ; jj:instructions "How big?" ;
    jj:option o:b.size:small , o:b.size:big , o:b.size:huge .
o:b.size:small a jj:Option ; jj:rank 1 ; jj:label "small" ; jj:criterion "Small." .
o:b.size:big a jj:Option ; jj:rank 2 ; jj:label "big" ; jj:criterion "Big." .
o:b.size:huge a jj:Option ; jj:rank 3 ; jj:label "huge" ; jj:criterion "Huge." .
"""


def write(directory: str, text: str, name: str = "tree.ttl") -> str:
    path = Path(directory) / name
    path.write_bytes(text.encode("utf-8"))  # exact bytes: write_text would turn \n into \r\n on Windows
    return str(path)


class GraphCase(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.dir = scratch.name

    def load(self, text: str):
        loaded = jev_graph.load_tree(write(self.dir, text))
        self.assertIsInstance(loaded, Ok, getattr(loaded, "error", None))
        return loaded.value

    def validate(self, text: str):
        return jev_graph.validate_tree(self.load(text))

    def assertRefused(self, text: str, *, constraint: str = "", path: str = "", shape: str = ""):
        """The TTL is refused as QUALITY.TREE with a violation of the named constraint, shape or path."""
        result = self.validate(text)
        self.assertIsInstance(result, Err, "the tree conformed but must be refused")
        self.assertEqual(result.error.code, "QUALITY.TREE")
        found = result.error.data["violations"]
        wanted = {"constraint": constraint, "path": path, "shape": shape}
        hits = [v for v in found if all(v[k] == w for k, w in wanted.items() if w)]
        self.assertTrue(hits, f"no violation with {wanted}; got {found}")
        for key in ("constraint", "shape", "path"):
            if wanted[key]:
                self.assertIn(wanted[key], result.error.message)
        self.assertTrue(all(v["focus"] and v["message"] for v in hits))
        return hits


class ShippedTreeTests(GraphCase):
    def test_quality_adr_ttl_passes_shacl(self):
        loaded = jev_graph.load_tree(str(QUESTIONS / "quality-adr.ttl"))
        self.assertIsInstance(loaded, Ok)
        self.assertEqual(jev_graph.validate_tree(loaded.value), Ok(None))

    def test_ttl_says_what_the_json_tree_says(self):
        tree = jev_graph.load_tree(str(QUESTIONS / "quality-adr.ttl")).value
        converted = jev_graph.tree_to_quality_json(tree)
        for key in ("id", "kind", "start", "nodes"):
            self.assertEqual(converted[key], ADR_JSON[key], key)
        self.assertEqual(converted, ADR_JSON)
        self.assertEqual(json.dumps(converted, sort_keys=False), json.dumps(ADR_JSON, sort_keys=False))

    def test_every_shipped_ttl_passes_shacl_and_compiles_to_its_json_tree(self):
        for kind in ("adr", "req", "nfr"):
            with self.subTest(kind):
                loaded = jev_graph.load_tree(str(QUESTIONS / f"quality-{kind}.ttl"))
                self.assertIsInstance(loaded, Ok)
                self.assertEqual(jev_graph.validate_tree(loaded.value), Ok(None))
                expected = json.loads((QUESTIONS / f"quality-{kind}.json").read_text(encoding="utf-8"))
                converted = jev_graph.tree_to_quality_json(loaded.value)
                self.assertEqual(converted, expected)
                self.assertEqual(json.dumps(jev_graph.compile_wave(loaded.value, "wave-1"), sort_keys=False),
                                 json.dumps(expected["nodes"]["wave-1"]["questions"], sort_keys=False))

    def test_compile_wave_is_the_json_waves_questions_object_in_order(self):
        tree = jev_graph.load_tree(str(QUESTIONS / "quality-adr.ttl")).value
        compiled = jev_graph.compile_wave(tree, "wave-1")
        expected = ADR_JSON["nodes"]["wave-1"]["questions"]
        self.assertEqual(json.dumps(compiled, sort_keys=False), json.dumps(expected, sort_keys=False))
        self.assertEqual(list(compiled), ["context", "alternatives", "consequences"])

    def test_compile_wave_refuses_an_unknown_node(self):
        tree = self.load(BRANCH_TTL)
        with self.assertRaises(KeyError):
            jev_graph.compile_wave(tree, "nope")
        with self.assertRaises(KeyError):
            jev_graph.compile_wave(tree, "done")  # a leaf asks nothing

    def test_the_converted_json_runs_through_the_existing_tree_loader(self):
        for name, text in (("adr", ADR_TTL), ("branch", BRANCH_TTL)):
            with self.subTest(name):
                tree = self.load(text)
                self.assertEqual(jev_graph.validate_tree(tree), Ok(None))
                path = write(self.dir, json.dumps(jev_graph.tree_to_quality_json(tree)), f"{name}.json")
                loaded = jj.load_quality_tree("adr", path)
                self.assertIsInstance(loaded, Ok, getattr(loaded, "error", None))

    def test_questions_are_resources_with_iris(self):
        tree = jev_graph.load_tree(str(QUESTIONS / "quality-adr.ttl")).value
        rows = list(tree.store.query(
            "PREFIX jj: <urn:judge-jev:ontology#> SELECT ?q WHERE { ?q a jj:Question } ORDER BY ?q"))
        self.assertEqual([r["q"].value for r in rows],
                         ["urn:judge-jev:question:adr.alternatives", "urn:judge-jev:question:adr.consequences",
                          "urn:judge-jev:question:adr.context"])


class ConversionTests(GraphCase):
    def test_branch_tree_conforms_and_converts_to_next_rules_and_a_leaf(self):
        tree = self.load(BRANCH_TTL)
        self.assertEqual(jev_graph.validate_tree(tree), Ok(None))
        nodes = jev_graph.tree_to_quality_json(tree)["nodes"]
        self.assertEqual(nodes["wave-1"]["next"], [{"when": {"size": ["big", "huge"]}, "goto": "wave-2"}, {"goto": "done"}])
        self.assertEqual(nodes["done"], {"verdict": "yes"})
        self.assertEqual(list(nodes["wave-2"]), ["per", "statements", "modals", "questions", "verdict_rules"])
        self.assertEqual(nodes["wave-2"]["modals"], ["Must", "MustNot"])
        self.assertEqual(nodes["wave-2"]["verdict_rules"], [{"all": {"size": "huge"}, "verdict": "no"}, {"verdict": "yes"}])
        self.assertEqual(list(nodes["wave-1"]["questions"]["size"]["criteria"]), ["small", "big", "huge"])


class ShaclRuleTests(GraphCase):
    def test_tree_start_must_exist(self):
        self.assertRefused(ADR_TTL.replace("    jj:start t:quality-adr:wave-1 ;\n", ""), path="jj:start")

    def test_tree_has_exactly_one_start(self):
        self.assertRefused(ADR_TTL.replace("jj:start t:quality-adr:wave-1 ;",
                                           "jj:start t:quality-adr:wave-1 , t:quality-adr:wave-2 ;"), path="jj:start")

    def test_start_must_be_a_node_of_the_tree(self):
        self.assertRefused(ADR_TTL.replace("jj:start t:quality-adr:wave-1", "jj:start t:quality-adr:wave-9"),
                           constraint="jjs:TreeStartIsNode")

    def test_a_file_defines_exactly_one_tree(self):
        result = self.validate(ADR_TTL + "\nt:other a jj:Tree .\n")
        self.assertEqual(result.error.code, "QUALITY.TREE")
        self.assertIn("exactly one jj:Tree", result.error.message)

    def test_node_ids_are_unique_in_a_tree(self):
        text = BRANCH_TTL.replace('jj:id "done"', 'jj:id "wave-1"')
        self.assertRefused(text, constraint="jjs:TreeNodeIdsUnique")

    def test_wave_asks_at_least_one_question(self):
        self.assertRefused(ADR_TTL.replace("    jj:asks q:adr.context , q:adr.alternatives , q:adr.consequences ;\n", ""),
                           path="jj:asks")

    def test_wave_has_at_least_one_rule(self):
        self.assertRefused(ADR_TTL.replace("    jj:rule t:quality-adr:wave-1:rule-1 , t:quality-adr:wave-1:rule-2 .",
                                           "    jj:per \"statement\" ."), path="jj:rule")

    def test_a_waves_rules_are_all_one_kind(self):
        text = BRANCH_TTL.replace("t:b:wave-1:r2 a jj:BranchRule ; jj:rank 2 ; jj:goto t:b:done .",
                                  't:b:wave-1:r2 a jj:VerdictRule ; jj:rank 2 ; jj:verdict "yes" .')
        self.assertRefused(text, constraint="jjs:WaveRulesSameKind")

    def test_a_question_has_instructions(self):
        text = ADR_TTL.replace('    jj:instructions "`item.text` is one architecture decision record as JSON. Does it name the alternatives considered?" ;\n', "")
        self.assertRefused(text, path="jj:instructions")

    def test_a_question_has_non_empty_instructions(self):
        text = ADR_TTL.replace("Does it name the alternatives considered?", "  ").replace("`item.text` is one architecture decision record as JSON.", "")
        self.assertRefused(text, path="jj:instructions")

    def test_a_question_has_at_least_two_options(self):
        text = ADR_TTL.replace("jj:option o:adr.context:problem-and-forces , o:adr.context:background-only , o:adr.context:missing .",
                               "jj:option o:adr.context:problem-and-forces .")
        self.assertRefused(text, path="jj:option")

    def test_a_question_has_at_most_255_options(self):
        extra = "".join(f'o:adr.context:extra{i} a jj:Option ; jj:rank {10 + i} ; jj:label "extra {i}" ; jj:criterion "Extra." .\n'
                        for i in range(253))
        names = " , ".join(f"o:adr.context:extra{i}" for i in range(253))
        text = ADR_TTL.replace("o:adr.context:background-only , o:adr.context:missing .",
                               f"o:adr.context:background-only , o:adr.context:missing , {names} .") + extra
        hits = self.assertRefused(text, path="jj:option")
        self.assertIn("2 to 255", hits[0]["message"])

    def test_exactly_255_options_conform(self):
        names = " , ".join(f"o:adr.context:extra{i}" for i in range(252))
        extra = "".join(f'o:adr.context:extra{i} a jj:Option ; jj:rank {10 + i} ; jj:label "extra {i}" ; jj:criterion "Extra." .\n'
                        for i in range(252))
        text = ADR_TTL.replace("o:adr.context:background-only , o:adr.context:missing .",
                               f"o:adr.context:background-only , o:adr.context:missing , {names} .") + extra
        self.assertEqual(jev_graph.validate_tree(self.load(text)), Ok(None))

    def test_an_option_has_a_label(self):
        self.assertRefused(ADR_TTL.replace('    jj:label "problem and forces" ;\n', ""), path="jj:label")

    def test_an_option_has_a_non_empty_criterion(self):
        self.assertRefused(ADR_TTL.replace('jj:criterion "Names only benefits. Fix: add the costs."', 'jj:criterion ""'),
                           path="jj:criterion")

    def test_an_option_has_a_criterion(self):
        self.assertRefused(ADR_TTL.replace('    jj:criterion "Names benefits and costs." .', "    jj:rank 1 ."), path="jj:criterion")

    def test_a_conditions_choice_is_an_option_of_its_question(self):
        text = ADR_TTL.replace("jj:choice o:adr.context:background-only , o:adr.context:missing",
                               "jj:choice o:adr.context:background-only , o:adr.alternatives:none")
        self.assertRefused(text, constraint="jjs:ConditionChoiceIsOptionOfQuestion")

    def test_a_conditions_question_is_asked_by_the_same_wave(self):
        text = ADR_TTL.replace("jj:asks q:adr.context , q:adr.alternatives , q:adr.consequences ;",
                               "jj:asks q:adr.context , q:adr.alternatives ;")
        self.assertRefused(text, constraint="jjs:ConditionQuestionAskedByWave")

    def test_a_branch_rules_goto_is_a_node_of_the_same_tree(self):
        text = BRANCH_TTL.replace("jj:goto t:b:done", "jj:goto t:b:elsewhere") + \
            't:b:elsewhere a jj:Leaf ; jj:id "elsewhere" ; jj:verdict "no" .\n'
        self.assertRefused(text, constraint="jjs:BranchGotoInTree")

    def test_a_branch_rules_goto_must_exist(self):
        self.assertRefused(BRANCH_TTL.replace("jj:goto t:b:done", "jj:goto t:b:nowhere"), constraint="jjs:BranchGotoInTree")

    def test_ranks_are_integers(self):
        self.assertRefused(ADR_TTL.replace("jj:rank 2 ;\n    jj:verdict \"yes\"", 'jj:rank "2.5"^^<http://www.w3.org/2001/XMLSchema#decimal> ;\n    jj:verdict "yes"'),
                           path="jj:rank")
        self.assertRefused(ADR_TTL.replace("jj:id \"alternatives\" ;\n    jj:rank 2", 'jj:id "alternatives" ;\n    jj:rank "second"'),
                           path="jj:rank")

    def test_rule_ranks_are_unique_per_wave(self):
        text = ADR_TTL.replace('jj:rank 2 ;\n    jj:verdict "yes"', 'jj:rank 1 ;\n    jj:verdict "yes"')
        self.assertRefused(text, constraint="jjs:WaveRuleRanksUnique")

    def test_question_ranks_are_unique_per_wave(self):
        text = ADR_TTL.replace('jj:id "alternatives" ;\n    jj:rank 2', 'jj:id "alternatives" ;\n    jj:rank 1')
        self.assertRefused(text, constraint="jjs:WaveQuestionRanksUnique")

    def test_the_highest_rank_rule_has_no_conditions(self):
        text = ADR_TTL.replace('jj:rank 2 ;\n    jj:verdict "yes" .',
                               'jj:rank 2 ;\n    jj:verdict "yes" ;\n    jj:whenAny [ a jj:Condition ; jj:question q:adr.context ; jj:choice o:adr.context:missing ] .')
        self.assertRefused(text, constraint="jjs:WaveLastRuleUnconditional")

    def test_the_highest_rank_is_the_last_not_the_first_listed(self):
        text = ADR_TTL.replace('jj:rank 1 ;\n    jj:verdict "no"', 'jj:rank 3 ;\n    jj:verdict "no"')  # the conditional rule is now last
        self.assertRefused(text, constraint="jjs:WaveLastRuleUnconditional")

    def test_a_leaf_has_only_a_verdict(self):
        for extra in ("jj:asks q:b.size", 'jj:per "statement"', "jj:rule t:b:wave-1:r2"):
            with self.subTest(extra):
                self.assertRefused(BRANCH_TTL.replace('jj:id "done" ;', f'jj:id "done" ; {extra} ;'), shape="jjs:LeafShape")

    def test_a_leaf_needs_a_verdict(self):
        self.assertRefused(BRANCH_TTL.replace('t:b:done a jj:Leaf ; jj:id "done" ; jj:verdict "yes" .', 't:b:done a jj:Leaf ; jj:id "done" .'),
                           path="jj:verdict")

    def test_no_cycle_through_goto(self):
        text = BRANCH_TTL.replace("t:b:wave-2:r2 a jj:VerdictRule ; jj:rank 2 ; jj:verdict \"yes\" .",
                                  "t:b:wave-2:r2 a jj:BranchRule ; jj:rank 2 ; jj:goto t:b:wave-1 .") \
            .replace("t:b:wave-2:r1 a jj:VerdictRule ; jj:rank 1 ; jj:verdict \"no\" ;\n    jj:whenAll [ a jj:Condition ; jj:question q:b.size ; jj:choice o:b.size:huge ] .",
                     "t:b:wave-2:r1 a jj:BranchRule ; jj:rank 1 ; jj:goto t:b:done ;\n    jj:whenAll [ a jj:Condition ; jj:question q:b.size ; jj:choice o:b.size:huge ] .")
        hits = self.assertRefused(text, constraint="jjs:WaveNoCycle")
        self.assertEqual({h["focus"] for h in hits}, {"urn:judge-jev:tree:b:wave-1", "urn:judge-jev:tree:b:wave-2"})

    def test_a_wave_that_goes_to_itself_is_a_cycle(self):
        text = BRANCH_TTL.replace("jj:goto t:b:done", "jj:goto t:b:wave-1")
        self.assertRefused(text, constraint="jjs:WaveNoCycle")

    def test_a_per_statement_wave_names_its_statements(self):
        self.assertRefused(BRANCH_TTL.replace('jj:statements "requirement_statement.statements" ;', ""),
                           constraint="jjs:WavePerNeedsStatements")

    def test_statements_without_per_are_refused(self):
        self.assertRefused(BRANCH_TTL.replace('t:b:wave-1 a jj:Wave ; jj:id "wave-1" ;', 't:b:wave-1 a jj:Wave ; jj:id "wave-1" ; jj:modal "Must" ;'),
                           constraint="jjs:WaveStatementsNeedPer")

    def test_question_ids_are_unique_per_wave(self):
        text = BRANCH_TTL.replace("jj:asks q:b.size ;\n    jj:rule t:b:wave-1:r1", "jj:asks q:b.size , q:b.other ;\n    jj:rule t:b:wave-1:r1") + \
            'q:b.other a jj:Question ; jj:id "size" ; jj:rank 2 ; jj:instructions "Other?" ; jj:option o:b.size:small , o:b.size:big .\n'
        self.assertRefused(text, constraint="jjs:WaveQuestionIdsUnique")


class MalformedTests(GraphCase):
    def test_turtle_that_does_not_parse_is_input_malformed(self):
        result = jev_graph.load_tree(write(self.dir, "t:x a jj:Tree ."))
        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, "INPUT.MALFORMED")

    def test_a_missing_file_is_input_missing(self):
        self.assertEqual(jev_graph.load_tree(str(Path(self.dir) / "none.ttl")).error.code, "INPUT.MISSING")

    def test_non_utf8_is_input_malformed(self):
        path = Path(self.dir) / "bad.ttl"
        path.write_bytes(b"\xff\xfe\x00")
        self.assertEqual(jev_graph.load_tree(str(path)).error.code, "INPUT.MALFORMED")


class DigestTests(GraphCase):
    def digest(self, text: str) -> str:
        return jev_graph.tree_digest(self.load(text)).value

    def test_digest_is_a_sha256_hex(self):
        d = self.digest(ADR_TTL)
        self.assertRegex(d, r"^[0-9a-f]{64}$")
        self.assertEqual(d, self.digest(ADR_TTL))

    def test_digest_ignores_triple_order_blank_node_names_prefixes_and_whitespace(self):
        base = self.digest(ADR_TTL)
        store = self.load(ADR_TTL).store
        lines = store.dump(format=ox.RdfFormat.N_TRIPLES, from_graph=ox.DefaultGraph()).decode("utf-8").splitlines()
        reordered = "\n".join(reversed(lines)) + "\n"
        self.assertEqual(self.digest(reordered), base)
        renamed = reordered.replace("_:", "_:renamed")
        self.assertNotEqual(renamed, reordered)
        self.assertEqual(self.digest(renamed), base)
        prefixes = ADR_TTL.replace("jj:", "jx:").replace("q:", "qq:").replace("\n    ", "\n\n\t   ") + "\n\n# trailing comment\n"
        self.assertEqual(self.digest(prefixes), base)

    def test_digest_changes_when_a_question_text_changes(self):
        base = self.digest(ADR_TTL)
        self.assertNotEqual(self.digest(ADR_TTL.replace("Does it name the alternatives considered?", "Does it list the alternatives considered?")), base)
        self.assertNotEqual(self.digest(ADR_TTL.replace("Names benefits and costs.", "Names benefits and costs, both.")), base)
        self.assertNotEqual(self.digest(ADR_TTL.replace('jj:verdict "no"', 'jj:verdict "fail"')), base)

    def test_digest_differs_between_trees(self):
        self.assertNotEqual(self.digest(ADR_TTL), self.digest(BRANCH_TTL))


if __name__ == "__main__":
    unittest.main()
