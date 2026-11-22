"""Exercise the installed consumer through a controlled public wheel surface."""
import json
from importlib import metadata
from importlib.util import find_spec
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
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
from test_jev_judge import consented


class ConsumerAdoptionTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(decidr_client, "_logger_handle", None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_shared_default_codes_preserve_wheel_message_and_recovery(self):
        wheel = types.ModuleType("sc_agent")
        wheel.logger = mock.Mock(return_value={"ok": True, "value": object()})
        wheel.category = lambda encoded: json.loads(encoded)["category"]
        wheel.retryable = lambda encoded: True
        for category, expected in (("quota", "DECIDR.RATE_LIMITED"), ("busy", "DECIDR.OVERLOADED"),
                                   ("network", "DECIDR.NETWORK"), ("validation", "DECIDR.VALIDATION"),
                                   ("response_invalid", "DECIDR.RESPONSE_INVALID")):
            with self.subTest(category=category), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
                error = decidr_client.wheel_error({"id": "test", "category": category,
                                                   "message": "Rust message", "action": "Rust recovery"})
                self.assertEqual((error.code, error.message, error.action),
                                 (expected, "Rust message", "Rust recovery"))
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            error = decidr_client.wheel_error({"id": "decision.context_exceeded", "category": "validation",
                                               "message": "context too large"})
        self.assertEqual(error.code, "DECIDR.CONTEXT_EXCEEDED")

    def test_missing_wheel_returns_actionable_shared_error(self):
        with mock.patch.dict(sys.modules, {"sc_agent": None}):
            result = decidr_client.extract("python", "source", "query")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["id"], "DEPENDENCY.SC_DECIDR")
        self.assertIn("Install sc-decidr", result["error"]["action"])

    def test_script_render_uses_the_sitr_pin_independently(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(jev_support, "SC_DECIDR_VERSION", "7.0.0"), \
                mock.patch.object(jev_support, "SITR_VERSION", "8.0.0"):
            rendered = jev_support._render(Path(tmp)) / "decidr_client.py"
            text = rendered.read_text(encoding="utf-8")
        self.assertIn(f'SC_DECIDR_VERSION = "{metadata.version("sc-decidr")}' , text)
        self.assertIn("return sc_agent.sitr.query(", text)

    def test_judge_imports_rendered_client(self):
        self.assertIs(jev_judge.decidr_client, decidr_client)
        try:
            installed_version = metadata.version("sc-decidr")
        except metadata.PackageNotFoundError:
            # The wheel is an optional inline-script dependency and unit CI does not install it.
            installed_version = jev_support.SC_DECIDR_VERSION
        self.assertEqual(decidr_client.SC_DECIDR_VERSION, installed_version)
        self.assertTrue(callable(decidr_client.extract))
        self.assertNotIn("import sc_treesitter", Path(decidr_client.__file__).read_text(encoding="utf-8"))

    def test_importing_rendered_client_does_not_import_sitr(self):
        path = Path(decidr_client.__file__)
        spec = importlib.util.spec_from_file_location("isolated_decidr_client", path)
        isolated = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {"sc_treesitter": None}):
            spec.loader.exec_module(isolated)
        self.assertTrue(callable(isolated.extract))

    def test_optional_sitr_is_lazy_and_extraction_reaches_a_dry_run(self):
        if importlib.util.find_spec("sc_agent.sitr") is None:
            if os.environ.get("JUDGE_JEV_REQUIRE_SITR") == "1":
                self.fail("JUDGE_JEV_REQUIRE_SITR=1 but the sc-decidr wheel is not installed")
            self.skipTest("sc-decidr wheel is not installed in this test environment")

        # Stub send to check extraction-to-request wiring without a provider call;
        # skip when the optional sc-decidr wheel is absent.
        source = Path(__file__).parent / "fixtures" / "sitr_match.rs"
        with tempfile.TemporaryDirectory() as root, mock.patch.dict(os.environ, {"JUDGE_JEV_LOG_ROOT": root}):
            captures = decidr_client.extract("rust", source.read_text(encoding="utf-8"), "(match_expression) @match")["value"]
        self.assertTrue(captures)
        prompt = "\n".join(capture["text"] for capture in captures)
        sent = []

        wheel = types.ModuleType("sc_agent")
        wheel.logger = mock.Mock(return_value={"ok": True, "value": object()})

        def dry_run(request, **kwargs):
            sent.append(json.loads(request))
            return {"ok": True, "value": {"answers": {"q": {"type": "noul", "noul": 0.5}}}}

        wheel.send = dry_run
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            request = json.dumps({"model": "jev", "state": prompt, "questions": {"q": {"type": "noul"}}})
            result = decidr_client.call_result(request, model="jev", project="judge-jev",                                                 abort_on=frozenset(), category_codes={},
                                                cancel=mock.Mock())
        self.assertTrue(result["ok"])
        self.assertEqual(sent[0]["state"], prompt)
        self.assertIn("match", prompt)

    def test_public_client_omits_removed_keyring_overrides(self):
        wheel = types.ModuleType("sc_agent")
        wheel.logger = mock.Mock(return_value={"ok": True, "value": object()})
        line = {"ok": True, "value": {"answers": {}}}
        wheel.send = mock.Mock(return_value=line)
        wheel.send_batch = mock.Mock(return_value={"ok": True, "value": [{"index": i, "result": line} for i in range(2)]})
        wheel.category = mock.Mock()
        cancel = mock.Mock()
        options = dict(model="jev", project="judge-jev",                        abort_on=frozenset(), category_codes={}, cancel=cancel,
                       general_log=None)
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            self.assertTrue(decidr_client.call_result("one", **options)["ok"])
            self.assertTrue(decidr_client.call_batch_results(["one", "two"], **options)["ok"])
        for operation in (wheel.send, wheel.send_batch):
            args = operation.call_args.kwargs
            self.assertNotIn("keyring_service", args)
            self.assertNotIn("keyring_account", args)
            self.assertEqual(args["project"], "judge-jev")
            self.assertEqual(args["agent_role"], "judge-jev")
            self.assertIs(args["cancel"], cancel)
            self.assertNotIn("provider", args)
            self.assertIs(args["general_log"], wheel.logger.return_value["value"])
        wheel.category.assert_not_called()

    def test_real_wheel_prefers_environment_then_dotenv_with_keyring_trapped(self):
        try:
            importlib.metadata.distribution("sc-decidr")
        except importlib.metadata.PackageNotFoundError:
            self.skipTest("sc-decidr wheel is not installed")

        # Other tests install a module double in sys.modules. Load the installed
        # wheel itself and make it visible only for these client calls.
        previous_agent = sys.modules.pop("sc_agent", None)
        try:
            wheel = importlib.import_module("sc_agent")
        finally:
            if previous_agent is not None:
                sys.modules["sc_agent"] = previous_agent

        seen = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
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

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        server.timeout = 5  # Hang guard, never an elapsed-time assertion.
        def serve():
            for _ in range(2):
                server.handle_request()
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                run_child(["git", "init", "-q", str(root)], check=True)
                config = root / "config"
                config.mkdir()
                environment = {"PATH": os.defpath, "TYPESAFE_API_KEY": "env-test-key",
                               "DECIDR_LOG_ROOT": str(root / "logs"), "JUDGE_JEV_LOG_ROOT": str(root / "logs")}
                request = {"model": "jev-latest", "state": "s", "questions": {"q": {"type": "noul"}}}
                options = dict(model="jev", project="test", abort_on=frozenset(),
                               category_codes={}, cancel=wheel.Cancel(), config_dir=str(config))
                client = decidr_client
                native_send = wheel.send
                def trapped_keyring(name):
                    raise RuntimeError("test keyring refused")
                def send(request, **kwargs):
                    kwargs["timeout_secs"] = 5
                    return native_send(request, base_url=f"http://127.0.0.1:{server.server_port}/v1",
                                       keyring_lookup=trapped_keyring, sleep=lambda _: None, **kwargs)
                with mock.patch.object(wheel, "send", side_effect=send), mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(client, "remote_preflight", return_value={"ok": True, "value": None}), \
                        mock.patch.dict(sys.modules, {"sc_agent": wheel}):
                    previous_cwd = os.getcwd()
                    os.chdir(root)
                    try:
                        dotenv = root / ".env"
                        dotenv.write_text("TYPESAFE_API_KEY=dotenv-test-key\n")
                        first = client.call_result(request, **options)
                        self.assertTrue(first["ok"], first)
                        del os.environ["TYPESAFE_API_KEY"]
                        second = client.call_result(request, **options)
                        self.assertTrue(second["ok"], second)
                        dotenv.unlink()
                        third = client.call_result(request, **options)
                        self.assertFalse(third["ok"], third)
                        self.assertIn("secrets.keyring_read", json.dumps(third["error"].data))
                    finally:
                        os.chdir(previous_cwd)
            self.assertEqual(seen, ["Bearer env-test-key", "Bearer dotenv-test-key"])
        finally:
            thread.join(12)
            server.server_close()
            self.assertFalse(thread.is_alive(), "scripted runner did not finish")

    def test_auth_error_value_maps_category_and_cancels(self):
        wheel = types.ModuleType("sc_agent")
        wheel.logger = mock.Mock(return_value={"ok": True, "value": object()})
        detail = {"id": "http.auth", "category": "auth", "message": "Rust auth failure", "action": "Fix key"}
        wheel.send = mock.Mock(return_value={"ok": False, "error": detail})
        cancel = mock.Mock()
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            result = decidr_client.call_result("one", model="jev", project="test", abort_on=frozenset({"auth"}),
                                               category_codes={"auth": "AUTH"}, cancel=cancel)
        self.assertEqual((result["error"].code, result["error"].message, result["error"].action), ("AUTH", "Rust auth failure", "Fix key"))
        self.assertEqual(result["error"].data, detail)
        cancel.cancel.assert_called_once_with()

    def test_returned_error_category_cancels_and_propagates(self):
        wheel = types.ModuleType("sc_agent")
        wheel.logger = mock.Mock(return_value={"ok": True, "value": object()})
        detail = {"id": "http.auth", "category": "auth", "message": "Rust denied", "action": "Fix key"}
        wheel.send = mock.Mock(return_value={"ok": False, "error": detail})
        cancel = mock.Mock()
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            result = decidr_client.call_result("one", model="jev", project="test", abort_on=frozenset({"auth"}),
                                               category_codes={}, cancel=cancel)
        self.assertIsInstance(result["error"], decidr_client.ClientError)
        self.assertEqual((result["error"].message, result["error"].action), ("Rust denied", "Fix key"))
        cancel.cancel.assert_called_once_with()

    def test_keyboard_interrupt_returns_cancellation(self):
        wheel = types.ModuleType("sc_agent")
        wheel.logger = mock.Mock(return_value={"ok": True, "value": object()})
        wheel.send = mock.Mock(side_effect=KeyboardInterrupt)
        cancel = mock.Mock()
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            result = decidr_client.call_result("one", model="jev", project="test", abort_on=frozenset(),
                                               category_codes={}, cancel=cancel)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"].code, "CANCELED")
        cancel.cancel.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
