"""REQ-JEV-0216: every skill, agent and reference of judge-jev links to references/definitions.md, the one page on definitions."""
import pathlib
import re
import unittest

T = pathlib.Path(__file__).resolve().parents[2] / "plugins/sc-judge-jev/install/templates"
PAGE = T / "skills/judge-jev/references/definitions.md.j2"


class DefinitionsSsotTest(unittest.TestCase):
    def guidance(self):
        files = [T / "skills/judge-jev/SKILL.md.j2", *sorted((T / "skills/judge-jev/references").glob("*.md.j2")),
                 *sorted((T / "agents").glob("*.md.j2"))]
        return [f for f in files if f != PAGE]

    def test_every_guidance_file_links_the_page(self):
        for f in self.guidance():
            with self.subTest(f.name):
                self.assertRegex(f.read_text(encoding="utf-8"), r"\]\((?:\.\./skills/judge-jev/)?(?:references/)?definitions\.md\)")

    def test_definitions_detail_lives_only_on_the_page(self):
        detail = re.compile(r"DEFINITIONS?\.[A-Z_]+|data\.material|jj:attachedTo|jj:Attachment|jj:Definition|definitions\.ttl|`Definitions:` paragraph|record-only|shared term")
        self.assertRegex(PAGE.read_text(encoding="utf-8"), detail)
        for f in self.guidance():
            with self.subTest(f.name):
                self.assertNotRegex(f.read_text(encoding="utf-8"), detail)


if __name__ == "__main__":
    unittest.main()
