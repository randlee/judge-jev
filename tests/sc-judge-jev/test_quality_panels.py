"""The rendered quality-tree panels must say exactly what the shipped tree files do. Offline: no model call.

The checks read the RENDERED panel (its data- attributes), not the generator's variables, and compare it with an
independent walk of the tree file: every combination of answers is run through the tree's rules and must land on
exactly one drawn path with the same verdict. A panel rendered from another tree, or edited by hand, fails.
"""
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_quality_panels as panels

REQUIRE = os.environ.get('JUDGE_JEV_REQUIRE_SC_COMPOSE') == '1'


def _list(value):
    return value if isinstance(value, list) else [value]


def verdict(tree, answers):
    """In a node the first rule that matches decides. Returns (verdict, nodes visited)."""
    node_id, visited = tree['start'], []
    while True:
        node = tree['nodes'][node_id]
        if 'verdict' in node:
            return node['verdict'], visited
        visited.append(node_id)
        for rule in node.get('next', []):
            if all(answers[q] in _list(c) for q, c in rule.get('when', {}).items()):
                node_id = rule['goto']
                break
        else:
            for rule in node['verdict_rules']:
                anyof = rule.get('any', {})
                if not anyof or any(answers[q] in _list(c) for q, c in anyof.items()):
                    return rule['verdict'], visited


def gate_questions(tree):
    found = {}
    for node_id, node in tree['nodes'].items():
        used = [q for r in node.get('next', []) for q in r.get('when', {})] + [q for r in node.get('verdict_rules', []) for q in r.get('any', {})]
        for q in dict.fromkeys(used):
            found[q] = (node_id, list(node['questions'][q]['criteria']))
    return found


def drawn_paths(panel):
    return [({c.get('data-question'): c.get('data-choices').split('|') if c.get('data-choices') else None
              for c in row if c.get('data-question')}, row.get('data-verdict'))
            for row in panel.iter('div') if row.get('data-path')]


def mismatches(tree, panel):
    """Answer combinations whose drawn path is missing, doubled or ends in the wrong verdict."""
    gates, paths, wrong = gate_questions(tree), drawn_paths(panel), []
    names = list(gates)
    for combo in itertools.product(*(gates[q][1] for q in names)):
        answers = dict(zip(names, combo))
        want, visited = verdict(tree, answers)
        hits = [v for cells, v in paths
                if all(cells[q] is None or answers[q] in cells[q] for q in names if gates[q][0] in visited)
                and all(cells[q] is None for q in names if gates[q][0] not in visited)]
        if hits != [want]:
            wrong.append((answers, want, hits))
    return wrong


class QualityPanels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not panels.sc_compose_available():
            if REQUIRE:
                raise AssertionError('JUDGE_JEV_REQUIRE_SC_COMPOSE=1 but sc-compose is unavailable')
            raise unittest.SkipTest('sc-compose is not installed')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.page = panels.page(cls.out, sorted((panels.TEMPLATES / 'examples').glob('*.json')))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'tmp'):
            cls.tmp.cleanup()

    def tree_and_panel(self, kind):
        raw = (panels.QUESTIONS / f'quality-{kind}.json').read_bytes()
        return raw, json.loads(raw), ET.parse(self.out / f'tree-{kind}.panel.xhtml').getroot()

    def test_each_panel_matches_its_tree(self):
        for kind in panels.KINDS:
            with self.subTest(kind=kind):
                raw, tree, panel = self.tree_and_panel(kind)
                self.assertEqual(panel.get('data-sha256'), hashlib.sha256(raw).hexdigest())
                drawn = {(d.get('data-node'), d.get('data-question'), c.get('data-choice'))
                         for d in panel.iter('div') if d.get('data-node') for c in d.iter('span') if c.get('data-choice') is not None}
                self.assertEqual(drawn, {(node, q, c) for q, (node, choices) in gate_questions(tree).items() for c in choices})
                self.assertEqual(mismatches(tree, panel), [])

    def test_a_changed_rule_is_caught(self):
        _, tree, panel = self.tree_and_panel('req')
        tree['nodes']['wave-1']['next'][1]['when']['checkable'] = ['no']      # "needs a measure" no longer stops
        self.assertTrue(mismatches(tree, panel))

    def test_a_hand_edited_verdict_is_caught(self):
        _, tree, panel = self.tree_and_panel('adr')
        next(row for row in panel.iter('div') if row.get('data-path') == '2').set('data-verdict', 'yes')
        self.assertTrue(mismatches(tree, panel))

    def test_every_gate_question_has_a_title(self):
        labels = json.loads((panels.TEMPLATES / 'labels.json').read_text(encoding='utf-8'))['checks']
        for kind in panels.KINDS:
            _, tree, _ = self.tree_and_panel(kind)
            self.assertEqual([q for q in gate_questions(tree) if q not in labels], [])

    def test_page_holds_every_panel_and_names_each_fixed_record(self):
        page = ET.parse(self.page).getroot()
        ids = {s.get('id') for s in page.iter('{http://www.w3.org/1999/xhtml}section')}
        self.assertEqual(ids, {'tree-req', 'tree-nfr', 'tree-adr', 'fix-req', 'fix-nfr', 'fix-adr'})


if __name__ == '__main__':
    unittest.main()
