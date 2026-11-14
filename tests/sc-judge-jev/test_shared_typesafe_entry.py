"""Controlled consumer-boundary proof of the shared entry, without credential lookup.

The stand-in supplies a controlled current account and the documented wheel
TypeSafe defaults. This tests selection and override omission only; precedence
and the real platform store remain agt-bjj-1.f-n4-precedence / agt-r17 work.
"""
from unittest import mock

from jev_support import read_log
import jev_judge as jj
from test_jev_batch import BatchCase, PLAN_QS, jsonl, request_line
from test_jev_judge import ScDecidrStub, Transport, consented, run_cli


class SharedTypeSafeEntry(BatchCase):
    def test_default_jev_selection_keeps_the_entry_shared_with_plan_anchor(self):
        default_entry = ("TYPESAFE_API_KEY", "controlled-current-account")
        for inject in (False, True):
            with self.subTest(inject=inject):
                observed = []
                wheel = ScDecidrStub(Transport())
                send_batch = wheel.send_batch

                def send(requests, **kwargs):
                    # `jev` selects TypeSafe in the published wheel catalog.
                    self.assertEqual(kwargs["model"], "jev")
                    self.assertNotIn("provider", kwargs)
                    self.assertNotIn("keyring_service", kwargs)
                    self.assertNotIn("keyring_account", kwargs)
                    self.assertNotIn("api_key", kwargs)
                    # Resolve only the identity in this controlled stand-in,
                    # never a password or an OS keychain entry.
                    identity = (kwargs.get("keyring_service", default_entry[0]),
                                kwargs.get("keyring_account", default_entry[1]))
                    observed.append(("typesafe", identity))
                    return send_batch(requests, **kwargs)

                wheel.send_batch = send
                root = self.d / str(inject)
                source = self.put("input.jsonl", jsonl([request_line("i", "text", ("cur", PLAN_QS["questions"]))]))
                argv = ["batch", "--input", source, "--run-dir", str(root), "--run-name", "shared-entry"]
                if inject:
                    argv.append("--sc-agent-log")
                with consented(), mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(wheel)):
                    code, result = run_cli(argv)
                self.assertEqual((code, result["ok"]), (0, True), result)
                self.assertEqual(observed, [("typesafe", default_entry)])
                self.assertEqual(len(read_log(root, action="result")), 1)
