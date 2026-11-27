"""The v2 client and judge-jev's Run-based batch contract."""
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
from unittest.mock import patch

from jev_support import SCRIPTS  # noqa: F401: renders the installed scripts
import jev_judge as judge
import jev_runs
import decidr_client
from pathlib import Path
from sc_agent.testing import FakeRun


class ClientRunTests(unittest.TestCase):
    def setUp(self):
        self.run = FakeRun({"provider": "local", "run_id": "test-run"})
        self.settings = judge.BatchSettings("plan", 1, "test", .6, False)
        self.request = {"item": {"id": "item", "text": "statement-canary"},
                        "questions": [{"candidate_id": "candidate", "questions": {
                            "q": {"type": "noul", "instructions": "score"}}}]}

    def test_fixture_batch_runs_through_a_run_and_logs_result_events(self):
        result = judge.judge_batch(self.run, [self.request], self.settings,
            fixture={"*": {"q": {"noul": .5}}}, echo=False, fields={"run": "test"})
        self.assertTrue(result.ok, result)
        line, answers = result.value[0]
        self.assertEqual((line.schema, line.run_id, line.session_id), ("jev-batch-result/2", "test-run", None))
        self.assertEqual(answers["q"].noul, .5)
        self.assertEqual(self.run.sent, [])
        self.assertEqual(len(self.run.logged), 1)
        event = self.run.logged[0]
        self.assertEqual(event["action"], "result")
        self.assertEqual(event["correlation_id"], "test-run")
        self.assertEqual(event["fields"]["item_id"], "item")
        self.assertNotIn("statement-canary", json.dumps(event))
        self.assertNotIn("answers", event["fields"])
        self.assertNotIn("request", event["fields"])

    def test_out_of_order_callbacks_are_logged_and_returned_in_input_order(self):
        original = judge.decidr_client.run_batch
        def reverse_callbacks(run, jobs, settings, **kwargs):
            deliver = kwargs["on_line"]
            captured = []
            kwargs["on_line"] = lambda line, answers: captured.append((line, answers))
            result = original(run, jobs, settings, **kwargs)
            for line, answers in reversed(captured):
                deliver(line, answers)
            return result
        second = dict(self.request, item={"id": "second", "text": "another"})
        with patch.object(judge.decidr_client, "run_batch", side_effect=reverse_callbacks):
            result = judge.judge_batch(self.run, [self.request, second], self.settings,
                fixture={"*": {"q": {"noul": .5}}}, echo=False)
        self.assertTrue(result.ok, result)
        self.assertEqual([line.request_id.split("/")[1] for line, _ in result.value], ["item", "second"])
        self.assertEqual([event["fields"]["item_id"] for event in self.run.logged], ["item", "second"])

    def test_dry_run_opens_no_run_and_writes_no_event(self):
        settings = self.settings._replace(dry_run=True)
        result = judge.judge_batch(None, [self.request], settings, fixture=None, echo=False)
        self.assertTrue(result.ok)
        self.assertEqual(result.value, [])
        self.assertEqual(self.run.logged, [])

    def test_log_failure_is_returned_with_original_code(self):
        def fail(_):
            return {"ok": False, "error": {"id": "log.write", "category": "log", "message": "controlled sink failure"}}
        self.run.log = fail
        result = judge.judge_batch(self.run, [self.request], self.settings,
            fixture={"*": {"q": {"noul": .5}}}, echo=False)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "DECIDR.LOG")
        self.assertIn("controlled sink failure", result.error.message)

    def test_rebuild_reads_answers_from_sessions(self):
        line = {"record_id": "REQ-1", "request_id": "r1", "session_id": "s1", "tree_sha256": "abc"}
        events = {"result": [line], "statement": [],
                  "wave": [{"record_id": "REQ-1", "node": "n", "request_id": "r1"}],
                  "verdict": [{"record_id": "REQ-1", "verdict": "pass"}]}
        answers = {"r1": {"q": {"noul": 0.5}}}
        with patch.object(jev_runs, "read_run_events", return_value=judge.Ok(events)), \
             patch.object(decidr_client, "answers_for", return_value=judge.Ok(answers)) as lookup, \
             patch.object(jev_runs, "run_triples", return_value=[]) as project:
            result = jev_runs.rebuild_from_log("test", {}, log_file=Path("test.jsonl"))
        self.assertTrue(result.ok, result)
        lookup.assert_called_once_with([line])
        self.assertEqual(project.call_args.args[2][0]["answers"], answers["r1"])

    def test_real_wheel_cache_and_session_answer_recovery_on_loopback(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                payload = json.dumps({"model": "jev-1.14.0", "answers": {"q": {"type": "noul", "noul": .5}}}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as root, \
                    patch.dict(os.environ, {"JUDGE_JEV_LOG_ROOT": root, "SC_PROJECT": "j6-test", "TYPESAFE_API_KEY": "test-credential"}), \
                    patch.object(decidr_client, "remote_judge_consent", return_value=judge.Ok(None)):
                opened = decidr_client.open_run(model="jev", config_dir=root,
                    seams={"base_url": f"http://127.0.0.1:{server.server_port}/v1"})
                self.assertTrue(opened.ok, opened)
                with opened.value as run:
                    first = judge.judge_batch(run, [self.request], self.settings, fixture=None, echo=False)
                    second = judge.judge_batch(run, [self.request], self.settings, fixture=None, echo=False)
                self.assertTrue(first.ok and second.ok, (first, second))
                first_line, _ = first.value[0]
                second_line, _ = second.value[0]
                self.assertTrue(first_line.ok and second_line.ok, (first_line, second_line))
                self.assertTrue(first_line.session_id)
                self.assertEqual(first_line.session_id, second_line.session_id)
                self.assertEqual(len(received), 1)
                lookup = decidr_client.answers_for([json.loads(decidr_client.encode_result_line(second_line))])
                self.assertTrue(lookup.ok, lookup)
                self.assertEqual(lookup.value[second_line.request_id]["q"]["noul"], .5)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_model_and_no_cache_are_forwarded_to_open_run(self):
        parser = judge.build_parser()
        args = parser.parse_args(["quality", "--req", "REQ-1", "--index", "index.json", "--model", "haiku", "--no-cache"])
        with patch.object(judge.decidr_client, "open_run", return_value=judge.Ok(self.run)) as opened:
            judge.open_command_run(args, timeout_secs=7, workers=2, cache=False)
        self.assertEqual(opened.call_args.kwargs, {"model": "haiku", "cache": False, "timeout_secs": 7, "workers": 2})
        self.assertTrue(args.no_cache)
