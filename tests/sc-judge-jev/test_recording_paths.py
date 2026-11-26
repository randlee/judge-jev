"""Published recordings normalize execution locations without changing model data."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from recording_paths import portable_recording


class PortableRecordings(unittest.TestCase):
    def test_paths_in_nested_json_strings_are_normalized_and_answers_are_unchanged(self):
        answers = {'choice': 'Cancel', 'confidence': .17, 'probabilities': {'Cancel': .22, 'none': .22}}
        value = {'argv': ['/Users/operator/project/scripts/run.py', '/private/var/folders/local/log.json'],
                 'stdout': json.dumps({'path': '/Users/operator/project/tree.json', 'answers': answers}),
                 'windows_stdout': json.dumps({'path': r'C:\Users\operator\work\run.py'}),
                 'answers': answers, 'session_id': 'captured-session'}
        result = portable_recording(value, repo='/Users/operator/project')
        self.assertEqual(result['argv'], ['{repo}/scripts/run.py', '{temporary}/folders/local/log.json'])
        self.assertEqual(json.loads(result['stdout']), {'path': '{repo}/tree.json', 'answers': answers})
        self.assertEqual(json.loads(result['windows_stdout'])['path'], r'{home}\work\run.py')
        self.assertEqual(result['answers'], answers)
        self.assertEqual(result['session_id'], 'captured-session')
        self.assertTrue(value['argv'][0].startswith('/Users/'), 'normalization must not mutate the capture')
        self.assertEqual(portable_recording(result, repo='/Users/operator/project'), result)

    def test_windows_repo_paths_match_native_forward_slash_and_json_spellings(self):
        repo = r'C:\Users\operator\project'
        value = {'argv': [repo + r'\scripts\run.py', repo.replace('\\', '/') + '/scripts/run.py'],
                 'stdout': json.dumps({'path': repo + r'\tree.json'})}
        result = portable_recording(value, repo=repo)
        self.assertEqual(result['argv'], [r'{repo}\scripts\run.py', '{repo}/scripts/run.py'])
        self.assertEqual(json.loads(result['stdout']), {'path': r'{repo}\tree.json'})
        self.assertEqual(portable_recording(result, repo=repo), result)

    def test_published_recordings_and_reports_have_no_personal_absolute_paths(self):
        for example in ('decidr-pipeline', 'judge-jev-quality'):
            for name in ('recorded.json', 'report.html'):
                path = ROOT / 'site/examples' / example / name
                with self.subTest(path=str(path)):
                    self.assertNotRegex(path.read_text(), r'/Users/|/home/[^/\s]+/|/private/(?:var|tmp)/|[A-Za-z]:\\Users\\')


if __name__ == '__main__':
    unittest.main()
