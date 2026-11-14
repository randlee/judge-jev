"""Result ordering/serialization driven by explicit gates, never sleeps or scheduling assumptions.

The 30-second waits only turn a broken handshake into a failure; elapsed time is not evidence.
"""
import json
import threading
import types
from unittest import mock

from jev_support import log_lines, read_log
import jev_judge as jj
from test_jev_batch import BatchCase, PLAN_QS, WheelCancelToken, request_line
from test_jev_judge import plan_answers


class WheelDelivery(BatchCase):
    def test_concurrent_out_of_order_callbacks_and_returned_replay_emit_once(self):
        first_converting = threading.Event()
        release_first = threading.Event()
        second_waiting = threading.Event()
        converted, stdout, failures = [], [], []
        original_convert = jj._sc_agent_result
        test = self

        class ObservedLock:
            def __init__(self):
                self.lock = threading.Lock()
                self.calls = 0
            def __enter__(self):
                self.calls += 1
                if self.calls == 2:
                    second_waiting.set()
                self.lock.acquire()
                return self
            def __exit__(self, *_):
                self.lock.release()

        accept_lock = ObservedLock()

        def convert(job, settings, result):
            converted.append(result["position"])
            if result["position"] == 1:
                first_converting.set()
                if not release_first.wait(30):
                    raise AssertionError("first conversion was never released")
            return original_convert(job, settings, result)

        class ControlledWheel:
            CancelToken = WheelCancelToken
            def send_batch(self, requests, *, on_result, **kwargs):
                results = [{"position": i, "response": {"model": "controlled", "answers": plan_answers()}}
                           for i in (1, 0)]
                def deliver(result):
                    try:
                        on_result(result)
                    except BaseException as exc:
                        failures.append(exc)
                first = threading.Thread(target=deliver, args=(results[0],))
                second = threading.Thread(target=deliver, args=(results[1],))
                first.start()
                try:
                    test.assertTrue(first_converting.wait(30), "first callback did not enter conversion")
                    second.start()
                    test.assertTrue(second_waiting.wait(30), "second callback did not reach the delivery lock")
                    test.assertEqual(converted, [1], "a second callback entered conversion while the first held the lock")
                finally:
                    release_first.set()
                    first.join(30)
                    if second.ident is not None:
                        second.join(30)
                test.assertFalse(first.is_alive(), "first callback did not complete")
                test.assertFalse(second.is_alive(), "second callback did not complete")
                test.assertEqual(failures, [])
                # The real wheel returns the same results after delivering callbacks.
                return results

        request = request_line("i", "text", ("c0", PLAN_QS["questions"]), ("c1", PLAN_QS["questions"]))
        settings = jj.BatchSettings("plan", "jev-latest", 1, "p", 0.6, 30.0, 1, 24000, False)
        log = jj.open_run_log(self.d, "delivery").value
        try:
            with mock.patch.object(jj, "sc_agent_module", return_value=jj.Ok(ControlledWheel())), \
                    mock.patch.object(jj, "threading", types.SimpleNamespace(Lock=lambda: accept_lock)), \
                    mock.patch.object(jj, "_sc_agent_result", side_effect=convert), \
                    mock.patch.object(jj, "write_stdout_line", side_effect=stdout.append):
                result = jj.pump_batch([request], settings, None, log, echo=True)
        finally:
            log.close()
        self.assertIsInstance(result, jj.Ok, result)
        self.assertEqual(converted, [1, 0])
        self.assertEqual([line["candidate_id"] for line in result.value], ["c0", "c1"])
        self.assertEqual([json.loads(line) for line in stdout], result.value)
        self.assertEqual(log_lines(self.d), result.value)
        for action in ("request", "answer", "result"):
            self.assertEqual(len(read_log(self.d, action=action)), 2)
