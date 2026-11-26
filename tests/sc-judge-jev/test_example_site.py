"""The main-branch Pages build publishes recorded example reports with working links."""
import contextlib
import importlib.util
from html.parser import HTMLParser
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('build_example_site', ROOT / 'scripts/build-site.py')
site_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_builder)


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.hrefs = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.extend(value for key, value in attrs if key == 'href')


class ExamplePages(unittest.TestCase):
    def test_pages_build_discovers_both_examples_and_every_index_link_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / 'site'
            site.mkdir()
            (site / 'index.html').write_text('<h1>Home</h1>')
            report = site / 'reports' / 'nested' / '20261125-1-run.html'
            report.parent.mkdir(parents=True)
            report.write_text('<h1>Existing report</h1>')
            announcement = site / 'announcements' / 'launch.md'
            announcement.parent.mkdir()
            announcement.write_text('# Launch\n\n**Released:** November 25, 2026\n')
            for example in ('decidr-pipeline', 'judge-jev-quality'):
                destination = site / 'examples' / example
                destination.mkdir(parents=True)
                shutil.copyfile(ROOT / 'site/examples' / example / 'report.html', destination / 'report.html')
            with mock.patch.object(site_builder, 'ROOT', root), mock.patch.object(site_builder, 'SITE', site), \
                 mock.patch.object(subprocess, 'run', side_effect=AssertionError('Pages must not invoke model or rendering tools')), \
                 contextlib.redirect_stdout(io.StringIO()):
                site_builder.main()
            index = site / 'diagrams' / 'index.html'
            hrefs = Links(index.read_text()).hrefs
            self.assertIn('../examples/decidr-pipeline/report.html', hrefs)
            self.assertIn('../examples/judge-jev-quality/report.html', hrefs)
            for section in ('diagrams', 'reports', 'announcements'):
                page = site / section / 'index.html'
                for href in Links(page.read_text()).hrefs:
                    url = urlsplit(href)
                    if url.scheme or not url.path:
                        continue
                    target = (page.parent / unquote(url.path)).resolve()
                    self.assertTrue(target.is_relative_to(site.resolve()), href)
                    self.assertTrue(target.is_file(), f'{section}/index.html -> {href}')
            for example in ('decidr-pipeline', 'judge-jev-quality'):
                self.assertEqual((site / 'examples' / example / 'report.html').read_bytes(),
                                 (ROOT / 'site/examples' / example / 'report.html').read_bytes())
            self.assertFalse((site / 'diagrams/examples').exists(), 'reports publish in place, without stale copies')


if __name__ == '__main__':
    unittest.main()
