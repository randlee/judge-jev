"""Offline checks for example routing and diagrams; no model, clock, or timing assertions."""
import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import decision_examples as examples
import render_tree_graph as diagrams


def record(rid, *statements):
    return {'id': rid, 'title': rid, 'requirement_statement': {'statements': list(statements)},
            'decision': {'text': 'Use the existing interface.'}, 'context': {'text': 'A problem.'},
            'alternatives': {'text': 'Another interface.'}, 'consequences': {'text': 'A cost.'}, 'rationale': 'One interface.'}


class RecordInputs(unittest.TestCase):
    def test_selected_diagnostic_refuses_before_any_send(self):
        index = {'requirements': [record('REQ-T-0001'), record('NFR-T-0001')], 'decisions': [],
                 'diagnostics': {'issues': [{'id': 'REQ-T-0001', 'rule': 'MODAL_MISMATCH'}]}}
        with mock.patch.object(examples.subprocess, 'run', side_effect=AssertionError('must not send')):
            with self.assertRaisesRegex(ValueError, 'import diagnostic'):
                examples.select_records(index, ['REQ-T-0001'])
            self.assertEqual(examples.select_records(index, ['NFR-T-0001'])[0][0], 'nfr')

    def test_statement_indexes_are_raptor_positions_and_must_not_is_included(self):
        source = record('REQ-T-0001', {'modal': 'Must', 'text': 'MUST read\nthe file.'},
                        {'modal': 'Should', 'text': 'SHOULD help.'}, {'modal': 'MustNot', 'text': 'MUST NOT write.'})
        items = examples.items('req', source)
        self.assertEqual([item['id'] for item in items], ['REQ-T-0001.s1', 'REQ-T-0001.s3'])
        self.assertEqual(json.loads(items[0]['text'])['record'], source)
        self.assertEqual(json.loads(items[1]['text'])['statement']['modal'], 'MustNot')

    def test_adr_uses_whole_record_and_literal_sections(self):
        source = record('ADR-T-0001')
        item, = examples.items('adr', source)
        self.assertEqual(json.loads(item['text']), source)
        tree, terms = examples.example_tree('adr', item, .8)
        self.assertEqual(terms, ['context', 'decision', 'rationale', 'alternatives', 'consequences', 'none'])
        self.assertEqual(set(tree['nodes']['gates']['questions']), {'context', 'alternatives', 'consequences'})

    def test_quality_rules_use_choices_and_first_match_not_confidence(self):
        rules = [{'when': {'term': 'no'}, 'goto': 'no'},
                 {'when': {'obligations': ['2', '3']}, 'goto': 'wave-2'}, {'goto': 'yes'}]
        self.assertEqual(examples.selected_rule(rules, [{'term': 'yes', 'obligations': '1'},
                                                     {'term': 'no', 'obligations': '2'}]), 1)
        self.assertEqual(examples.selected_rule(rules, [{'term': 'yes', 'obligations': '2'}]), 2)
        self.assertEqual(examples.selected_rule(rules, [{'term': 'yes', 'obligations': '1'}]), 3)

    def test_quality_diagram_refuses_a_tree_that_differs_from_the_commands_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / 'tree.json'
            tree.write_text('{"id":"captured-tree"}')
            result = {'tree': {'path': str(tree), 'id': 'captured-tree',
                               'sha256': hashlib.sha256(tree.read_bytes()).hexdigest()}}
            self.assertEqual(examples.quality_tree(result)['id'], 'captured-tree')
            tree.write_text('{"id":"changed-tree"}')
            with self.assertRaisesRegex(ValueError, 'recorded digest'):
                examples.quality_tree(result)

    def test_replay_does_not_invoke_any_decision_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            saved = tmp / 'saved.json'
            value = {'example': 'decidr-pipeline', 'mode': 'live', 'exit_code': 0, 'views': []}
            saved.write_text(json.dumps(value))
            argv = ['run.py', '--output', str(tmp / 'replay'), '--replay', str(saved)]
            with mock.patch.object(sys, 'argv', argv), mock.patch.object(examples.shutil, 'which', return_value='/controlled'), \
                 mock.patch.object(examples.subprocess, 'run', side_effect=AssertionError('must not send')), \
                 mock.patch('render_decision_report.render_report') as render:
                self.assertEqual(examples.main('decidr-pipeline'), 0)
            self.assertEqual(json.loads((tmp / 'replay/run.json').read_text()), value)
            self.assertTrue(render.call_args.kwargs['replay'])


