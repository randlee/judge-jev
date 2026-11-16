"""The runtime prompt templates of references/write-records.md and the commands that page gives."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from layout_support import sc_compose

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "plugins" / "sc-judge-jev" / "install" / "templates" / "skills" / "judge-jev"
TEMPLATES = SKILL / "assets" / "templates"
TENETS, WRITE = TEMPLATES / "record-tenets.md.j2", TEMPLATES / "record-write.md.j2"
REFERENCE = SKILL / "references" / "write-records.md.j2"
QUESTIONS = SKILL / "assets" / "questions"

RECORD = {"record_id": "REQ-ABC-0001", "kind": "req", "title": "One listener",
          "record_text": "### Requirement Statement\n\n- The server MUST do x and OLD-TEXT-MARKER.",
          "prd_clauses": [{"id": "PRD-CMD-1", "text": "Every command returns a Result."}]}
TENET_REPLY = {"record_id": "REQ-ABC-0001",
               "tenets": [{"id": "T1", "modal": "MUST", "text": "The server does x.", "prd": ["PRD-CMD-1"]},
                          {"id": "T2", "modal": "MUST NOT", "text": "The server does y.", "prd": []}],
               "rationale": ["x keeps callers simple"],
               "terms": [{"name": "listener", "meaning": "one bound TCP socket", "source": "docs/a.md:3"}],
               "must_not_say": ["that a crate must avoid a dependency"], "conflicts": []}


def render(template, variables):
    lib = sc_compose()
    request = lib.ComposeRequest(str(template.parent), lib.ComposeMode.file(str(template)), vars_input=variables,
                                 policy=lib.ComposePolicy(strict_undeclared_variables=True))
    return lib.compose_file(request).rendered_text


def write_vars(**extra):
    merged = {**RECORD, **TENET_REPLY, **extra}
    merged.pop("record_text")
    return merged


def fenced(marker):
    """The fenced bash block of the reference that contains `marker`."""
    for block in re.findall(r"```bash\n(.*?)```", REFERENCE.read_text(encoding="utf-8"), re.S):
        if marker in block:
            return block
    raise AssertionError(f"no bash block contains {marker!r}")


class TemplateShape(unittest.TestCase):
    def test_runtime_templates_are_copied_not_rendered_at_install(self):
        for template in (TENETS, WRITE):
            with self.subTest(template=template.name):
                lines = template.read_text(encoding="utf-8").split("\n")
                self.assertEqual(lines[0], "---")
                self.assertTrue(lines[1].startswith("name: judge-jev-record-"), lines[1])

    def test_write_template_never_reads_the_old_record(self):
        self.assertNotIn("record_text", WRITE.read_text(encoding="utf-8"))
        self.assertNotIn("original_text", WRITE.read_text(encoding="utf-8"))


class TenetsPrompt(unittest.TestCase):
    def test_req_asks_for_a_modal_and_shows_the_record(self):
        text = render(TENETS, RECORD)
        self.assertIn("OLD-TEXT-MARKER", text)
        self.assertIn("**PRD-CMD-1** Every command returns a Result.", text)
        self.assertIn('"modal": "MUST"', text)
        self.assertNotIn('"part"', text)
        self.assertNotIn("as its author first wrote it", text)

    def test_adr_asks_for_a_part(self):
        text = render(TENETS, {**RECORD, "record_id": "ADR-ABC-0001", "kind": "adr"})
        self.assertIn('"part": "decision"', text)
        self.assertNotIn('"modal"', text)

    def test_original_text_is_shown_when_given(self):
        text = render(TENETS, {**RECORD, "original_text": "FIRST-DRAFT-MARKER"})
        self.assertIn("as its author first wrote it", text)
        self.assertIn("FIRST-DRAFT-MARKER", text)

    def test_a_missing_variable_is_an_error(self):
        lib = sc_compose()
        with self.assertRaises(lib.ScComposeError):
            render(TENETS, {k: v for k, v in RECORD.items() if k != "prd_clauses"})


class WritePrompt(unittest.TestCase):
    def test_req_prompt(self):
        text = render(WRITE, write_vars())
        self.assertNotIn("OLD-TEXT-MARKER", text)
        self.assertIn("Write 3 complete candidate texts", text)
        self.assertIn("- **T1** [MUST] The server does x. (PRD-CMD-1)\n- **T2** [MUST NOT] The server does y.\n", text)
        self.assertIn("- `listener`: one bound TCP socket", text)
        self.assertIn("- that a crate must avoid a dependency", text)
        self.assertIn("confidence 0.6 or higher", text)
        self.assertIn("**MUST NOT statements:**", text)
        self.assertNotIn("already scored low", text)
        self.assertNotIn("{%", text)
        self.assertNotIn("{{", text)

    def test_n_threshold_and_avoid(self):
        text = render(WRITE, write_vars(n=5, threshold=0.7, avoid=["s2: check read as needs a measure"]))
        self.assertIn("Write 5 complete candidate texts", text)
        self.assertIn("Make the 5 candidates differ", text)
        self.assertIn("confidence 0.7 or higher", text)
        self.assertIn("already scored low", text)
        self.assertIn("- s2: check read as needs a measure", text)

    def test_adr_prompt(self):
        tenets = [{"id": "T1", "part": "decision", "text": "Use one writer thread.", "prd": []}]
        text = render(WRITE, write_vars(record_id="ADR-ABC-0001", kind="adr", tenets=tenets))
        self.assertIn("- **T1** [decision] Use one writer thread.", text)
        self.assertIn("### Alternatives Considered", text)
        self.assertNotIn("MUST statements", text)

    def test_choices_are_the_shipped_tree(self):
        """Every choice the prompt names exists in the tree, and its failing choices are the tree's."""
        for kind in ("req", "nfr", "adr"):
            with self.subTest(kind=kind):
                node = json.loads((QUESTIONS / f"quality-{kind}.json").read_text(encoding="utf-8"))["nodes"]["wave-1"]
                failing = {}
                for rule in node["verdict_rules"]:
                    if rule["verdict"] == "no":
                        for question, choices in {**rule.get("all", {}), **rule.get("any", {})}.items():
                            failing.setdefault(question, set()).update(choices)
                text = render(WRITE, write_vars(kind=kind))
                rows = re.findall(r"^\| `(\w+)`: [^|]* \| ([^|]*) \| ([^|]*) \|$", text, re.M)
                self.assertEqual(sorted(q for q, _, _ in rows), sorted(node["questions"]))
                for question, passing, fails in rows:
                    named_pass, named_fail = set(re.findall(r"`([^`]+)`", passing)), set(re.findall(r"`([^`]+)`", fails))
                    self.assertEqual(named_pass | named_fail, set(node["questions"][question]["criteria"]), question)
                    self.assertFalse(named_pass & named_fail, question)
                    self.assertEqual(named_fail, failing[question], question)


