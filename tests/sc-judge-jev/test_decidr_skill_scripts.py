"""Deterministic CLI checks for all five skill helpers, with a logging decidr stub."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'plugins/sc-judge-jev/skills/walking-decidr-trees/scripts'
sys.path.insert(0, str(ROOT / 'scripts'))
import decision_examples as examples


@unittest.skipUnless(shutil.which('bash') and shutil.which('jq'), 'Bash and jq are required for the pipeline helpers')
class SkillHelpers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'calls.jsonl'
        handler = self.root / 'stub.py'
        handler.write_text('''import json,os,sys
request=json.load(sys.stdin)
with open(os.environ['CALL_LOG'],'a',encoding='utf-8') as log:
    log.write(json.dumps({'argv':sys.argv[1:],'request':request})+'\\n')
response=os.environ['STUB_RESPONSE']
if 'STUB_GATES' in os.environ:
    response=os.environ['STUB_DIAGNOSTIC'] if 'which_part' in request['questions'] else os.environ['STUB_GATES']
print(response)
sys.exit(int(os.environ.get('STUB_EXIT','0')))
''')
        stub = self.root / 'decidr'
        stub.write_text('#!/usr/bin/env bash\n"$STUB_PYTHON" "$STUB_HANDLER" "$@"\n')
        stub.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ['PATH'],
                        CALL_LOG=str(self.log), STUB_PYTHON=Path(sys.executable).as_posix(),
                        STUB_HANDLER=handler.as_posix(), STUB_RESPONSE='{"ok":true,"value":{}}')
        for name in ('SC_PROJECT', 'DECIDR_AGENT_ROLE'):
            self.env.pop(name, None)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def guard(self, text, *args):
        return subprocess.run(['bash', (SCRIPTS / 'send-next.sh').as_posix(), *args],
                              input=text, text=True, capture_output=True, env=self.env)

    def verdict(self, value):
        return subprocess.run(['jq', '-c', '-f', str(SCRIPTS / 'verdict.jq')],
                              input=json.dumps(value), text=True, capture_output=True, env=self.env)

    def test_empty_and_leaf_inputs_make_zero_decidr_calls_including_no_newline(self):
        leaf = {'verdict': 'yes', 'stage': 'gates', 'item': 'REQ-T.s1'}
        for text in ('', json.dumps(leaf), json.dumps(leaf) + '\n'):
            with self.subTest(text=text):
                completed = self.guard(text, 'jev')
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout) if completed.stdout else None, leaf if text else None)
                self.assertEqual(self.calls(), [])

    def test_newline_free_request_is_sent_once_with_argument_overrides(self):
        self.env.update(SC_PROJECT='env-project', DECIDR_AGENT_ROLE='env-role')
        request = {'questions': {'q': {'type': 'choice'}}, 'state': {'item': 'controlled'}}
        completed = self.guard(json.dumps(request), 'haiku', '--project', 'chosen-project', '--agent-role', 'chosen-role')
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.calls(), [{'argv': ['send', '--project', 'chosen-project', '--agent-role', 'chosen-role', '--model', 'haiku'], 'request': request}])

    def test_request_uses_environment_and_preserves_native_error_and_exit(self):
        self.env.update(SC_PROJECT='env-project', DECIDR_AGENT_ROLE='env-role', STUB_EXIT='1',
                        STUB_RESPONSE='{"ok":false,"error":{"id":"controlled.failure"}}')
        completed = self.guard('{"questions":{}}\n', 'jev')
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)['error']['id'], 'controlled.failure')
        self.assertEqual(self.calls()[0]['argv'], ['send', '--project', 'env-project', '--agent-role', 'env-role', '--model', 'jev'])

    def test_missing_request_configuration_and_malformed_routes_make_no_calls(self):
        for text in ('{"questions":{}}', '{"unexpected":true}', 'not JSON'):
            with self.subTest(text=text):
                completed = self.guard(text, 'jev')
                self.assertNotEqual(completed.returncode, 0)
                self.assertTrue(completed.stderr)
                self.assertEqual(self.calls(), [])

    def test_actual_example_pipeline_uses_two_models_and_the_configured_guard(self):
        gates = {key: {'type': 'choice', 'choice': choice, 'confidence': confidence}
                 for key, choice, confidence in (('obligations', '1', .9), ('term', 'yes', .7), ('checkable', 'yes', .9))}
        self.env['STUB_GATES'] = json.dumps({'ok': True, 'value': {'answers': gates}})
        answer = {'type': 'choice', 'choice': 'Cancel', 'confidence': .2,
                  'probabilities': {'Cancel': .5, 'none': .5}}
        self.env['STUB_DIAGNOSTIC'] = json.dumps({'ok': True, 'value': {'model': 'controlled-model', 'answers': {'which_part': answer}}})
        source = {'id': 'REQ-T-0001', 'title': 'Cancel', 'requirement_statement': {
            'statements': [{'modal': 'Must', 'text': 'The CLI MUST cancel the `Cancel`.'}]}}
        with mock.patch.dict(os.environ, self.env, clear=True):
            views, commands, code = examples.pipeline_views([('req', source)], self.root, .8, 'haiku', 'jev')
        self.assertEqual(code, 0, commands)
        self.assertEqual(views[0]['path'], ['gates', 'which-part', 'review'])
        self.assertEqual(views[0]['raw']['boundaries']['verdict']['which_part'], 'none')
        calls = self.calls()
        self.assertEqual(len(calls), 2)
        self.assertEqual([call['argv'][call['argv'].index('--model') + 1] for call in calls], ['haiku', 'jev'])
        self.assertTrue(all(call['argv'][call['argv'].index('--project') + 1] == 'decidr-question-tree' for call in calls))
        self.assertEqual(set(calls[1]['request']['questions']), {'which_part'})
        self.assertIn(answer['choice'], calls[1]['request']['questions']['which_part']['criteria'])

    def test_verdict_passes_a_leaf_and_surfaces_second_stage_errors(self):
        leaf = {'verdict': 'yes', 'stage': 'gates', 'item': 'REQ-T.s1'}
        self.assertEqual(json.loads(self.verdict(leaf).stdout), leaf)
        for value in ({'ok': False, 'error': {'id': 'controlled.failure'}},
                      {'ok': True, 'value': {'answers': {}}}):
            checked = self.verdict(value)
            self.assertNotEqual(checked.returncode, 0)
            self.assertEqual(checked.stdout, '')
            self.assertTrue(checked.stderr)

    def test_verdict_reports_a_top_tie_with_none_without_rewriting_the_model_choice(self):
        answer = {'type': 'choice', 'choice': 'Cancel', 'confidence': .17,
                  'probabilities': {'Cancel': .4, 'none': .4, 'cancel': .2}}
        value = {'ok': True, 'value': {'model': 'controlled-model', 'answers': {'which_part': answer}}}
        verdict = json.loads(self.verdict(value).stdout)
        self.assertEqual((verdict['which_part'], verdict['model_choice'], verdict['tied_with_none']), ('none', 'Cancel', True))
        self.assertEqual(verdict['confidence'], .17)
        answer['probabilities'] = {'Cancel': .5, 'none': .3, 'cancel': .2}
        verdict = json.loads(self.verdict(value).stdout)
        self.assertEqual((verdict['which_part'], verdict['tied_with_none']), ('Cancel', False))
        answer['confidence'] = -1
        self.assertNotEqual(self.verdict(value).returncode, 0)

    def test_prepare_preserves_whole_record_and_refuses_overwrite_or_wrong_input(self):
        record = '## REQ-SAG-0104: Cancel token\n\nDefinitions: one cancellation signal.\n'
        record += '\n'.join('- ' + line for line in ('The crate MUST provide Cancel.', 'An operation MUST hold Cancel.',
                                                   'The CLI MUST cancel Cancel.', 'Python MUST cancel Cancel.'))
        source = self.root / 'record.md'; source.write_text(record)
        output = self.root / 'prepared'
        argv = [sys.executable, str(SCRIPTS / 'prepare.py'), str(source), str(output)]
        completed = subprocess.run(argv, text=True, capture_output=True, env=self.env)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        request = json.loads((output / 'request.json').read_text())
        payload = json.loads(request['state']['item']['text'])
        self.assertEqual(payload, {'statement': {'index': 3, 'text': 'The CLI MUST cancel Cancel.'}, 'record': record})
        self.assertEqual(set(request['questions']), {'obligations', 'term', 'checkable'})
        before = (output / 'request.json').read_bytes()
        self.assertNotEqual(subprocess.run(argv, capture_output=True, env=self.env).returncode, 0)
        self.assertEqual((output / 'request.json').read_bytes(), before)
        source.write_text('## Wrong record\n- The CLI MUST stop.')
        argv[-1] = str(self.root / 'invalid')
        self.assertNotEqual(subprocess.run(argv, capture_output=True, env=self.env).returncode, 0)
        self.assertFalse((self.root / 'invalid').exists())

    def term_choices(self, text):
        item = self.root / 'item.json'
        item.write_text(json.dumps({'text': json.dumps({'statement': {'text': text}})}))
        completed = subprocess.run([sys.executable, str(SCRIPTS / 'terms.py'), str(item)], text=True, capture_output=True, env=self.env)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_terms_cli_groups_words_and_keeps_names_negation_and_hyphens(self):
        text = 'When the CLI MUST not send to `When` and `Cancel` or cancel; a command-line tool is on the path.'
        self.assertEqual(self.term_choices(text), ['CLI', 'not send', 'When', 'Cancel', 'cancel', 'command-line tool', 'path', 'none'])

    def test_terms_cli_keeps_stopwords_inside_backticked_names(self):
        text = 'The tool MUST inspect `state and events` for `Cancel Token` or cancel operation.'
        self.assertEqual(self.term_choices(text), ['tool', 'inspect state and events', 'Cancel Token', 'cancel operation', 'none'])

    def test_terms_cli_splits_punctuation_and_deduplicates_complete_phrases(self):
        text = 'Systems MUST read logs, check flags; emit events and read logs or `read logs`.'
        self.assertEqual(self.term_choices(text), ['Systems', 'read logs', 'check flags', 'emit events', 'none'])

    def test_terms_cli_uses_prepositions_as_phrase_boundaries(self):
        text = "The CLI MUST obtain records through Raptor's query interface against recorded Jev answers."
        self.assertEqual(self.term_choices(text), ['CLI', 'obtain records', "Raptor's query interface", 'recorded Jev answers', 'none'])

    def test_next_default_req_policy_uses_file_item_and_all_three_gates(self):
        item = {'id': 'REQ-T.s1', 'text': json.dumps({'statement': {'text': 'The CLI MUST send.'}})}
        terms = ['CLI', 'send', 'none']
        for name, value in (('item', item), ('terms', terms)):
            (self.root / (name + '.json')).write_text(json.dumps(value))
        argv = ['jq', '-c', '--slurpfile', 'item', str(self.root / 'item.json'), '--slurpfile', 'terms',
                str(self.root / 'terms.json'), '--argjson', 'bar', '.8', '-f', str(SCRIPTS / 'next.jq')]
        def route(value):
            return subprocess.run(argv, input=json.dumps(value), text=True, capture_output=True, env=self.env)
        answers = {key: {'type': 'choice', 'choice': choice, 'confidence': .8}
                   for key, choice in (('obligations', '1'), ('term', 'yes'), ('checkable', 'yes'))}
        value = {'ok': True, 'value': {'answers': answers, 'state': {'item': 'wrong echo'}}}
        self.assertEqual(json.loads(route(value).stdout)['verdict'], 'yes')
        answers['term']['confidence'] = .79
        request = json.loads(route(value).stdout)
        self.assertEqual(request['state']['item'], item)
        self.assertEqual(request['state']['gate']['question'], 'term')
        self.assertEqual(set(request['questions']['which_part']['criteria']), set(terms))
        answers['obligations']['choice'] = '2'
        self.assertEqual(json.loads(route(value).stdout)['state']['gate']['question'], 'obligations')
        del answers['checkable']
        for bad in (value, {'ok': False, 'error': {'id': 'controlled.failure'}}):
            completed = route(bad)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(completed.stdout, '')
            self.assertTrue(completed.stderr)
        self.assertEqual(self.calls(), [])
