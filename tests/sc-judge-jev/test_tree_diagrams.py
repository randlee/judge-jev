"""docs/diagrams/trees/*.md are generated from the shipped trees and must match them (scripts/gen_tree_diagrams.py)."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("gen_tree_diagrams", ROOT / "scripts" / "gen_tree_diagrams.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


class TreeDiagramsTest(unittest.TestCase):
    def test_committed_diagrams_match_trees(self):
        for tree_id in gen.TREES:
            with self.subTest(tree=tree_id):
                committed = (gen.OUT / f"{tree_id}.md").read_text(encoding="utf-8")
                self.assertEqual(committed, gen.page(tree_id), "rerun python3 scripts/gen_tree_diagrams.py")

    def test_marks_follow_verdict_rules(self):
        body = gen.page("quality-req")
        self.assertIn("✗ needs a measure", body)
        self.assertIn("→ 2", body)
        self.assertIn("✓ condition+obligation", body)
        self.assertIn("<b>d_check_method</b> (diagnostic)", body)
        self.assertNotIn("✗ unit test", body)


if __name__ == "__main__":
    unittest.main()
