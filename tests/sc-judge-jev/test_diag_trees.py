"""The diagnostic trees and the strategy tables shipped with the fix strategy."""
import json
import re
import unittest
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[2] / "plugins" / "sc-judge-jev" / "install" / "templates"
QUESTIONS = TEMPLATES / "skills" / "judge-jev" / "assets" / "questions"
FIX_STRATEGY = TEMPLATES / "skills" / "judge-jev" / "references" / "fix-strategy.md.j2"
PROPOSER = TEMPLATES / "agents" / "jev-fix-proposer.md.j2"


def load(name):
    return json.loads((QUESTIONS / name).read_text(encoding="utf-8"))


def strategy_names(path, heading):
    """First-column code spans of the table that follows `heading`."""
    text = path.read_text(encoding="utf-8")
    table = text[text.index(heading):]
    rows = []
    for line in table.splitlines()[1:]:
        if line.startswith("|"):
            rows.append(line)
        elif rows:
            break
    return [m.group(1) for m in (re.match(r"\| `([a-z-]+)` \|", row) for row in rows) if m]


class DiagnosticTreeTests(unittest.TestCase):
    def test_gate_is_the_shipped_gate(self):
        for kind in ("req", "nfr", "adr"):
            with self.subTest(kind=kind):
                gate, diag = load(f"quality-{kind}.json"), load(f"diag-{kind}.json")
                self.assertEqual(diag["kind"], gate["kind"])
                self.assertEqual(diag["start"], gate["start"])
                self.assertEqual(sorted(diag["nodes"]), sorted(gate["nodes"]))
                for name, node in gate["nodes"].items():
                    other = diag["nodes"][name]
                    self.assertEqual(other["verdict_rules"], node["verdict_rules"])
                    self.assertEqual({k: v for k, v in other.items() if k not in ("questions", "verdict_rules")},
                                     {k: v for k, v in node.items() if k not in ("questions", "verdict_rules")})
                    for qid, question in node["questions"].items():
                        self.assertEqual(other["questions"][qid], question)

    def test_added_questions_are_diagnostic_choices(self):
        for kind in ("req", "nfr", "adr"):
            with self.subTest(kind=kind):
                gate, diag = load(f"quality-{kind}.json"), load(f"diag-{kind}.json")
                added = 0
                for name, node in diag["nodes"].items():
                    for qid, question in node["questions"].items():
                        if qid in gate["nodes"][name]["questions"]:
                            continue
                        added += 1
                        self.assertTrue(qid.startswith("d_"), qid)
                        self.assertEqual(question["type"], "choice")
                        self.assertGreaterEqual(len(question["criteria"]), 2)
                self.assertGreater(added, 0)

    def test_verdict_rules_never_read_a_diagnostic_answer(self):
        for kind in ("req", "nfr", "adr"):
            with self.subTest(kind=kind):
                for node in load(f"diag-{kind}.json")["nodes"].values():
                    self.assertNotIn('"d_', json.dumps(node["verdict_rules"]))

    def test_diagnostic_tree_is_not_marked_approved(self):
        for kind in ("req", "nfr", "adr"):
            with self.subTest(kind=kind):
                self.assertIs(load(f"diag-{kind}.json")["approved"], False)


class StrategyTableTests(unittest.TestCase):
    def test_skill_and_proposer_list_the_same_strategies(self):
        skill = strategy_names(FIX_STRATEGY, "| Strategy |")
        proposer = strategy_names(PROPOSER, "| `strategy` |")
        self.assertGreaterEqual(len(skill), 10)
        self.assertEqual(skill, proposer)

    def test_every_trigger_names_answers_the_trees_ask(self):
        ids = set()
        for kind in ("req", "nfr", "adr"):
            for node in load(f"diag-{kind}.json")["nodes"].values():
                ids.update(node["questions"])
        text = FIX_STRATEGY.read_text(encoding="utf-8")
        table = text[text.index("| Strategy |"):text.index("Fix `term` answers first")]
        for name in set(re.findall(r"`(d_[a-z_]+)`", table)):
            self.assertIn(name, ids)


if __name__ == "__main__":
    unittest.main()
