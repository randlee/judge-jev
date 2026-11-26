"""REQ-JEV-0216: guidance that mentions definitions links to references/definitions.md, and the definitions syntax lives only there."""
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
    def test_guidance_that_mentions_definitions_links_the_page(self):
        for f in guidance():
            text = f.read_text(encoding="utf-8")
            if re.search(r"definition", text, re.I):
                with self.subTest(f.name):
                    self.assertRegex(text, LINK)

    def test_definition_syntax_is_only_on_the_page(self):
        for f in guidance():
            with self.subTest(f.name):
                self.assertNotRegex(f.read_text(encoding="utf-8"), r"jj:Definition|jj:attachedTo")


if __name__ == "__main__":
    unittest.main()
