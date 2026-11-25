"""Normalize local execution locations before publishing a recorded decision run.

Only path text is normalized. Model choices, confidence, probabilities, session
ids and digests remain unchanged. The result is a portable presentation copy.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HOME_PATH = re.compile(r'/(?:Users|home)/[^/\s"<>\\]+')
WINDOWS_HOME = re.compile(r'[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s"<>]+')


def portable_recording(value, *, repo=ROOT, locations=()):
    replacements = [(str(Path(repo)), '{repo}'), (str(Path(repo).resolve()), '{repo}')]
    replacements.extend((str(path), label) for path, label in locations if path is not None)
    replacements.extend((path.replace('\\', '\\\\'), label)
                        for path, label in list(replacements) if '\\' in path)
    replacements = sorted(set(replacements), key=lambda item: len(item[0]), reverse=True)

    def normalize(item):
        if isinstance(item, dict):
            return {key: normalize(part) for key, part in item.items()}
        if isinstance(item, list):
            return [normalize(part) for part in item]
        if not isinstance(item, str):
            return item
        for path, label in replacements:
            item = item.replace(path, label)
        item = HOME_PATH.sub('{home}', item)
        item = WINDOWS_HOME.sub('{home}', item)
        for prefix, label in (('/private/var/', '{temporary}/'), ('/private/tmp/', '{tmp}/'),
                              ('/var/folders/', '{temporary}/'), ('/tmp/', '{tmp}/')):
            item = item.replace(prefix, label)
        return item

    return normalize(value)
