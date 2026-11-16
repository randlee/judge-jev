"""Typed sc-agent exceptions stay inside judge-jev's error contract; no provider transport is implemented here."""
import json
import unittest
from unittest import mock

from jev_support import SCRIPTS  # noqa: F401
import jev_judge as jj  # noqa: E402
import decidr_client  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
