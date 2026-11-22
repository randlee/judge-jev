#!/usr/bin/env python3
"""Run judge-jev's real-provider cases and record unattended keychain outcomes."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INVALID_KEY = 'invalid-judge-jev-integration-key'


def accepted_keychain(result):
    return result.get('ok') is True or (result.get('error') or {}).get('id') == 'secrets.keyring_timeout'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--venv', required=True, type=Path)
    parser.add_argument('--env-file', required=True, type=Path)
    parser.add_argument('--key-variable', required=True)
    parser.add_argument('--results', required=True, type=Path)
    args = parser.parse_args()
    try:
        values = dict(line.split('=', 1) for line in args.env_file.read_text().splitlines()
                      if line.strip() and not line.lstrip().startswith('#'))
        secret = values.get(args.key_variable)
        if not secret:
            raise ValueError('TypeSafe key is required')
        python = str(args.venv.resolve() / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
        env = {k: v for k, v in os.environ.items()
               if not k.endswith('_API_KEY') and k not in (args.key_variable, 'SC_AGENT_TEST_TRAP_PLATFORM_KEYRING')
               and not k.startswith('SC_AGENT__')}
        env.update(SC_PROJECT='judge-jev-integration', JUDGE_JEV_REQUIRE_SITR='1',
                   PATH=str(Path(python).parent) + os.pathsep + env.get('PATH', ''))
        cases = []
        with tempfile.TemporaryDirectory(prefix='judge-jev-live-') as tmp:
            root = Path(tmp)
            env['JUDGE_JEV_LOG_ROOT'] = str(root / 'logs')
            env['DECIDR_LOG_ROOT'] = str(root / 'logs')
            def run(name, command, *, key=secret, expected=0, check=None):
                child_env = dict(env)
                if key is not None:
                    child_env[args.key_variable] = key
                try:
                    proc = subprocess.run(command, cwd=root, env=child_env, stdin=subprocess.DEVNULL,
                                          capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
                except subprocess.TimeoutExpired as exc:
                    message = f'{name}: timed out after 300 seconds'
                    if exc.stderr:
                        stderr = exc.stderr.decode('utf-8', 'replace') if isinstance(exc.stderr, bytes) else exc.stderr
                        print(stderr.replace(secret, '<redacted>').replace(INVALID_KEY, '<invalid-key>'), file=sys.stderr)
                    print(message, file=sys.stderr)
                    cases.append({'case': name, 'passed': False, 'error': message})
                    return ''
                stdout = proc.stdout.replace(secret, '<redacted>').replace(INVALID_KEY, '<invalid-key>')
                stderr = proc.stderr.replace(secret, '<redacted>').replace(INVALID_KEY, '<invalid-key>')
                if stderr:
                    print(f'{name} stderr: {stderr}', file=sys.stderr)
                try:
                    passed = proc.returncode == expected and (check(stdout) if check else True)
                except (ValueError, TypeError, KeyError, AttributeError):
                    passed = False
                cases.append({'case': name, 'passed': passed, 'exit': proc.returncode, 'stdout': stdout, 'stderr': stderr})
                print(f'{name}: {"PASS" if passed else "FAIL"}', flush=True)
                return stdout
            run('git-init', ['git', 'init', '-q', str(root)])
            installer = ROOT / 'plugins/sc-judge-jev/install.py'
            run('install', [python, str(installer), '--dest', str(root), '--target', 'claude', '--allow-remote-judge'])
            setup = ("import json,sys; from pathlib import Path; "
                     "sys.path.insert(0,sys.argv[1]); from test_quality import INDEX; "
                     "from test_jev_batch import BatchTests,jsonl; p=Path(sys.argv[2]); "
                     "(p/'index.json').write_text(json.dumps(INDEX)); (p/'batch.jsonl').write_text(jsonl(BatchTests.LINES))")
            run('prepare', [python, '-c', setup, str(ROOT / 'tests/sc-judge-jev'), str(root)])
            script = str(root / '.claude/skills/judge-jev/scripts/jev_judge.py')
            run('quality', [python, script, 'quality', '--req', 'REQ-T-0001', '--index', 'index.json'],
                check=lambda text: json.loads(text).get('success') is True)
            batch = [python, script, 'batch', '--input', 'batch.jsonl', '--repeat', '1']
            run('batch', batch, check=lambda text: len(rows := [json.loads(line) for line in text.splitlines()]) == 3 and all(r.get('ok') for r in rows))
            for n in range(4):
                run(f'invalid-key-{n + 1}', batch, key=INVALID_KEY, expected=2,
                    check=lambda text: any((json.loads(line).get('error') or {}).get('code') == 'AUTH.CREDENTIALS' for line in text.splitlines()))
            for operation in ('send', 'send_batch'):
                probe = ("import json,sc_agent; q={'model':'jev','state':'test','questions':{'q':{'type':'noul'}}}; "
                         f"r=sc_agent.{operation}({'[q]' if operation == 'send_batch' else 'q'},model='jev',agent_role='judge-jev'); "
                         "r=(r['value'][0] if r.get('ok') and isinstance(r.get('value'),list) else r); "
                         "print(json.dumps({'ok':r.get('ok'),'error':{'id':(r.get('error') or {}).get('id')}}))")
                text = run('keychain-' + operation, [python, '-c', probe], key=None,
                           check=lambda out: accepted_keychain(json.loads(out)))
                try:
                    parsed = json.loads(text)
                    cases[-1]['keychain_outcome'] = 'success' if parsed.get('ok') else (parsed.get('error') or {}).get('id')
                except (ValueError, TypeError):
                    cases[-1]['keychain_outcome'] = 'invalid result'
            run('sitr', [python, '-m', 'pytest', '-q', str(ROOT / 'tests/sc-judge-jev/test_decidr_client.py'), '-k', 'sitr'], key=None)
        args.results.parent.mkdir(parents=True, exist_ok=True)
        args.results.write_text(json.dumps(cases, indent=2), encoding='utf-8')
        return 0 if all(case['passed'] for case in cases) else 1
    finally:
        args.env_file.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
