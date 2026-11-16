"""Typed sc-agent exceptions stay inside judge-jev's error contract; no provider transport is implemented here."""
import json
import unittest
from unittest import mock

from jev_support import SCRIPTS  # noqa: F401
import jev_judge as jj  # noqa: E402
import decidr_client  # noqa: E402


class SagErrorCompatibility(unittest.TestCase):
    def call_with(self, exc):
        with mock.patch.object(jj, "_new_cancel_token", return_value=mock.Mock()), \
                mock.patch.object(decidr_client, "call", side_effect=exc):
            return jj.call_jev({"model": "jev-latest", "state": {}, "questions": {}}, 30)

    def test_auth_sag_error_is_typed_and_redacted(self):
        exc = RuntimeError("provider failure")
        exc.id = "auth.credentials"
        exc.category = "auth"
        exc.message = "Bearer secret-token"
        exc.detail = json.dumps({"id": exc.id, "category": exc.category, "attempts": 1})
        got = self.call_with(exc)
        self.assertIsInstance(got, jj.Err)
        self.assertEqual(got.error.code, "AUTH.CREDENTIALS")
        self.assertNotIn("secret-token", got.error.message)

    def test_context_sag_error_maps_from_decision_identifier(self):
        exc = RuntimeError("request too large")
        exc.id = "decision.context_exceeded"
        exc.category = "validation"
        exc.message = "request too large"
        exc.detail = json.dumps({"id": exc.id, "category": exc.category, "attempts": 2})
        got = self.call_with(exc)
        self.assertIsInstance(got, jj.Err)
        self.assertEqual((got.error.code, got.error.recoverable, got.error.meta["attempts"]),
                         ("JEV.CONTEXT_EXCEEDED", True, 2))


if __name__ == "__main__":
    unittest.main()
