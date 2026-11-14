"""Guard judge-jev preserving already-redacted native detail in stdout and its log.

The frozen capture came from an offline HTTP-layer probe using published Rust
crates 0.1.0 (source 7afe38348fd736bcb6a0cfb632c25c7c20e60327). CI replays the
capture; it does not regenerate it. Fixture/sentinel checks below validate the
input's shape and isolation only, not native redaction. This test does not
prove the wheel guarantee or cover config, decision, credential-resolution or
Python-boundary native errors; those paths are tracked by B-1 agt-b-1.10.
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
    def test_consumer_preserves_already_redacted_detail_in_stdout_and_log(self):
        captured = json.loads((Path(__file__).parent / "fixtures" / "native-keyring-redaction" / "detail.json").read_text())
        self.assertEqual(captured["credential_source"], "keyring")
        detail = captured["detail"]
        sentinel = "sk-controlled-keyring-redaction-sentinel-77"
        # Frozen-input checks only: the consumer behavior is asserted below.
        native_text = json.dumps(detail)
        self.assertNotIn(sentinel, native_text)
        self.assertEqual(native_text.count("[redacted]"), 3)
        # No Bearer prefix or environment credential can change this fixture
        # through Python scrubbing; the assertions below compare detail exactly.
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
