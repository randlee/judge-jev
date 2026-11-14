"""Controlled wheel boundary checks; native released-wheel behavior is verified separately."""
import unittest
from unittest import mock

import sc_observability as sco
from jev_support import read_log
import jev_judge as jj
from test_jev_batch import BatchCase, PLAN_QS, jsonl, request_line
from test_jev_judge import ScDecidrStub, Transport, consented, run_cli


class WheelLogging(BatchCase):
    def test_optional_logger_is_passed_directly_and_run_events_stay_queryable(self):
        for inject in (False, True):
            with self.subTest(inject=inject):
                captured = {}
                wheel = ScDecidrStub(Transport())
                original = wheel.send_batch

                def send(requests, **kwargs):
                    captured.update(kwargs)
                    if inject:
                        logger = kwargs["general_log"]
                        self.assertIsInstance(logger, sco.Logger)
                        admitted = logger.log(sco.LogEvent(level="info", target="decidr", action="decidr.test_send", fields={"source": "controlled-wheel"}))
                        self.assertIsInstance(admitted, sco.Ok)
                    return original(requests, **kwargs)

                wheel.send_batch = send
                owned = []
                original_open = jj.open_run_log

                def opened(*args, **kwargs):
                    result = original_open(*args, **kwargs)
                    owned.append(result.value._logger)
                    return result

                root = self.d / str(inject)
                argv = ["batch", "--input", self.put("input.jsonl", jsonl([request_line("s1", "text", ("cur", PLAN_QS["questions"]))])),
                        "--run-dir", str(root), "--run-name", "logger-test"]
                if inject:
                    argv.append("--sc-agent-log")
                with consented(), mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(wheel)), mock.patch.object(jj, "open_run_log", side_effect=opened):
                    code, output = run_cli(argv)
                self.assertEqual(code, 0, output)
                self.assertNotIn("session_log", captured, "session log uses the wheel default")
                self.assertNotIn("keyring_service", captured)
                self.assertNotIn("keyring_account", captured)
                if inject:
                    self.assertIs(captured["general_log"], owned[0], "same Logger, no adapter")
                else:
                    self.assertNotIn("general_log", captured, "omission leaves wheel file logging intact")
                events = read_log(root)
                actions = [event["action"] for event in events]
                self.assertEqual(actions, (["decidr.test_send"] if inject else []) + ["request", "answer", "result"])
                self.assertEqual(output["ok"], True)

    def test_public_log_options_own_injection_and_keep_the_logger_alive(self):
        for inject in (False, True):
            with self.subTest(inject=inject):
                root = self.d / ("accessor-" + str(inject))
                log = jj.open_run_log(root, "accessor", inject).value
                try:
                    options = log.sc_agent_log_options()
                    if inject:
                        self.assertIsInstance(options["general_log"], sco.Logger)
                        self.assertIs(options["general_log"], log.sc_agent_log_options()["general_log"])
                        options.clear()  # the caller owns the returned options, not the logger
                        self.assertIn("general_log", log.sc_agent_log_options())
                    else:
                        self.assertEqual(options, {})
                    self.assertIsInstance(log.event("accessor-used", {}), jj.Ok)
                    self.assertIsInstance(log.flush(), jj.Ok)
                finally:
                    self.assertIsInstance(log.close(), jj.Ok)
                self.assertEqual(len(read_log(root, action="accessor-used")), 1)

    def test_consumer_retains_logger_after_wheel_boundary(self):
        log = jj.open_run_log(self.d / "lifetime", "lifetime", True).value
        wheel = ScDecidrStub(Transport())
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        line = request_line("s1", "text", ("cur", PLAN_QS["questions"]))
        try:
            with mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(wheel)):
                result = jj.pump_batch([line], settings, None, log, echo=False)
            self.assertIsInstance(result, jj.Ok)
            self.assertIsInstance(log.event("after-send", {"still_owned": True}), jj.Ok)
            self.assertIsInstance(log.flush(), jj.Ok)
        finally:
            self.assertIsInstance(log.close(), jj.Ok)
        self.assertIn("after-send", [event["action"] for event in read_log(self.d / "lifetime")])


class QualityLoggerLifetime(unittest.TestCase):
    def test_interrupt_closes_the_owned_run_logger(self):
        import tempfile
        from pathlib import Path
        from test_quality import INDEX
        from test_jev_judge import write
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = write(root, "index.json", INDEX)
            owned = []
            original_open = jj.open_run_log

            def opened(*args, **kwargs):
                result = original_open(*args, **kwargs)
                close = mock.Mock(wraps=result.value.close)
                result.value.close = close
                owned.append(close)
                return result

            with consented(), mock.patch.object(jj, "open_run_log", side_effect=opened), \
                    mock.patch.object(jj, "walk_tree", side_effect=KeyboardInterrupt):
                code, output = run_cli(["quality", "--adr", "ADR-T-0001", "--index", index,
                                        "--run-dir", str(root / "logs"), "--sc-agent-log"])
            self.assertEqual((code, output["error"]["code"]), (130, "CANCELED"))
            self.assertEqual(len(owned), 1)
            owned[0].assert_called_once_with()
