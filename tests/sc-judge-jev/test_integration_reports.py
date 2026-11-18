"""Controlled report rendering and retained historical panel integrity; no live calls."""
import json
from pathlib import Path
import shutil
from child_support import run_child
from layout_support import REQUIRE_SC_COMPOSE, sc_compose
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[2]


class IntegrationReports(unittest.TestCase):
    def test_documented_strict_render_escapes_raw_values_once(self):
        sc_compose()
        if shutil.which("sc-compose") is None:
            if REQUIRE_SC_COMPOSE:
                self.fail("JUDGE_JEV_REQUIRE_SC_COMPOSE=1 but sc-compose CLI is unavailable")
            self.skipTest("sc-compose CLI is unavailable")
        values = dict(platform="controlled platform", run_utc="controlled time", owner="controlled owner",
                      judge_jev_commit="controlled revision", sc_agent_version="controlled version",
                      python_version="controlled Python", command_and_cases="install --dest <checkout>",
                      outcome="render check only", evidence_and_failures="A & B <diagnostic>")
        with tempfile.TemporaryDirectory() as directory:
            variables, output = Path(directory) / "values.json", Path(directory) / "panel.xhtml"
            variables.write_text(json.dumps(values), encoding="utf-8")
            run_child(["sc-compose", "render", "--root", ".", "--file",
                            "templates/integration-report/report.xhtml.j2", "--var-file", str(variables),
                            "--strict", "--output", str(output)], cwd=ROOT, check=True, hang_guard=60)
            text = "".join(ET.parse(output).getroot().itertext())
            self.assertIn(values["command_and_cases"], text)
            self.assertIn(values["evidence_and_failures"], text)
            self.assertNotIn("&amp;lt;checkout", output.read_text(encoding="utf-8"))

    def test_oldest_run_contains_the_corrected_panel_and_original_timestamp(self):
        class RunPage(HTMLParser):
            def __init__(self):
                super().__init__()
                self.panels = []

            def handle_starttag(self, tag, attrs):
                if tag == "iframe":
                    self.panels.append(dict(attrs)["srcdoc"])

        reports = ROOT / "site/reports"
        panel = (reports / "20261116-0-integration/macos.xhtml").read_text(encoding="utf-8")
        self.assertIn("--dest <checkout>", "".join(ET.fromstring(panel).itertext()))
        self.assertNotIn("&amp;lt;checkout", panel)
        page = RunPage()
        page.feed((reports / "20261116-0-integration.html").read_text(encoding="utf-8"))
        self.assertEqual(page.panels, [panel])
        record = json.loads((reports / "20261116-0-integration/20261116-0-integration.json").read_text())
        self.assertEqual(record["created_at"], "2026-11-16T15:15:00Z")
