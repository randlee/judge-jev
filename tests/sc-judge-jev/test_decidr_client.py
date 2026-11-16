"""Exercise the installed consumer through a controlled public wheel surface."""
import json
from importlib import metadata
from importlib.util import find_spec
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock

import jev_support  # noqa: F401  (render and install the scripts on sys.path)
from child_support import run_child
import decidr_client
import jev_judge


class ConsumerAdoptionTests(unittest.TestCase):
    def test_judge_imports_rendered_client(self):
        self.assertIs(jev_judge.decidr_client, decidr_client)
        try:
            installed_version = metadata.version("sc-decidr")
        except metadata.PackageNotFoundError:
            # The wheel is an optional inline-script dependency and unit CI does not install it.
            installed_version = jev_support.SC_DECIDR_VERSION
        self.assertEqual(decidr_client.SC_DECIDR_VERSION, installed_version)
        self.assertFalse(hasattr(decidr_client, "extract"))

    def test_public_client_forwards_explicit_keyring_values_when_requested(self):
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
            self.assertIsNone(args["general_log"])
        wheel.category.assert_not_called()

    @unittest.skipUnless(find_spec("sc_agent"), "sc-decidr wheel is not installed")
    def test_real_wheel_prefers_dotenv_then_environment_with_keyring_trapped(self):
        import sc_agent

        seen = []

        class LocalRunner(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, body):
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self.reply({"ok": True, "model": "jev-latest"})

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                seen.append(self.headers.get("Authorization"))
                self.reply({"model": "jev-latest", "answers": {"q": {"type": "noul", "noul": 0.5}},
                            "usage": {"input_tokens": 1, "output_tokens": 1}})

        server = ThreadingHTTPServer(("127.0.0.1", 0), LocalRunner)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 120)  # hang guard only
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        request = json.dumps({"model": "jev-latest", "state": "s", "questions": {"q": {"type": "noul"}}})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_child(["git", "init", "-q", str(root)], check=True)
            config = root / "config"
            config.mkdir()
            (config / "default.json").write_text(json.dumps({
                "log_root": str(root / "logs"),
                "local_runners": {"dec": {"kind": "mapika", "host": "127.0.0.1", "port": server.server_port,
                                          "model": "jev-latest", "key_env": "TYPESAFE_API_KEY"}},
            }))
            environment = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY") and not k.startswith("SC_AGENT__")}
            environment.update(TYPESAFE_API_KEY="env-test-key", SC_AGENT_TEST_TRAP_PLATFORM_KEYRING="1")
            previous = os.getcwd()
            try:
                os.chdir(root)
                with mock.patch.dict(os.environ, environment, clear=True):
                    options = dict(model="dec", project="test", agent_role="test", abort_on=frozenset(),
                                   category_codes={}, cancel=sc_agent.CancelToken(), config_dir=str(config))
                    dotenv = root / ".env"
                    dotenv.write_text("TYPESAFE_API_KEY=dotenv-test-key\n")
                    decidr_client.call(request, **options)
                    dotenv.unlink()
                    decidr_client.call(request, **options)
                    del os.environ["TYPESAFE_API_KEY"]
                    with self.assertRaises(sc_agent.SagError) as caught:
                        decidr_client.call(request, **options)
                    self.assertIn("secrets.keyring_construction_refused", caught.exception.detail)
            finally:
                os.chdir(previous)
        self.assertEqual(seen, ["Bearer dotenv-test-key", "Bearer env-test-key"])

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
