"""Typed sc-agent exceptions stay inside judge-jev's error contract; no provider transport is implemented here."""
import json
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jev_support import SCRIPTS  # noqa: F401
import jev_judge as jj  # noqa: E402
import decidr_client  # noqa: E402
import judge_jev_settings as settings  # noqa: E402
from result import run_main  # noqa: E402
from test_jev_judge import run_cli, write  # noqa: E402
import test_jev_batch as batch_helpers  # noqa: E402
from test_quality import INDEX  # noqa: E402
from test_definitions import ADR, definition, iri, ttl  # noqa: E402


class SharedClientFailureCompatibility(unittest.TestCase):
    def call_with(self, record):
        with mock.patch.object(decidr_client, "call_result", return_value=record):
            return jj.call_jev({"model": "jev-latest", "state": {}, "questions": {}}, 30)

    def test_auth_result_is_typed_and_redacted(self):
        record = {"ok": False, "position": None, "line": None, "attempts": 1,
                  "error": {"code": "AUTH.CREDENTIALS", "message": "Bearer secret-token", "retryable": False,
                            "action": "Check credentials.", "status": 401, "retry_after_ms": None,
                            "attempts": 1, "data": {"id": "auth.credentials"}}}
        got = self.call_with(record)
        self.assertIsInstance(got, jj.Err)
        self.assertEqual(got.error.code, "AUTH.CREDENTIALS")
        self.assertNotIn("secret-token", got.error.message)

    def test_context_result_uses_shared_category_code(self):
        record = {"ok": False, "position": None, "line": None, "attempts": 2,
                  "error": {"code": "JEV.CONTEXT_EXCEEDED", "message": "request too large", "retryable": True,
                            "action": "Shorten evidence.", "status": None, "retry_after_ms": None,
                            "attempts": 2, "data": {"id": "decision.context_exceeded"}}}
        got = self.call_with(record)
        self.assertIsInstance(got, jj.Err)
        self.assertEqual((got.error.code, got.error.recoverable, got.error.meta["attempts"]),
                         ("JEV.CONTEXT_EXCEEDED", True, 2))


class Interrupts(unittest.TestCase):
    def assert_canceled(self, result):
        code, output = result
        self.assertEqual(code, 130)
        self.assertEqual((output["success"], output["data"], output["error"]["code"]),
                         (False, None, "CANCELED"))

    def test_judge_input_interrupt_returns_canceled(self):
        with mock.patch.object(jj, "read_request_lines", side_effect=KeyboardInterrupt):
            self.assert_canceled(run_cli(["batch", "--input", "input.jsonl", "--run-dir", "runs", "--dry-run"]))

    def test_settings_input_interrupt_returns_canceled(self):
        output = io.StringIO()
        with mock.patch.object(settings, "show", side_effect=KeyboardInterrupt), contextlib.redirect_stdout(output):
            code = run_main(lambda: settings.main(["show"]))
        envelope = json.loads(output.getvalue())
        self.assertEqual((code, envelope["success"], envelope["data"], envelope["error"]["code"]),
                         (130, False, None, "CANCELED"))

    def test_batch_interrupt_closes_owned_log_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = write(root, "input.jsonl", batch_helpers.jsonl(batch_helpers.BatchTests.LINES))
            answers = write(root, "answers.json", batch_helpers.BatchTests.FIXTURE)
            log = mock.Mock()
            with mock.patch.object(jj, "open_run_log", return_value=jj.Ok(log)), \
                    mock.patch.object(jj, "pump_batch", side_effect=KeyboardInterrupt):
                self.assert_canceled(run_cli(["batch", "--input", source, "--run-dir", str(root / "logs"),
                                               "--answers-file", answers]))
            log.close.assert_called_once_with()

    def test_quality_interrupt_closes_owned_log_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = write(root, "index.json", INDEX)
            answers = write(root, "answers.json", {"*": {}})
            log = mock.Mock()
            with mock.patch.object(jj, "open_run_log", return_value=jj.Ok(log)), \
                    mock.patch.object(jj, "walk_tree", side_effect=KeyboardInterrupt):
                self.assert_canceled(run_cli(["quality", "--adr", "ADR-T-0001", "--index", index,
                                               "--run-dir", str(root / "logs"), "--answers-file", answers]))
            log.close.assert_called_once_with()

    def test_compare_interrupt_closes_each_open_arm_log_once(self):
        for interrupted_arm in (0, 1):
            with self.subTest(arm=interrupted_arm), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                index = write(root, "index.json", INDEX)
                defs = write(root, "defs.ttl", ttl(definition("fast", "fast", "Under 5 s.", "docs/r.md", (ADR, None))))
                answers = write(root, "answers.json", {"*": {}})
                logs = [mock.Mock(), mock.Mock()]
                for log in logs:
                    log.close.return_value = jj.Ok(None)
                walks = [jj.Ok(("yes", [], []))] * interrupted_arm + [KeyboardInterrupt()]
                with mock.patch.object(jj, "open_run_log", side_effect=[jj.Ok(log) for log in logs]), \
                        mock.patch.object(jj, "walk_tree", side_effect=walks):
                    self.assert_canceled(run_cli(["compare-definition", "--adr", "ADR-T-0001", "--index", index,
                                                   "--definitions", defs, "--definition", iri("fast"),
                                                   "--run-dir", str(root / "logs"), "--answers-file", answers]))
                for log in logs[:interrupted_arm + 1]:
                    log.close.assert_called_once_with()
                if interrupted_arm == 0:
                    logs[1].close.assert_not_called()

    def test_compare_final_event_interrupt_closes_final_log_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = write(root, "index.json", INDEX)
            defs = write(root, "defs.ttl", ttl(definition("fast", "fast", "Under 5 s.", "docs/r.md", (ADR, None))))
            answers = write(root, "answers.json", {"*": {}})
            logs = [mock.Mock() for _ in range(3)]
            for log in logs:
                log.close.return_value = jj.Ok(None)
            logs[2].event.side_effect = KeyboardInterrupt
            with mock.patch.object(jj, "open_run_log", side_effect=[jj.Ok(log) for log in logs]), \
                    mock.patch.object(jj, "walk_tree", return_value=jj.Ok(("yes", [], []))):
                self.assert_canceled(run_cli(["compare-definition", "--adr", "ADR-T-0001", "--index", index,
                                               "--definitions", defs, "--definition", iri("fast"),
                                               "--run-dir", str(root / "logs"), "--answers-file", answers]))
            for log in logs:
                log.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