class ReferenceCommands(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)

    def apply(self, record_id, candidate):
        script = re.search(r"<<'PY'\n(.*?)\nPY\n", fenced("applied {len(fresh)} sections"), re.S).group(1)
        doc = self.dir / "requirements.md"
        if not doc.exists():
            doc.write_text("# Requirements\n\n## REQ-ABC-0001: One\n\n**Status:** Active  \n\n### Requirement Statement\n\n"
                           "- The server MUST do x and y.\n\n### Rationale\n\nOld reason.\n\n### Success Criteria\n\nOld test.\n\n"
                           "### Related Documents\n\n- [REQ-ABC-0002](requirements.md)\n\n"
                           "# Requirement: Two\n\n## REQ-ABC-0002: Two\n\n### Requirement Statement\n\n- Untouched MUST stay.\n",
                           encoding="utf-8")
        cand = self.dir / "c.md"
        cand.write_text(candidate, encoding="utf-8")
        done = subprocess.run([sys.executable, "-c", script, str(doc), record_id, str(cand)], capture_output=True, text=True)
        return done, doc.read_text(encoding="utf-8")

    def test_apply_replaces_only_the_sections_written(self):
        done, text = self.apply("REQ-ABC-0001", "### Requirement Statement\n\n**MUST statements:**\n\n- The server MUST do x.\n"
                                "- The server MUST do y.\n\n### Rationale\n\nNew reason.\n\n### Success Criteria\n\nNew test.\n")
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "applied 3 sections to REQ-ABC-0001"), done.stderr)
        self.assertNotIn("x and y", text)
        self.assertNotIn("Old reason", text)
        self.assertIn("## REQ-ABC-0001: One\n\n**Status:** Active  \n\n### Requirement Statement\n\n**MUST statements:**\n", text)
        self.assertIn("New test.\n\n### Related Documents\n\n- [REQ-ABC-0002](requirements.md)\n\n# Requirement: Two", text)
        self.assertIn("- Untouched MUST stay.", text)

    def test_apply_rejects_an_unknown_record_a_bad_start_and_an_unknown_section(self):
        for record_id, candidate, why in (
                ("REQ-ABC-0009", "### Rationale\n\nx\n", "0 headings name REQ-ABC-0009"),
                ("REQ-ABC-000", "### Rationale\n\nx\n", "0 headings name REQ-ABC-000 "),
                ("REQ-ABC-0001", "Some prose first.\n\n### Rationale\n\nx\n", "does not start with a ### section heading"),
                ("REQ-ABC-0001", "### Verification\n\nx\n", "the record has no section ['Verification']")):
            with self.subTest(why=why):
                before = (self.dir / "requirements.md").read_text(encoding="utf-8") if (self.dir / "requirements.md").exists() else None
                done, text = self.apply(record_id, candidate)
                self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
                self.assertIn("REJECT: ", done.stdout)
                self.assertIn(why, done.stdout)
                if before is not None:
                    self.assertEqual(text, before)

    @unittest.skipUnless(shutil.which("jq"), "jq is not installed")
    def test_coverage_check(self):
        program = re.search(r"jq -r --arg kind \"\$KIND\" --slurpfile t \"\$X/tenets.json\" '(.*?)' \"\$X/<writer>.json\"",
                            fenced("REJECT uncovered"), re.S).group(1)
        (self.dir / "tenets.json").write_text(json.dumps(TENET_REPLY), encoding="utf-8")
        reply = {"candidates": [{"n": 1, "covers": {"T1": [1], "T2": [2]}}, {"n": 2, "covers": {"T1": [1]}},
                                {"n": 3, "covers": {"T1": [1], "T2": [1]}}, {"n": 4, "covers": {"T1": [1, 2], "T2": []}}]}
        (self.dir / "w.json").write_text(json.dumps(reply), encoding="utf-8")

        def check(kind):
            done = subprocess.run(["jq", "-r", "--arg", "kind", kind, "--slurpfile", "t", str(self.dir / "tenets.json"), program,
                                   str(self.dir / "w.json")], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            return done.stdout.splitlines()

        self.assertEqual(check("req"), ["c1: ok", "c2: REJECT uncovered T2", "c3: REJECT one statement covers two tenets",
                                        "c4: REJECT uncovered T2"])
        self.assertEqual(check("adr")[2], "c3: ok")
        reply["cannot"] = [{"tenet": "T2", "why": "no measure"}]
        (self.dir / "w.json").write_text(json.dumps(reply), encoding="utf-8")
        self.assertEqual(check("req")[1], "c2: ok")


if __name__ == "__main__":
    unittest.main()
