"""`quality --questions <tree>.ttl` and `validate --tree <tree>.ttl`: a Turtle tree is accepted wherever a JSON tree is,
dispatched on the file extension. Jev is never called; nothing here sleeps or times."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from test_graph_tree import ADR_TTL
from test_quality import QUESTIONS, QualityCase, tree_answers, tree_node  # noqa: F401
from test_validate import validate

KINDS = (("adr", "--adr", "ADR-T-0001"), ("req", "--req", "REQ-T-0001"), ("nfr", None, None))  # the test index has no NFR record
BOGUS = ADR_TTL.replace('    jj:id "quality-adr" ;', '    jj:id "quality-adr" ; jj:bogus 1 ;')


def questions_of(response):
    wave = response["data"]["results"][0]["wave"]
    return wave["request"]["questions"] if "request" in wave else wave["requests"][0]["request"]["questions"]



def tree_digest(path):
    """The documented tree digest: SHA-256 of the file's bytes with CRLF read as LF."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

class QualityTtl(QualityCase):
    def test_dry_run_with_a_ttl_tree_sends_the_json_trees_questions(self):
        for kind, flag, record in KINDS[:2]:
            ttl = QUESTIONS / f"quality-{kind}.ttl"
            with self.subTest(kind):
                code, out = self.quality(flag, record, "--questions", str(ttl), "--dry-run")
                self.assertEqual((code, out["success"], out["error"]), (0, True, None), out)
                tree = out["data"]["results"][0]["tree"]
                self.assertEqual(tree, {"id": f"quality-{kind}", "source": "override", "path": str(ttl),
                                        "sha256": tree_digest(ttl)})
                self.assertEqual(questions_of(out), tree_node(f"quality-{kind}.json")["questions"])

    def test_a_ttl_tree_judges_a_record_like_its_json_tree(self):
        ttl = str(QUESTIONS / "quality-adr.ttl")
        answers = {"ADR-T-0001/wave-1": tree_answers("quality-adr.json", alternatives="none")}
        code, out = self.quality("--adr", "ADR-T-0001", "--questions", ttl, answers=answers)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["results"][0]["verdict"], "no")

    def test_a_shacl_invalid_ttl_is_quality_tree(self):
        path = self.d / "bad.ttl"
        path.write_text(BOGUS, encoding="utf-8")
        code, out = self.quality("--adr", "ADR-T-0001", "--questions", str(path), "--dry-run")
        self.assertNotEqual(code, 0)
        self.assertEqual(out["error"]["code"], "QUALITY.TREE", out)
        self.assertIn("jj:bogus", out["error"]["message"] + json.dumps(out["error"]))

    def test_unparsable_turtle_is_input_malformed(self):
        path = self.d / "broken.ttl"
        path.write_text("t:x a jj:Tree ;;; <<<", encoding="utf-8")
        code, out = self.quality("--adr", "ADR-T-0001", "--questions", str(path), "--dry-run")
        self.assertNotEqual(code, 0)
        self.assertEqual(out["error"]["code"], "INPUT.MALFORMED", out)


class ValidateTtl(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)

    def test_shipped_ttl_trees_pass(self):
        for kind, _flag, _record in KINDS:
            path = QUESTIONS / f"quality-{kind}.ttl"
            with self.subTest(kind):
                code, out = validate("--tree", str(path))
                self.assertEqual((code, out["success"], out["error"]), (0, True, None), out)
                self.assertEqual(out["data"], {"kind": "tree", "path": str(path),
                                               "sha256": tree_digest(path)})

    def test_a_crlf_copy_of_a_ttl_tree_has_the_lf_digest(self):
        lf = QUESTIONS / "quality-adr.ttl"
        crlf = self.d / "quality-adr.ttl"
        crlf.write_bytes(lf.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        code, out = validate("--tree", str(crlf))
        self.assertEqual((code, out["success"]), (0, True), out)
        self.assertEqual(out["data"]["sha256"], tree_digest(lf))

    def test_a_shacl_invalid_ttl_is_quality_tree(self):
        path = self.d / "bad.ttl"
        path.write_text(BOGUS, encoding="utf-8")
        code, out = validate("--tree", str(path))
        self.assertEqual((code, out["success"], out["error"]["code"]), (2, False, "QUALITY.TREE"), out)
        self.assertEqual([v["path"] for v in out["data"]["violations"]], ["jj:bogus"])

    def test_a_missing_ttl_is_input_missing(self):
        code, out = validate("--tree", str(self.d / "none.ttl"))
        self.assertEqual((code, out["error"]["code"]), (2, "INPUT.MISSING"), out)


if __name__ == "__main__":
    unittest.main()
