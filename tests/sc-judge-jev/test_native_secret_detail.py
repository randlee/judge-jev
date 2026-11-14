"""Consumer output/log coverage using actual offline native-library redaction output.

The fixture producer uses released Rust crates 0.1.0 (sc-decidr 0.1.0's source
7afe38348fd736bcb6a0cfb632c25c7c20e60327), injected KeyringSource and automatic
HttpClient error redaction. This is not a live wheel or OS-keyring test.
"""
import json
import os
from pathlib import Path
import types
from unittest import mock

from jev_support import log_lines, read_log
import jev_judge as jj
from test_jev_batch import BatchCase, PLAN_QS, WheelCancelToken, request_line


class NativeSecretDetail(BatchCase):
    def test_keyring_resolved_native_detail_stays_redacted_in_stdout_and_log(self):
        captured = json.loads((Path(__file__).parent / "fixtures" / "native-keyring-redaction" / "detail.json").read_text())
        self.assertEqual(captured["credential_source"], "keyring")
        detail = captured["detail"]
        sentinel = "sk-controlled-keyring-redaction-sentinel-77"
        native_text = json.dumps(detail)
        self.assertNotIn(sentinel, native_text)
        self.assertEqual(native_text.count("[redacted]"), 3)
        # No Bearer prefix: this regression cannot pass through the Python
        # Bearer-token heuristic, and no environment key registers the sentinel.
        self.assertNotIn("bearer", native_text.lower())
        stdout = []

        def replay(requests, **kwargs):
            self.assertEqual(len(list(requests)), 1)
            return [{"position": 0, "error": detail}]

        wheel = types.SimpleNamespace(CancelToken=WheelCancelToken, send_batch=replay)
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        request = request_line("item", "text", ("cur", PLAN_QS["questions"]))
        log = jj.open_run_log(self.d, "native-secret-detail").value
        try:
            with mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}), \
                    mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(wheel)), \
                    mock.patch.object(jj, "write_stdout_line", side_effect=stdout.append):
                result = jj.pump_batch([request], settings, None, log, echo=True)
        finally:
            log.close()
        self.assertIsInstance(result, jj.Ok, result)
        self.assertEqual(len(result.value), 1)
        self.assertEqual(result.value[0]["error"]["detail"], detail)
        self.assertEqual([json.loads(line) for line in stdout], result.value)
        self.assertEqual(log_lines(self.d), result.value)
        events = read_log(self.d)
        emitted = json.dumps({"stdout": stdout, "events": events})
        self.assertNotIn(sentinel, emitted)
        self.assertIn("[redacted]", emitted)
