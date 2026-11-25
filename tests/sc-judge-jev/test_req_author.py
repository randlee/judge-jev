"""req-author quotes the shipped gate questions and their choices."""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "plugins/sc-judge-jev/install/templates"
AGENT = (TEMPLATES / "agents/req-author.md.j2").read_text(encoding="utf-8")
QUESTIONS = TEMPLATES / "skills/judge-jev/assets/questions"


class ReqAuthorTest(unittest.TestCase):
    def test_quoted_gate_questions_match_the_trees(self):
        for kind in ("req", "nfr"):
            nodes = json.loads((QUESTIONS / f"quality-{kind}.json").read_text(encoding="utf-8"))["nodes"]
            for node in nodes.values():
                for qid, q in node.get("questions", {}).items():
                    if qid.startswith("d_"):
                        continue
                    with self.subTest(kind=kind, question=qid):
                        self.assertIn(f"`{qid}`", AGENT)
                        for choice in q["criteria"]:
                            self.assertTrue(f"`{choice}`" in AGENT or f'"{choice}"' in AGENT, choice)
        adr = json.loads((QUESTIONS / "quality-adr.json").read_text(encoding="utf-8"))["nodes"]["wave-1"]["questions"]
        for qid, q in adr.items():
            self.assertIn(f"`{qid}`", AGENT)
            self.assertIn(f'"{next(iter(q["criteria"]))}"', AGENT)  # the passing choice is the first

    def test_question_text_is_quoted_verbatim(self):
        for kind in ("req", "nfr"):
            nodes = json.loads((QUESTIONS / f"quality-{kind}.json").read_text(encoding="utf-8"))["nodes"]
            for qid in ("obligations", "term", "checkable"):
                text = nodes["wave-1"]["questions"][qid]["instructions"].split("use `record` as context. ")[1]
                self.assertIn(text, AGENT, f"{kind}.{qid}")

    def test_version_sync_skips_only_vendored_raptor_templates(self):
        import importlib.util, shutil, tempfile
        spec = importlib.util.spec_from_file_location("cvs", ROOT / "scripts/check_version_sync.py")
        cvs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cvs)
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp) / "plugins/x"
            d.mkdir(parents=True)
            for name in ("raptor-req-record.md.j2", "other.md.j2"):
                (d / name).write_text("---\nname: x\nversion: 1.0.0\n---\nbody\n", encoding="utf-8")
            cvs._rel = lambda f: f.relative_to(tmp).as_posix()
            drift = cvs.locked_drift(pathlib.Path(tmp), "9.9.9")
        self.assertEqual([x for x in drift if "template version" in x], ["plugins/x/other.md.j2: template version 1.0.0 != VERSION 9.9.9"])


if __name__ == "__main__":
    unittest.main()
