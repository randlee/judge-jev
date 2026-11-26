"""REQ-JEV-0216: guidance that tells an agent to look up, add or test a term links to references/definitions.md, and the definitions syntax lives only there."""
import pathlib
import re
import unittest

T = pathlib.Path(__file__).resolve().parents[2] / "plugins/sc-judge-jev/install/templates"
PAGE = T / "skills/judge-jev/references/definitions.md.j2"
LINK = re.compile(r"\]\((?:\.\./skills/judge-jev/)?(?:references/)?definitions\.md\)")


def guidance():
    files = [T / "skills/judge-jev/SKILL.md.j2", *sorted((T / "skills/judge-jev/references").glob("*.md.j2")),
             *sorted((T / "agents").glob("*.md.j2"))]
    return [f for f in files if f != PAGE]


class DefinitionsSsotTest(unittest.TestCase):
    def test_guidance_that_looks_up_adds_or_tests_a_term_links_the_page(self):
        tells = re.compile(r"define-term|[Dd]efined terms|compare-definition|^## Definitions", re.M)
        linked = [f.name for f in guidance() if tells.search(f.read_text(encoding="utf-8"))]
        self.assertTrue(linked)
        for f in guidance():
            text = f.read_text(encoding="utf-8")
            if tells.search(text):
                with self.subTest(f.name):
                    self.assertRegex(text, LINK)

    def test_definition_syntax_is_only_on_the_page(self):
        for f in guidance():
            with self.subTest(f.name):
                self.assertNotRegex(f.read_text(encoding="utf-8"), r"jj:Definition|jj:attachedTo")


if __name__ == "__main__":
    unittest.main()