@unittest.skipUnless(shutil.which('jq'), 'jq is required to exercise the example filter')
class JqRouting(unittest.TestCase):
    def route(self, value, tree):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, payload in (('item', {'id': 'ADR-T-0001', 'text': '{}'}),
                                  ('terms', ['context', 'none']), ('tree', tree)):
                (tmp / (name + '.json')).write_text(json.dumps(payload))
            argv = ['jq', '-c', '--argjson', 'bar', '.8']
            for name in ('item', 'terms', 'tree'):
                argv.extend(['--slurpfile', name, str(tmp / (name + '.json'))])
            argv.extend(['-f', str(examples.SKILL / 'scripts/next.jq')])
            return subprocess.run(argv, input=json.dumps(value), text=True, capture_output=True)

    def test_adr_policy_and_confidence_boundary(self):
        item, = examples.items('adr', record('ADR-T-0001'))
        tree, _ = examples.example_tree('adr', item, .8)
        answers = {p['id']: {'type': 'choice', 'choice': p['pass'], 'confidence': .8}
                   for p in tree['nodes']['gates']['policy']}
        value = {'ok': True, 'value': {'answers': answers}}
        self.assertEqual(json.loads(self.route(value, tree).stdout)['verdict'], 'yes')
        answers['context']['confidence'] = .79
        continued = json.loads(self.route(value, tree).stdout)
        self.assertEqual(continued['state']['gate']['question'], 'context')
        self.assertEqual(continued['questions'], tree['nodes']['which-part']['questions'])
        answers['context']['confidence'] = .95
        answers['context']['choice'] = 'background only'
        self.assertEqual(json.loads(self.route(value, tree).stdout)['state']['gate']['cause'], 'choice')

    def test_error_and_missing_answers_emit_no_request(self):
        item, = examples.items('adr', record('ADR-T-0001'))
        tree, _ = examples.example_tree('adr', item, .8)
        for value in ({'ok': False, 'error': {'id': 'controlled.failure'}}, {'ok': True, 'value': {'answers': {}}}):
            checked = self.route(value, tree)
            self.assertNotEqual(checked.returncode, 0)
            self.assertEqual(checked.stdout, '')
            self.assertTrue(checked.stderr)


class DiagramGraph(unittest.TestCase):
    def test_all_branches_and_ordered_fallthrough_survive_both_formats(self):
        tree = {'id': 'two-waves', 'start': 'first', 'nodes': {
            'first': {'questions': {'q': {'criteria': {'a': 'A', 'b': 'B'}}},
                      'next': [{'when': {'q': 'a'}, 'goto': 'yes'}, {'goto': 'second'}]},
            'second': {'questions': {'r': {'criteria': {'x': 'X', 'y': 'Y'}}},
                       'verdict_rules': [{'any': {'r': 'x'}, 'verdict': 'no'}, {'verdict': 'yes'}]},
            'yes': {'verdict': 'yes'}}}
        result = {'path': ['first', 'second'], 'verdict': 'yes',
                  'waves': [{'node': 'first', 'rule_position': 2}, {'node': 'second', 'rule_position': 2}]}
        nodes, edges, active = diagrams.graph(tree, result)
        self.assertIn(('first__r1', 'second', 'no'), edges)
        self.assertIn(('second__r1', 'verdict_no', 'yes'), edges)
        self.assertIn(('first__r1', 'second'), active)
        self.assertNotIn(('first__r1', 'yes'), active)
        for fmt in ('mmd', 'd2'):
            source = diagrams.render(tree, fmt, result)
            self.assertIn('Verdict: no', source)
            self.assertIn('Verdict: yes', source)
        tree['nodes']['first']['next'][0]['goto'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'unknown target'):
            diagrams.graph(tree)


if __name__ == '__main__':
    unittest.main()
