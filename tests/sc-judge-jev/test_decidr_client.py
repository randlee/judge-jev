"""Exercise the installed consumer through a controlled public wheel surface."""
import json
import sys
import types
import unittest
from unittest import mock

import jev_support  # noqa: F401  (render and install the scripts on sys.path)
import decidr_client
import jev_judge


class ConsumerAdoptionTests(unittest.TestCase):
    def test_judge_imports_rendered_client(self):
        self.assertIs(jev_judge.decidr_client, decidr_client)
        self.assertEqual(decidr_client.SC_DECIDR_VERSION, "0.2.0")
        self.assertFalse(hasattr(decidr_client, "extract"))

    def test_single_and_batch_use_public_wheel_api_with_keyring_overrides(self):
        wheel = types.ModuleType("sc_agent")
        wheel.SagError = type("SagError", (Exception,), {})
        line = json.dumps({"response": {"answers": {}}})
        wheel.send = mock.Mock(return_value=line)
        wheel.send_batch = mock.Mock(return_value=[line, line])
        wheel.category = mock.Mock()
        cancel = mock.Mock()
        options = dict(model="jev", project="judge-jev", agent_role="quality",
                       abort_on=frozenset(), category_codes={}, cancel=cancel,
                       keyring_service="plan-anchor", keyring_account="typesafe-api-key")
        with mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            self.assertEqual(decidr_client.call("one", **options), (line, None))
            self.assertEqual(decidr_client.call_batch(["one", "two"], **options), [(line, None), (line, None)])
        for operation in (wheel.send, wheel.send_batch):
            args = operation.call_args.kwargs
            self.assertEqual(args["keyring_service"], "plan-anchor")
            self.assertEqual(args["keyring_account"], "typesafe-api-key")
            self.assertEqual(args["project"], "judge-jev")
            self.assertEqual(args["agent_role"], "quality")
            self.assertIs(args["cancel"], cancel)
            self.assertNotIn("provider", args)
            self.assertNotIn("general_log", args)
        wheel.category.assert_not_called()

    def test_auth_error_line_maps_category_and_cancels(self):
        wheel = types.ModuleType("sc_agent")
        wheel.SagError = type("SagError", (Exception,), {})
        line = json.dumps({"error": {"id": "auth", "category": "auth"}})
        wheel.send = mock.Mock(return_value=line)
        wheel.category = mock.Mock(return_value="auth")
        cancel = mock.Mock()
        with mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            result = decidr_client.call("one", model="jev", project="judge-jev",
                                       agent_role="quality", abort_on=frozenset({"auth"}),
                                       category_codes={"auth": "AUTH"}, cancel=cancel)
        self.assertEqual(result, (line, "AUTH"))
        cancel.cancel.assert_called_once_with()
        self.assertEqual(json.loads(wheel.category.call_args.args[0])["category"], "auth")

    def test_sag_error_category_cancels_and_propagates(self):
        wheel = types.ModuleType("sc_agent")
        wheel.SagError = type("SagError", (Exception,), {})
        error = wheel.SagError("denied")
        error.category = "auth"
        wheel.send = mock.Mock(side_effect=error)
        cancel = mock.Mock()
        with mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            with self.assertRaises(wheel.SagError) as caught:
                decidr_client.call("one", model="jev", project="judge-jev",
                                   agent_role="quality", abort_on=frozenset({"auth"}),
                                   category_codes={}, cancel=cancel)
        self.assertIs(caught.exception, error)
        cancel.cancel.assert_called_once_with()

    def test_keyboard_interrupt_cancels_and_propagates(self):
        wheel = types.ModuleType("sc_agent")
        wheel.SagError = type("SagError", (Exception,), {})
        wheel.send = mock.Mock(side_effect=KeyboardInterrupt)
        cancel = mock.Mock()
        with mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            with self.assertRaises(KeyboardInterrupt):
                decidr_client.call("one", model="jev", project="judge-jev",
                                   agent_role="quality", abort_on=frozenset(),
                                   category_codes={}, cancel=cancel)
        cancel.cancel.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
