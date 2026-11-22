"""Controlled tests for unattended live-run orchestration; no provider or keychain."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load_runner():
    spec = importlib.util.spec_from_file_location('live_runner', ROOT / 'scripts/integration.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LiveRunner(unittest.TestCase):
    def test_only_success_or_typed_timeout_are_accepted(self):
        accepts = load_runner().accepted_keychain
        self.assertTrue(accepts({'ok': True, 'value': {}}))
        self.assertTrue(accepts({'ok': False, 'error': {'id': 'secrets.keyring_timeout'}}))
        self.assertFalse(accepts({'ok': False, 'error': {'id': 'secrets.keyring_read'}}))
        self.assertFalse(accepts({}))

    def test_runner_separates_environment_and_keychain_and_records_timeout(self):
        runner = load_runner()
        calls = []
        def child(argv, **kwargs):
            calls.append((argv, kwargs['env']))
            if 'quality' in argv:
                out, code = json.dumps({'success': True}), 0
            elif 'batch' in argv:
                invalid = kwargs['env'].get('TEST_KEY') == runner.INVALID_KEY
                out = '\n'.join(json.dumps({'ok': not invalid, 'error': {'code': 'AUTH.CREDENTIALS'} if invalid else None}) for _ in range(3))
                code = 2 if invalid else 0
            elif '-c' in argv and 'sc_agent.' in argv[2]:
                out, code = json.dumps({'ok': False, 'error': {'id': 'secrets.keyring_timeout'}}), 0
            else:
                out, code = '', 0
            return subprocess.CompletedProcess(argv, code, out, '')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            credentials, results = root / 'keys', root / 'results.json'
            credentials.write_text('TEST_KEY=controlled-secret\n')
            argv = ['integration.py', '--venv', str(root / 'venv'), '--env-file', str(credentials),
                    '--key-variable', 'TEST_KEY', '--results', str(results)]
            with mock.patch.object(sys, 'argv', argv), mock.patch.object(runner.subprocess, 'run', side_effect=child), \
                    mock.patch.dict(os.environ, {'OTHER_API_KEY': 'unrelated', 'SC_AGENT_TEST_TRAP_PLATFORM_KEYRING': '1'}, clear=True):
                self.assertEqual(runner.main(), 0)
            report = json.loads(results.read_text())
            keychain = [row for row in report if row['case'].startswith('keychain-')]
            self.assertEqual([row['keychain_outcome'] for row in keychain], ['secrets.keyring_timeout'] * 2)
            probes = [env for argv, env in calls if '-c' in argv and 'sc_agent.' in argv[2]]
            self.assertEqual(len(probes), 2)
            self.assertTrue(all('TEST_KEY' not in env and 'OTHER_API_KEY' not in env
                                and 'SC_AGENT_TEST_TRAP_PLATFORM_KEYRING' not in env for env in probes))
            self.assertFalse(credentials.exists())
            self.assertNotIn('controlled-secret', results.read_text())


if __name__ == '__main__':
    unittest.main()
