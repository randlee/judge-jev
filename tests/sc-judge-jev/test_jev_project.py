"""Project selection for live commands; temporary configuration and a controlled client only."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
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
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "--quiet", str(self.repo)], check=True, capture_output=True)
        self.global_dir = self.root / "global"
        self.local_dir = self.repo / ".sc/sc-agent"
        self.home = self.root / "home"
        self.home.mkdir()
        environment = {"HOME": str(self.home), "USERPROFILE": str(self.home),
                       "SC_AGENT_HOME": str(self.global_dir), "JUDGE_JEV_LOG_ROOT": str(self.root / "logs"),
                       "PATH": os.environ.get("PATH", "")}
        patcher = mock.patch.dict(os.environ, environment, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        previous = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, previous)
        index = write(self.repo, "index.json", INDEX)
        stream = write(self.repo, "requests.jsonl", json.dumps(request_line()) + "\n")
        definitions = write(self.repo, "terms.ttl", ttl(definition("fast", "fast", "Under 5 s.", "docs/r.md", (ADR, None))))
        self.commands = [
            ["quality", "--index", index, "--adr", "ADR-T-0001"],
            ["batch", "--input", stream],
            ["drift", "--old-index", index, "--new-index", index, "--adr", "ADR-T-0001",
             "--controls", "0", "--question-set", "brief"],
            ["compare-definition", "--index", index, "--adr", "ADR-T-0001",
             "--definitions", definitions, "--definition", iri("fast")],
        ]

    def config(self, folder, name, project):
        folder.mkdir(parents=True, exist_ok=True)
        return write(folder, name, {"project": project})

    @staticmethod
    def answers(questions):
        return {qid: {"type": "choice", "choice": next(iter(q["criteria"])), "confidence": 1.,
                      "probabilities": {choice: float(i == 0) for i, choice in enumerate(q["criteria"])}}
                for qid, q in questions.items()}

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

    def test_flag_environment_and_file_projects_reach_the_client_for_all_commands(self):
        self.config(self.global_dir, "sc-agent.json", "global")
        self.config(self.local_dir, "decidr.local.json", "local")
        for source, extra, expected in (("flag", ["--project", "chosen"], "chosen"),
                                        ("environment", [], "environment"), ("file", [], "local")):
            if source == "file":
                os.environ.pop("SC_PROJECT", None)
            else:
                os.environ["SC_PROJECT"] = "environment"
            for command in self.commands:
                self.projects = []
                with self.subTest(source=source, command=command[0]), \
                        mock.patch.object(jj.decidr_client, "remote_preflight", return_value={"ok": True, "value": None}), \
                        mock.patch.object(jj.decidr_client, "call_batch_results", side_effect=self.transport) as batch, \
                        mock.patch.object(jj.decidr_client, "call_result") as single:
                    code, output = run_cli([*command, *extra])
                    self.assertEqual(code, 0, output)
                    self.assertTrue(batch.called)
                    single.assert_not_called()
                    self.assertTrue(self.projects)
                    self.assertEqual(set(self.projects), {expected})

    def test_missing_project_exits_two_before_any_client_or_log_call(self):
        for command in self.commands:
            with self.subTest(command=command[0]), \
                    mock.patch.object(jj.decidr_client, "call_batch_results") as batch, \
                    mock.patch.object(jj.decidr_client, "call_result") as single, \
                    mock.patch.object(jj, "open_run_log") as log:
                code, output = run_cli(command)
                self.assertEqual(code, 2, output)
                self.assertEqual(output["error"]["code"], "DECIDR.CONFIG")
                for field in ("message", "suggested_action"):
                    self.assertIn("--project", output["error"][field])
                    self.assertIn("SC_PROJECT", output["error"][field])
                batch.assert_not_called()
                single.assert_not_called()
                log.assert_not_called()

    def test_all_file_layers_and_nested_worktree_resolution(self):
        for folder in (self.global_dir, self.local_dir):
            for name in ("sc-agent.json", "decidr.json", "decidr.local.json"):
                project = folder.name + ":" + name
                self.config(folder, name, project)
                code, output = run_cli(["check-project"])
                self.assertEqual((code, output["data"]["project"]), (0, project))
        nested = self.repo / "nested"
        nested.mkdir()
        os.chdir(nested)
        self.assertEqual(run_cli(["check-project"])[1]["data"]["project"], project)

    def test_default_global_folder_is_under_the_isolated_home(self):
        os.environ.pop("SC_AGENT_HOME")
        self.config(self.home / ".sc-agent", "decidr.json", "home-project")
        self.assertEqual(run_cli(["check-project"])[1]["data"]["project"], "home-project")

    def test_empty_and_invalid_projects_do_not_fall_back(self):
        self.config(self.global_dir, "sc-agent.json", "global")
        for project in (None, "", " ", 7):
            with self.subTest(project=project):
                self.config(self.local_dir, "decidr.local.json", project)
                self.assertEqual(run_cli(["check-project"])[0], 2)
        os.environ["SC_PROJECT"] = ""
        self.assertEqual(run_cli(["check-project"])[0], 2)
        os.environ["SC_PROJECT"] = "environment"
        self.assertEqual(run_cli(["check-project", "--project", ""])[0], 2)

    def test_malformed_config_is_a_typed_error(self):
        self.local_dir.mkdir(parents=True)
        write(self.local_dir, "decidr.local.json", "{invalid")
        code, output = run_cli(["check-project"])
        self.assertEqual(code, 2)
        self.assertEqual(output["error"]["code"], "DECIDR.CONFIG")
        self.assertIn("decidr.local.json", output["error"]["message"])

    def test_offline_commands_need_no_project_and_ignore_project_config(self):
        self.local_dir.mkdir(parents=True)
        write(self.local_dir, "decidr.json", "{invalid")
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
                answers = write(self.repo, "answers.json", {"*": self.answers(questions(output))})
                code, output = run_cli([*command, "--answers-file", answers])
                self.assertEqual(code, 0, output)
                batch.assert_not_called()
                single.assert_not_called()


if __name__ == "__main__":
    unittest.main()
