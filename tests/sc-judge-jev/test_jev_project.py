"""Project forwarding and upstream refusal handling; controlled clients, no live calls."""
import contextlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

import jev_support  # noqa: F401
import jev_judge as jj
from test_definitions import ADR, definition, iri, ttl
from test_jev_judge import request_line, run_cli, wheel_record, write
from test_quality import INDEX


class ProjectTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        environment = {"HOME": str(self.root), "USERPROFILE": str(self.root),
                       "JUDGE_JEV_LOG_ROOT": str(self.root / "logs"), "PATH": os.environ.get("PATH", "")}
        patcher = mock.patch.dict(os.environ, environment, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)
        index = write(self.root, "index.json", INDEX)
        stream = write(self.root, "requests.jsonl", json.dumps(request_line()) + "\n")
        definitions = write(self.root, "terms.ttl", ttl(definition("fast", "fast", "Under 5 s.", "docs/r.md", (ADR, None))))
        self.commands = [
            ["quality", "--index", index, "--adr", "ADR-T-0001"],
            ["batch", "--input", stream],
            ["drift", "--old-index", index, "--new-index", index, "--adr", "ADR-T-0001",
             "--controls", "0", "--question-set", "brief"],
            ["compare-definition", "--index", index, "--adr", "ADR-T-0001",
             "--definitions", definitions, "--definition", iri("fast")],
        ]

    @staticmethod
    def answers(questions):
        return {qid: {"type": "choice", "choice": next(iter(q["criteria"])), "confidence": 1.,
                      "probabilities": {choice: float(i == 0) for i, choice in enumerate(q["criteria"])}}
                for qid, q in questions.items()}

    @staticmethod
    def refusal():
        return jj.ClientError("DECIDR.CONFIG", "Set the upstream project", data={"id": "config.missing_project"})

    def transport(self, requests, **kwargs):
        self.projects.append(kwargs["project"])
        records = [wheel_record((json.dumps({"response": {"model": "controlled", "answers": self.answers(request["questions"])},
                                            "sends": 1}), None), i) for i, request in enumerate(requests)]
        for record in records:
            kwargs["on_result"](record)
        return {"ok": True, "value": records}

    def test_every_live_command_help_lists_project(self):
        for command in self.commands:
            with self.subTest(command=command[0]), contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(SystemExit) as stopped:
                    jj.main([command[0], "--help"])
                self.assertEqual(stopped.exception.code, 0)
                self.assertIn("--project", output.getvalue())

    def test_explicit_project_and_none_reach_the_client_for_all_commands(self):
        os.environ["SC_PROJECT"] = "upstream-environment"
        for extra, expected in ((["--project", "chosen"], "chosen"), ([], None), (["--project", ""], None)):
            for command in self.commands:
                self.projects = []
                with self.subTest(extra=extra, command=command[0]), \
                        mock.patch.object(jj.decidr_client, "remote_preflight", return_value={"ok": True, "value": None}), \
                        mock.patch.object(jj.decidr_client, "call_batch_results", side_effect=self.transport) as batch, \
                        mock.patch.object(jj.decidr_client, "call_result") as single:
                    code, output = run_cli([*command, *extra])
                    self.assertEqual(code, 0, output)
                    self.assertTrue(batch.called)
                    single.assert_not_called()
                    self.assertTrue(self.projects)
                    self.assertEqual(set(self.projects), {expected})

    def test_first_missing_project_refusal_stops_every_command_with_one_client_call(self):
        commands = [list(command) for command in self.commands]
        commands[0] += ["--req", "REQ-T-0001"]  # Multiple statements and a later record must not continue.
        commands[2] += ["--controls", "3"]
        for form in ("batch-error", "callback-error"):
            def refuse(requests, **kwargs):
                self.assertIsNone(kwargs["project"])
                self.assertEqual(kwargs["abort_on"], frozenset({"auth"}))
                self.assertIsNotNone(kwargs["cancel"])
                error = self.refusal()
                if form == "batch-error":
                    return {"ok": False, "error": error}
                record = {"ok": False, "error": error, "position": 0}
                kwargs["on_result"](record)
                return {"ok": True, "value": [record]}
            for command in commands:
                with self.subTest(form=form, command=command[0]), \
                        mock.patch.object(jj.decidr_client, "remote_preflight", return_value={"ok": True, "value": None}), \
                        mock.patch.object(jj.decidr_client, "call_batch_results", side_effect=refuse) as batch, \
                        mock.patch.object(jj.decidr_client, "call_result") as single:
                    code, output = run_cli(command)
                    self.assertEqual(code, 2, output)
                    self.assertEqual(output["error"]["code"], "DECIDR.CONFIG")
                    for field in ("message", "suggested_action"):
                        self.assertIn("--project", output["error"][field])
                        self.assertIn("SC_PROJECT", output["error"][field])
                    batch.assert_called_once()
                    single.assert_not_called()

    def test_only_missing_project_cancels_the_controlled_pending_queue(self):
        class Cancel:
            canceled = False
            def cancel(self):
                self.canceled = True
        for identifier in ("config.missing_project", "config.invalid"):
            attempted = []
            def send_batch(requests, *, cancel, on_result, **kwargs):
                rows = []
                for i, _request in enumerate(requests):
                    if cancel.canceled:
                        detail = {"id": "decision.cancelled", "category": "cancelled", "message": "canceled"}
                    else:
                        attempted.append(i)
                        detail = {"id": identifier, "category": "config", "message": "controlled refusal"}
                    result = {"ok": False, "error": detail}
                    rows.append({"index": i, "result": result})
                    on_result(i, result)
                return {"ok": True, "value": rows}
            wheel = SimpleNamespace(Cancel=Cancel, logger=mock.Mock(), flush=mock.Mock(),
                                    send_batch=mock.Mock(side_effect=send_batch))
            with self.subTest(identifier=identifier), mock.patch.dict(sys.modules, {"sc_agent": wheel}), \
                    mock.patch.object(jj.decidr_client, "remote_preflight", return_value={"ok": True, "value": None}):
                settings = jj.quality_settings(False)
                source = [request_line(str(i)) for i in range(3)]
                if identifier == "config.missing_project":
                    stream = write(self.root, "queue.jsonl", "".join(json.dumps(line) + "\n" for line in source))
                    with mock.patch.object(jj, "open_run_log", return_value=jj.Ok(object())), \
                            mock.patch.object(jj, "log_result_line") as log_line:
                        code, output = run_cli(["batch", "--input", stream])
                    self.assertEqual(code, 2)
                    # run_cli parses the entire stdout as one JSON value: duplicate
                    # refusal envelopes or queued result lines would leave raw text.
                    self.assertIsInstance(output, dict)
                    self.assertEqual(output["error"]["code"], "DECIDR.CONFIG")
                    log_line.assert_not_called()
                else:
                    with mock.patch.object(jj, "log_result_line"):
                        result = jj._live_batch_results(source, settings, object(), False)
                    self.assertIsInstance(result, jj.Ok)
                self.assertEqual(attempted, [0] if identifier == "config.missing_project" else [0, 1, 2])
                wheel.send_batch.assert_called_once()
                wheel.logger.assert_not_called()

    def test_offline_commands_need_no_project(self):
        def questions(value):
            if isinstance(value, dict):
                candidate = value.get("questions")
                if isinstance(candidate, dict) and all("criteria" in q for q in candidate.values()):
                    return candidate
                parts = value.values()
            elif isinstance(value, list):
                parts = value
            else:
                return None
            return next((found for part in parts if (found := questions(part))), None)
        for command in self.commands:
            with self.subTest(command=command[0]), \
                    mock.patch.object(jj.decidr_client, "call_batch_results") as batch, \
                    mock.patch.object(jj.decidr_client, "call_result") as single:
                code, output = run_cli([*command, "--dry-run"])
                self.assertEqual(code, 0, output)
                answers = write(self.root, "answers.json", {"*": self.answers(questions(output))})
                code, output = run_cli([*command, "--answers-file", answers])
                self.assertEqual(code, 0, output)
                batch.assert_not_called()
                single.assert_not_called()


if __name__ == "__main__":
    unittest.main()
