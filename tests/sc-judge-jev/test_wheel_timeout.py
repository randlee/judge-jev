"""The pinned wheel cannot silently ignore an explicit custom live timeout."""
from unittest import mock

from jev_support import SCRIPTS  # noqa: F401 - render installed modules before importing them
import jev_judge as jj
from test_jev_batch import BatchCase, PLAN_QS, jsonl, request_line
from test_jev_judge import ScDecidrStub, Transport, consented, plan_answers, run_cli


class WheelTimeout(BatchCase):
    def setUp(self):
        super().setUp()
        self.line = request_line('i', 'text', ('c', PLAN_QS['questions']))
        self.source = self.put('in.jsonl', jsonl([self.line]))

    def test_custom_live_timeout_is_typed_and_never_loads_the_wheel(self):
        for timeout in (0.5, 60.0):
            with self.subTest(timeout=timeout):
                with consented(), mock.patch.object(jj, 'sc_agent_module', side_effect=AssertionError('wheel loaded')):
                    code, result = run_cli(['batch', '--input', self.source, '--run-dir', str(self.d / str(timeout)),
                                            '--timeout', str(timeout)])
                self.assertEqual((code, result['error']['code']), (2, 'DEPENDENCY.SC_DECIDR_TIMEOUT'))
                self.assertIn('wheel', result['error']['message'])
                self.assertTrue(result['error']['suggested_action'])

    def test_default_live_value_still_delegates_to_the_wheel(self):
        wheel = ScDecidrStub(Transport())
        with consented(), mock.patch.object(jj, 'sc_agent_module', return_value=jj.Ok(wheel)):
            code, result = run_cli(['batch', '--input', self.source, '--run-dir', str(self.d / 'default')])
        self.assertEqual((code, result['ok']), (0, True))

    def test_custom_timeout_remains_available_for_fixtures_and_dry_runs(self):
        fixture = self.put('answers.json', {'*': plan_answers()})
        for mode in (['--answers-file', fixture], ['--dry-run']):
            with self.subTest(mode=mode), mock.patch.object(jj, 'sc_agent_module', side_effect=AssertionError('offline wheel load')):
                code, result = run_cli(['batch', '--input', self.source, '--run-dir', str(self.d / mode[0]),
                                        '--timeout', '60', *mode])
            self.assertEqual(code, 0, result)
            self.assertEqual(result['retry_count'], 0)
