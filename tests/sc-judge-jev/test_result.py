"""Tests for the Result<T, E> helpers and how expected failures propagate through the scripts.

result.py is the shared discriminated union (Ok / Err, ToolError, err). The
scripts return Err for every expected failure; only their CLI boundary turns
an Err into a JSON envelope and an exit code. These tests pin both halves.
Standard library only.
"""
import contextlib
import dataclasses
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
from layout_support import SCRIPTS  # noqa: E402 - the scripts as installed
sys.path.insert(0, str(SCRIPTS))
import judge_jev_paths as jp  # noqa: E402
import judge_jev_settings as js  # noqa: E402
import result  # noqa: E402
from result import Err, Ok, ToolError, err  # noqa: E402


class ResultHelperTests(unittest.TestCase):
    def test_ok_and_err_are_discriminated_by_the_ok_literal(self):
        self.assertIs(Ok(1).ok, True)
        self.assertIs(Err("x").ok, False)
        self.assertEqual(Ok(1).value, 1)
        self.assertEqual(Err("x").error, "x")
        self.assertNotIsInstance(Ok(1), Err)
        self.assertNotIsInstance(Err("x"), Ok)

    def test_variants_are_frozen_value_objects(self):
        self.assertEqual(Ok([1]), Ok([1]))
        self.assertNotEqual(Ok(1), Err(1))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            Ok(1).value = 2
        with self.assertRaises(TypeError):
            Ok(1, ok=False)  # the discriminant is not settable

    def test_tool_error_envelope_and_err_helper(self):
        made = err("CODE.X", "went wrong", "do this", {"k": 1})
        self.assertIsInstance(made, Err)
        self.assertEqual(made.error, ToolError("CODE.X", "went wrong", "do this", {"k": 1}))
        self.assertEqual(list(made.error.to_json().items()),
                         [("code", "CODE.X"), ("message", "went wrong"), ("recoverable", False), ("suggested_action", "do this")])
        self.assertIsNone(err("C", "m").error.to_json()["suggested_action"])

    def test_scripts_share_one_result_module(self):
        self.assertIs(js.Ok, result.Ok)
        self.assertIs(js.Err, result.Err)
        self.assertIs(js.find_settings, jp.find_settings)


class SettingsPropagationTests(unittest.TestCase):
    """An Err from the settings code becomes one envelope in main."""

    def run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = js.main(argv)
        return code, json.loads(buf.getvalue())

    def test_main_emits_an_err_as_the_envelope_and_exits_2(self):
        failed = err("SETTINGS.MALFORMED", "bad", "fix it")
        with mock.patch.object(js, "show", return_value=failed):
            code, out = self.run_main(["show"])
        self.assertEqual(code, 2)
        self.assertEqual(set(out), {"success", "data", "error"})
        self.assertEqual((out["success"], out["error"]["code"]), (False, "SETTINGS.MALFORMED"))

    def test_main_reports_an_unexpected_exception_as_script_internal(self):
        with mock.patch.object(js, "show", side_effect=RuntimeError("boom")):
            code, out = self.run_main(["show"])
        self.assertEqual((code, out["error"]["code"], out["error"]["message"]), (2, "SCRIPT.INTERNAL", "RuntimeError: boom"))

    def test_a_folder_outside_any_repository_is_an_err_value(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(js, "_git_toplevel", return_value=None):
            found = js.find_repo_root(Path(td))
        self.assertIsInstance(found, Err)


if __name__ == "__main__":
    unittest.main()
