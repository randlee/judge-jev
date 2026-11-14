"""``jev_judge.py doctor`` (REQ-JEV-0214, REQ-JEV-0215): check everything judge-jev loads in a repository, call nothing.

Errors (exit 2, report in ``data``): schema and model failures, SHACL violations (edges, cycles, closed shapes), duplicate
question ids. Warnings (exit 0): an unattached definition, a record absent from ``--index``, a missing location, a missing
source. Jev is never called, no key is set, and nothing is written.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jev_support  # noqa: F401  (puts the rendered scripts on sys.path)
import jev_definitions  # noqa: E402
import jev_judge as jj  # noqa: E402

from test_definitions import ADR, OTHER, definition, iri, ttl  # noqa: E402
from test_graph_tree import BRANCH_TTL  # noqa: E402
from test_jev_judge import env, run_cli, write  # noqa: E402
from test_quality import INDEX, TreeOverride, never_called  # noqa: E402


def renamed(text, to):
    """BRANCH_TTL as a second tree ``to``: every IRI differs, every ``jj:id`` of a question is the same."""
    return text.replace("t:b", f"t:{to}").replace("q:b.", f"q:{to}.").replace("o:b.", f"o:{to}.").replace('jj:id "b"', f'jj:id "{to}"')


class DoctorCase(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        self.root = self.d / "repo"
        (self.root / "docs").mkdir(parents=True)
        (self.root / "docs" / "r.md").write_text("# Title\n\n## Heading\n\ntext\n", encoding="utf-8")
        self.index = write(self.d, "index.json", INDEX)

    def files(self):
        return sorted(str(p) for p in self.d.rglob("*"))

    def doctor(self, *argv, root=True):
        before = self.files()
        with env(), mock.patch.object(jj, "sc_agent_module", side_effect=AssertionError("unexpected live sc-decidr call")):
            code, out = run_cli(["doctor", *argv, *(["--repository-root", str(self.root)] if root else [])])
        self.assertEqual(self.files(), before, "doctor writes nothing")
        return code, out

    def defs(self, *definitions, name="defs.definitions.ttl"):
        return write(self.root, name, ttl(*definitions))

    def codes(self, out, key):
        return [i["code"] for i in out["data"][key]]


class CleanScope(DoctorCase):
    def test_the_shipped_trees_alone_are_clean(self):
        code, out = self.doctor()
        self.assertEqual((code, out["success"], out["data"]["ok"], out["data"]["errors"], out["data"]["warnings"]), (0, True, True, [], []), out)
        names = {Path(c["path"]).name for c in out["data"]["checked"]}
        self.assertTrue({"quality-req.ttl", "quality-nfr.ttl", "quality-adr.ttl", "quality-req.json", "dev.json", "plan.json"} <= names)
        self.assertEqual(out["data"]["counts"], {"files": len(out["data"]["checked"]), "errors": 0, "warnings": 0})

    def test_a_valid_definition_with_a_real_source_and_location_is_clean(self):
        path = self.defs(definition("x", "fast", "t", "docs/r.md", (ADR, "docs/r.md#Heading")))
        code, out = self.doctor(path, "--index", self.index)
        self.assertEqual((code, out["data"]["errors"], out["data"]["warnings"]), (0, [], []), out)
        self.assertIn({"kind": "definitions", "path": path}, out["data"]["checked"])
        self.assertEqual(out["data"]["notes"], [])

    def test_definitions_under_the_repository_folder_are_found_without_naming_them(self):
        write(self.root, ".sc/judge-jev/definitions.ttl", ttl(definition("x", "fast", "t", "docs/r.md")))
        code, out = self.doctor()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.codes(out, "warnings"), ["DEFINITION.UNATTACHED"])

    def test_a_directory_argument_is_scanned(self):
        folder = self.root / "extra"
        write(folder, "sub/b.definitions.ttl", ttl(definition("x", "fast", "t", "docs/r.md")))
        code, out = self.doctor(str(folder))
        self.assertEqual((code, self.codes(out, "warnings")), (0, ["DEFINITION.UNATTACHED"]), out)

    def test_a_file_named_twice_is_checked_once(self):
        path = self.defs(definition("x", "fast", "t", "docs/r.md", (ADR, None)))
        code, out = self.doctor(path, path)
        self.assertEqual(code, 0, out)
        self.assertEqual(sum(1 for c in out["data"]["checked"] if c["path"] == path), 1)


class Warnings(DoctorCase):
    def test_an_unattached_definition_is_one_warning_naming_it_and_exit_0(self):
        path = self.defs(definition("x", "fast", "t", "docs/r.md"))
        code, out = self.doctor(path)
        self.assertEqual((code, out["success"], out["data"]["errors"]), (0, True, []), out)
        (warning,) = out["data"]["warnings"]
        self.assertEqual((warning["code"], warning["definition"], warning["file"]), ("DEFINITION.UNATTACHED", iri("x"), path))
        self.assertIn(iri("x"), warning["message"])

    def test_without_an_index_attachments_are_not_checked_and_doctor_says_so(self):
        path = self.defs(definition("x", "fast", "t", "docs/r.md", (OTHER, None)))
        code, out = self.doctor(path)
        self.assertEqual((code, out["data"]["warnings"]), (0, []), out)
        self.assertEqual([n["code"] for n in out["data"]["notes"]], ["DOCTOR.INDEX_SKIPPED"])

    def test_a_record_the_index_does_not_hold_is_a_warning(self):
        path = self.defs(definition("x", "fast", "t", "docs/r.md", (OTHER, None), (ADR, None)))
        code, out = self.doctor(path, "--index", self.index)
        self.assertEqual(code, 0, out)
        (warning,) = out["data"]["warnings"]
        self.assertEqual((warning["code"], warning["record"]), ("DEFINITION.RECORD_UNKNOWN", OTHER))

    def test_a_record_of_another_repository_is_a_warning(self):
        other = "urn:raptor:repo:elsewhere#ADR-T-0001"
        path = self.defs(definition("x", "fast", "t", "docs/r.md", (other, None)))
        code, out = self.doctor(path, "--index", self.index)
        self.assertEqual((code, self.codes(out, "warnings")), (0, ["DEFINITION.RECORD_UNKNOWN"]), out)

    def test_a_location_that_does_not_exist_is_a_warning(self):
        for location in ("docs/missing.md", "docs/r.md#Nowhere", "docs/"):
            with self.subTest(location):
                path = self.defs(definition("x", "fast", "t", "docs/r.md", (ADR, location)))
                code, out = self.doctor(path)
                self.assertEqual((code, self.codes(out, "warnings")), (0, ["DEFINITION.LOCATION_MISSING"]), out)
                self.assertEqual(out["data"]["warnings"][0]["location"], location)

    def test_a_symbol_location_checks_its_file_and_notes_the_symbol_is_unresolved(self):
        path = self.defs(definition("x", "fast", "t", "docs/r.md", (ADR, "docs/r.md::Thing")))
        code, out = self.doctor(path)
        self.assertEqual((code, out["data"]["warnings"]), (0, []), out)
        self.assertEqual([n["code"] for n in out["data"]["notes"]], ["DOCTOR.INDEX_SKIPPED", "DOCTOR.SYMBOL_UNCHECKED"])

    def test_a_source_that_does_not_exist_is_a_warning(self):
        path = self.defs(definition("x", "fast", "t", "docs/gone.md", (ADR, None)))
        code, out = self.doctor(path)
        self.assertEqual((code, self.codes(out, "warnings")), (0, ["DEFINITION.SOURCE_MISSING"]), out)
        self.assertEqual(out["data"]["warnings"][0]["source"], "docs/gone.md")

    def test_a_source_path_too_long_for_the_file_system_is_a_missing_source_warning(self):
        path = self.defs(definition("x", "fast", "t", "docs/" + "a" * 300 + ".md", (ADR, None)))
        code, out = self.doctor(path)
        self.assertEqual((code, self.codes(out, "warnings"), out["data"]["errors"]), (0, ["DEFINITION.SOURCE_MISSING"], []), out)

    def test_definitions_with_an_index_that_names_no_repository_warn(self):
        index = json.loads(json.dumps(INDEX))
        del index["metadata"]["repository"]
        path = self.defs(definition("x", "fast", "t", "docs/r.md", (ADR, None)))
        code, out = self.doctor(path, "--index", write(self.d, "norepo.json", index))
        self.assertEqual((code, self.codes(out, "warnings")), (0, ["DEFINITION.REPOSITORY_UNKNOWN"]), out)
        code, out = self.doctor(path, "--index", self.index)  # the index with a repository: no such warning
        self.assertEqual(self.codes(out, "warnings"), [])

    def test_a_definitions_file_in_a_subfolder_of_the_repository_folder_is_neither_loaded_nor_validated(self):
        write(self.root, ".sc/judge-jev/team/bad.definitions.ttl", "this is not turtle")
        code, out = self.doctor()
        self.assertEqual((code, out["data"]["errors"]), (0, []), out)
        self.assertFalse([c for c in out["data"]["checked"] if "team" in c["path"]])
        self.assertEqual(jev_definitions.discover(self.root), [])

    def test_every_warning_at_once_still_exits_0(self):
        path = self.defs(definition("a", "one", "t", "docs/gone.md", (OTHER, "docs/none.md")), definition("b", "two", "t", "docs/r.md"))
        code, out = self.doctor(path, "--index", self.index)
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(self.codes(out, "warnings")),
                         ["DEFINITION.LOCATION_MISSING", "DEFINITION.RECORD_UNKNOWN", "DEFINITION.SOURCE_MISSING", "DEFINITION.UNATTACHED"])
        self.assertEqual(out["data"]["counts"]["errors"], 0)


class Errors(DoctorCase):
    def failed(self, *argv):
        code, out = self.doctor(*argv)
        self.assertEqual((code, out["success"], out["data"]["ok"]), (2, False, False), out)
        self.assertEqual(out["error"]["code"], "DOCTOR.FAILED")
        self.assertEqual(out["data"]["counts"]["errors"], len(out["data"]["errors"]))
        return out["data"]["errors"]

    def test_a_ttl_cycle_names_the_cycle(self):
        path = write(self.root, "cyc.ttl", BRANCH_TTL.replace("jj:goto t:b:done", "jj:goto t:b:wave-1"))
        (error,) = self.failed(path)
        self.assertEqual((error["code"], error["file"]), ("QUALITY.TREE", path))
        self.assertIn("cycle", error["message"])
        self.assertEqual(error["violations"][0]["constraint"], "jjs:WaveNoCycle")

    def test_a_json_cycle_in_a_path_argument(self):
        tree = TreeOverride.TREE
        loop = {**tree, "nodes": {**tree["nodes"], "w1": {**tree["nodes"]["w1"], "next": [{"goto": "w1"}]}}}
        path = write(self.root, "loop.json", loop)
        (error,) = self.failed(path)
        self.assertEqual((error["code"], error["file"]), ("QUALITY.TREE", path))
        self.assertIn("cycle", error["message"])

    def test_a_tree_that_breaks_a_closed_shape(self):
        path = write(self.root, "x.ttl", BRANCH_TTL + 't:b jj:surprise "x" .\n')
        (error,) = self.failed(path)
        self.assertEqual(error["code"], "QUALITY.TREE")
        self.assertTrue(error["violations"])

    def test_a_json_tree_that_fails_its_model(self):
        path = write(self.root, "bad.json", {"id": "x", "start": "nope", "nodes": {}})
        (error,) = self.failed(path)
        self.assertEqual((error["code"], error["file"]), ("QUALITY.TREE", path))

    def test_a_question_iri_declared_in_two_files_names_both_files(self):
        first = write(self.root, "one.ttl", BRANCH_TTL)
        second = write(self.root, "two.ttl", BRANCH_TTL.replace("t:b", "t:c").replace('jj:id "b"', 'jj:id "c"'))  # new tree and node IRIs, same question IRIs
        errors = self.failed(first, second)
        codes = {e["code"] for e in errors}
        self.assertEqual(codes, {"QUESTIONS.DUPLICATE_IRI"})
        (error,) = [e for e in errors if e["question"] == "urn:judge-jev:question:b.size"]
        self.assertEqual(error["files"], [first, second])
        for needle in ("urn:judge-jev:question:b.size", first, second):
            self.assertIn(needle, error["message"])

    def test_a_copy_of_a_tree_in_a_second_file_is_a_duplicate(self):
        one = write(self.root, "one.ttl", BRANCH_TTL)
        copy = write(self.root, "copy.ttl", BRANCH_TTL)
        self.assertTrue({e["code"] for e in self.failed(one, copy)} == {"QUESTIONS.DUPLICATE_IRI"})

    def test_a_consumer_extension_under_the_repository_folder_cannot_redeclare_a_shipped_question(self):
        shipped = (jj.QUESTIONS_DIR / "quality-adr.ttl").read_text(encoding="utf-8")
        write(self.root, ".sc/judge-jev/extension.ttl", shipped.replace("t:quality-adr", "t:mine").replace('jj:id "quality-adr"', 'jj:id "mine"'))
        code, out = self.doctor()
        self.assertEqual(code, 2, out)
        errors = [e for e in out["data"]["errors"] if e["code"] == "QUESTIONS.DUPLICATE_IRI"]
        self.assertTrue(errors, out)
        self.assertTrue(all(len(e["files"]) == 2 and any(f.endswith("extension.ttl") for f in e["files"])
                            and any(f.endswith("quality-adr.ttl") for f in e["files"]) for e in errors), errors)

    OTHER_SIZE = ('q:b.other a jj:Question ; jj:id "size" ; jj:rank 2 ; jj:instructions "Other?" ; '
                  'jj:option o:b.size:small , o:b.size:big .\n')

    def test_a_jj_id_used_twice_in_one_wave_is_a_tree_error(self):
        text = BRANCH_TTL.replace('t:b:wave-1 a jj:Wave ; jj:id "wave-1" ; jj:asks q:b.size ;',
                                  't:b:wave-1 a jj:Wave ; jj:id "wave-1" ; jj:asks q:b.size , q:b.other ;') + self.OTHER_SIZE
        path = write(self.root, "dup.ttl", text)
        (error,) = self.failed(path)
        self.assertEqual((error["code"], error["file"]), ("QUALITY.TREE", path))

    def test_a_jj_id_used_twice_in_one_tree_across_waves_is_an_error(self):
        # wave-2 asks q:b.other (id "size", like wave-1's q:b.size); each wave alone is valid
        wave2 = BRANCH_TTL.replace('t:b:wave-2 a jj:Wave ; jj:id "wave-2" ; jj:asks q:b.size ;', 't:b:wave-2 a jj:Wave ; jj:id "wave-2" ; jj:asks q:b.other ;')
        wave2 = wave2.replace("jj:whenAll [ a jj:Condition ; jj:question q:b.size ; jj:choice o:b.size:huge ] .\nt:b:wave-2:r2",
                              "jj:whenAll [ a jj:Condition ; jj:question q:b.other ; jj:choice o:b.size:huge ] .\nt:b:wave-2:r2")
        text = wave2 + self.OTHER_SIZE.replace("o:b.size:small , o:b.size:big", "o:b.size:small , o:b.size:big , o:b.size:huge")
        path = write(self.root, "dup.ttl", text)
        code, out = self.doctor(path)
        self.assertEqual(code, 2, out)
        (error,) = [e for e in out["data"]["errors"] if e["file"] == path]
        self.assertEqual((error["code"], error["question_id"]), ("QUESTIONS.DUPLICATE_ID", "size"))
        self.assertEqual(error["iris"], ["urn:judge-jev:question:b.other", "urn:judge-jev:question:b.size"])

    def test_the_shipped_trees_are_clean(self):
        code, out = self.doctor()
        self.assertEqual((code, out["data"]["errors"]), (0, []), out)

    def test_a_definition_iri_in_two_files_is_an_error(self):
        a = self.defs(definition("x", "fast", "t", "docs/r.md", (ADR, None)), name="a.definitions.ttl")
        b = self.defs(definition("x", "slow", "t", "docs/r.md", (ADR, None)), name="b.definitions.ttl")
        (error,) = self.failed(a, b)
        self.assertEqual(error["code"], "DEFINITIONS.INVALID")
        self.assertIn(iri("x"), error["message"])

    def test_hostile_definitions_files_are_errors_and_the_rest_is_still_checked(self):
        cases = {
            "malformed": (b"d:one a jj:Definition ; ;; .", "INPUT.MALFORMED"),
            "non-utf8": (b"\xff\xfe\x00bad", "INPUT.MALFORMED"),
            "oversized": (b"#" + b"x" * 200_000, "DEFINITIONS.INVALID"),
            "blank node": ((ttl() + '[] a jj:Definition ; jj:term "t" ; jj:text "x" ; jj:source "docs/r.md" .\n').encode(), "DEFINITIONS.INVALID"),
            "literal record": (ttl(definition("x", "t", "x", "docs/r.md", (ADR, None))).replace(f"<{ADR}>", '"ADR-T-0001"').encode(), "DEFINITIONS.INVALID"),
            "two records": ((ttl(definition("x", "t", "x", "docs/r.md", (ADR, None))) + f"a:x0 jj:record <{OTHER}> .\n").encode(), "DEFINITIONS.INVALID"),
            "long term": (ttl(definition("x", "t" * 200, "x", "docs/r.md", (ADR, None))).encode(), "DEFINITIONS.INVALID"),
        }
        valid = self.defs(definition("ok", "fine", "t", "docs/r.md", (ADR, None)), name="ok.definitions.ttl")
        for name, (data, code) in cases.items():
            with self.subTest(name):
                bad = self.root / "bad.definitions.ttl"
                bad.write_bytes(data)
                errors = self.failed(str(bad), valid)
                self.assertEqual([(e["code"], e["file"]) for e in errors], [(code, str(bad))])
                self.assertTrue(all(c["path"] for c in self.doctor(str(bad), valid)[1]["data"]["checked"]))

    def test_a_missing_path_an_unknown_extension_and_bad_json_are_errors(self):
        text = self.root / "notes.txt"
        text.write_text("hi", encoding="utf-8")
        broken = self.root / "broken.json"
        broken.write_text("{", encoding="utf-8")
        other = write(self.root, "other.json", {"hello": 1})
        errors = self.failed(str(self.root / "nope.json"), str(text), str(broken), other)
        self.assertEqual([e["code"] for e in errors], ["INPUT.MISSING", "VALIDATION.INPUT", "INPUT.MALFORMED", "INPUT.MALFORMED"])
        for e in errors:
            self.assertTrue(e["message"])

    def test_an_error_and_a_warning_together_exit_2_and_report_both(self):
        warn = self.defs(definition("x", "fast", "t", "docs/r.md"))
        bad = write(self.root, "cyc.ttl", BRANCH_TTL.replace("jj:goto t:b:done", "jj:goto t:b:wave-1"))
        code, out = self.doctor(warn, bad)
        self.assertEqual(code, 2, out)
        self.assertEqual((self.codes(out, "errors"), self.codes(out, "warnings")), (["QUALITY.TREE"], ["DEFINITION.UNATTACHED"]))

    def test_an_unreadable_index_is_an_error_not_a_traceback(self):
        path = self.defs(definition("x", "fast", "t", "docs/r.md", (ADR, None)))
        for index in (str(self.d / "none.json"), write(self.d, "bad.json", "{"), write(self.d, "arr.json", [])):
            with self.subTest(index):
                code, out = self.doctor(path, "--index", index)
                self.assertEqual(code, 2, out)
                self.assertFalse(out["success"])
                self.assertTrue(out["error"]["code"])


class NoJev(DoctorCase):
    def test_doctor_needs_no_key_and_never_calls_jev(self):
        # env() clears the environment (no key) and call_jev is a stub that fails the test; doctor still reports
        path = self.defs(definition("x", "fast", "t", "docs/r.md", (ADR, None)))
        for argv in ((), (path,), (path, "--index", self.index)):
            code, out = self.doctor(*argv)
            self.assertEqual((code, out["success"]), (0, True), out)
        self.assertNotIn("log", out["data"])

    def test_doctor_is_a_listed_subcommand_with_the_documented_flags(self):
        code, out = self.doctor("--no-such-flag")
        self.assertEqual((code, out["error"]["code"]), (2, "VALIDATION.INPUT"), out)


if __name__ == "__main__":
    unittest.main()
