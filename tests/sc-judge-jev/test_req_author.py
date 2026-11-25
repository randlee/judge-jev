"""req-author quotes the shipped gate questions and their choices; the Raptor record templates are vendored verbatim."""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "plugins/sc-judge-jev/install/templates"
AGENT = (TEMPLATES / "agents/req-author.md.j2").read_text(encoding="utf-8")
QUESTIONS = TEMPLATES / "skills/judge-jev/assets/questions"
RECORDS = TEMPLATES / "skills/judge-jev/assets/templates"


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
                            self.assertIn(choice, AGENT)
        adr = json.loads((QUESTIONS / "quality-adr.json").read_text(encoding="utf-8"))["nodes"]["wave-1"]["questions"]
        for qid, q in adr.items():
            self.assertIn(f"`{qid}`", AGENT)
            self.assertIn(next(iter(q["criteria"])), AGENT)  # the passing choice is the first

    def test_question_text_is_quoted_verbatim(self):
        nodes = json.loads((QUESTIONS / "quality-req.json").read_text(encoding="utf-8"))["nodes"]
        for qid in ("obligations", "term", "checkable"):
            text = nodes["wave-1"]["questions"][qid]["instructions"].split("use `record` as context. ")[1]
            self.assertIn(text, AGENT)

    def test_raptor_templates_carry_their_provenance(self):
        for kind in ("req", "nfr", "adr"):
            lines = (RECORDS / f"raptor-{kind}-record.md.j2").read_text(encoding="utf-8").split("\n")
            self.assertEqual(lines[0], "---")
            self.assertTrue(lines[1].startswith("# Copied from randlee/raptor integration/judge-jev at "), kind)
            self.assertEqual(lines[2], f"name: {kind}-new")


if __name__ == "__main__":
    unittest.main()
