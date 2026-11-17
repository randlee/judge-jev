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


def parsed_result(*, answers=None, position=0, error=None):
    """Controlled output at the public wheel parse_result boundary."""
    return dict(session_id="controlled", position=position, sends=1, digests={}, error=error,
                answers=answers or {}, usage={})


class ConsumerAdoptionTests(unittest.TestCase):
    def test_shared_default_codes_preserve_wheel_message_and_recovery(self):
        wheel = types.ModuleType("sc_agent")
        wheel.category = lambda encoded: json.loads(encoded)["category"]
        wheel.retryable = lambda encoded: True
        for category, expected in (("quota", "DECIDR.RATE_LIMITED"), ("busy", "DECIDR.OVERLOADED"),
                                   ("network", "DECIDR.NETWORK"), ("validation", "DECIDR.VALIDATION"),
                                   ("response_invalid", "DECIDR.RESPONSE_INVALID")):
            with self.subTest(category=category), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
                error = decidr_client.wheel_error({"id": "test", "category": category,
                                                   "message": "Rust message", "recovery": "Rust recovery"})
                self.assertEqual((error.code, error.message, error.action),
                                 (expected, "Rust message", "Rust recovery"))
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            error = decidr_client.wheel_error({"id": "decision.context_exceeded", "category": "validation",
                                               "message": "context too large"})
        self.assertEqual(error.code, "DECIDR.CONTEXT_EXCEEDED")

    def test_missing_sitr_returns_actionable_shared_error(self):
        with mock.patch.dict(sys.modules, {"sc_treesitter": None}):
            with self.assertRaises(decidr_client.ClientError) as caught:
                decidr_client.extract("python", "query", "source")
        self.assertEqual(caught.exception.code, "DEPENDENCY.SITR")
        self.assertIn(f"sitr=={jev_support.SITR_VERSION}", caught.exception.message)
        self.assertIn(f"sitr=={jev_support.SITR_VERSION}", caught.exception.action)

    def test_script_render_uses_the_sitr_pin_independently(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(jev_support, "SC_DECIDR_VERSION", "7.0.0"), \
                mock.patch.object(jev_support, "SITR_VERSION", "8.0.0"):
            rendered = jev_support._render(Path(tmp)) / "decidr_client.py"
            text = rendered.read_text(encoding="utf-8")
        self.assertIn('SC_DECIDR_VERSION = "7.0.0"', text)
        self.assertIn("Optional sitr 8.0.0", text)

    def test_judge_imports_rendered_client(self):
        self.assertIs(jev_judge.decidr_client, decidr_client)
        try:
            installed_version = metadata.version("sc-decidr")
        except metadata.PackageNotFoundError:
            # The wheel is an optional inline-script dependency and unit CI does not install it.
            installed_version = jev_support.SC_DECIDR_VERSION
        self.assertEqual(decidr_client.SC_DECIDR_VERSION, installed_version)
        self.assertTrue(callable(decidr_client.extract))
        self.assertIn(f"Optional sitr {jev_support.SITR_VERSION}", Path(decidr_client.__file__).read_text(encoding="utf-8"))

    def test_importing_rendered_client_does_not_import_sitr(self):
        path = Path(decidr_client.__file__)
        spec = importlib.util.spec_from_file_location("isolated_decidr_client", path)
        isolated = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {"sc_treesitter": None}):
            spec.loader.exec_module(isolated)
        self.assertTrue(callable(isolated.extract))

    def test_optional_sitr_is_lazy_and_extraction_reaches_a_dry_run(self):
        if importlib.util.find_spec("sc_treesitter") is None:
            self.skipTest("sitr wheel is not installed in this test environment")

        # Stub send to check extraction-to-request wiring without a provider call;
        # skip when the optional sitr wheel is absent.
        source = Path(__file__).parent / "fixtures" / "sitr_match.rs"
        captures = decidr_client.extract("rust", "(match_expression) @match", source.read_text(encoding="utf-8"))
        self.assertTrue(captures)
        prompt = "\n".join(capture.text for capture in captures)
        sent = []

        wheel = types.ModuleType("sc_agent")
        wheel.SagError = type("SagError", (Exception,), {})

        def dry_run(request, **kwargs):
            sent.append(json.loads(request))
            return '{"response": {"dry_run": true}}'

        wheel.send = dry_run
        wheel.parse_result = lambda _: parsed_result(answers={"q": decidr_client.NoulAnswer(0.5)})
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            request = json.dumps({"model": "jev", "state": prompt, "questions": {"q": {"type": "noul"}}})
            result = decidr_client.call_result(request, model="jev", project="judge-jev", agent_role="quality",
                                                abort_on=frozenset(), category_codes={},
                                                cancel=mock.Mock())
        self.assertTrue(result["ok"])
        self.assertEqual(sent[0]["state"], prompt)
        self.assertIn("match", prompt)

    def test_public_client_forwards_explicit_keyring_values_when_requested(self):
        wheel = types.ModuleType("sc_agent")
        wheel.SagError = type("SagError", (Exception,), {})
        line = json.dumps({"response": {"answers": {}}})
        wheel.send = mock.Mock(return_value=line)
        wheel.send_batch = mock.Mock(return_value=[json.dumps({"response": {"answers": {}}, "position": i}) for i in range(2)])
        wheel.category = mock.Mock()
        wheel.parse_result = lambda line: parsed_result(position=json.loads(line).get("position", 0))
        cancel = mock.Mock()
        options = dict(model="jev", project="judge-jev", agent_role="quality",
                       abort_on=frozenset(), category_codes={}, cancel=cancel,
                       keyring_service="plan-anchor", keyring_account="typesafe-api-key")
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            self.assertTrue(decidr_client.call_result("one", **options)["ok"])
            self.assertTrue(decidr_client.call_batch_results(["one", "two"], **options)["ok"])
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

    @unittest.skipUnless(find_spec("yaml"), "PyYAML is required to read the loopback repository consent setting")
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
            settings = root / ".sc/judge-jev/settings.yaml"
            settings.parent.mkdir(parents=True)
            settings.write_text("schema_version: 1\nallow_remote_judge: true\n")
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
                    decidr_client.remote_preflight(str(root), "controlled loopback requests")
                    options = dict(model="dec", project="test", agent_role="test", abort_on=frozenset(),
                                   category_codes={}, cancel=sc_agent.CancelToken(), config_dir=str(config))
                    dotenv = root / ".env"
                    dotenv.write_text("TYPESAFE_API_KEY=dotenv-test-key\n")
                    decidr_client.call_result(request, **options)
                    dotenv.unlink()
                    decidr_client.call_result(request, **options)
                    del os.environ["TYPESAFE_API_KEY"]
                    result = decidr_client.call_result(request, **options)
                    self.assertFalse(result["ok"])
                    self.assertIn("secrets.keyring_construction_refused", json.dumps(result["error"].data))
            finally:
                os.chdir(previous)
        self.assertEqual(seen, ["Bearer dotenv-test-key", "Bearer env-test-key"])

    def test_auth_error_line_maps_category_and_cancels(self):
        wheel = types.ModuleType("sc_agent")
        wheel.SagError = type("SagError", (Exception,), {})
        line = json.dumps({"error": {"id": "auth", "category": "auth", "message": "Rust auth failure", "recovery": "Fix key"}})
        wheel.send = mock.Mock(return_value=line)
        wheel.category = mock.Mock(return_value="auth")
        wheel.retryable = mock.Mock(return_value=False)
        typed_error = wheel.SagError("Rust auth failure")
        typed_error.detail = json.loads(line)["error"]
        typed_error.category = "auth"
        wheel.parse_result = lambda _: parsed_result(error=typed_error)
        cancel = mock.Mock()
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            result = decidr_client.call_result("one", model="jev", project="judge-jev",
                                       agent_role="quality", abort_on=frozenset({"auth"}),
                                       category_codes={"auth": "AUTH"}, cancel=cancel)
        self.assertEqual((result["error"].code, result["error"].message, result["error"].action), ("AUTH", "Rust auth failure", "Fix key"))
        cancel.cancel.assert_called_once_with()
        self.assertEqual(json.loads(wheel.category.call_args.args[0])["category"], "auth")

    def test_sag_error_category_cancels_and_propagates(self):
        wheel = types.ModuleType("sc_agent")
        wheel.SagError = type("SagError", (Exception,), {})
        error = wheel.SagError("denied")
        error.category = "auth"
        error.detail = {"id": "auth", "category": "auth", "message": "Rust denied", "recovery": "Fix key"}
        wheel.category = mock.Mock(return_value="auth")
        wheel.retryable = mock.Mock(return_value=False)
        wheel.send = mock.Mock(side_effect=error)
        cancel = mock.Mock()
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            result = decidr_client.call_result("one", model="jev", project="judge-jev",
                                               agent_role="quality", abort_on=frozenset({"auth"}),
                                               category_codes={}, cancel=cancel)
        self.assertIsInstance(result["error"], decidr_client.ClientError)
        self.assertEqual((result["error"].message, result["error"].action), ("Rust denied", "Fix key"))
        cancel.cancel.assert_called_once_with()

    def test_keyboard_interrupt_cancels_and_propagates(self):
        wheel = types.ModuleType("sc_agent")
        wheel.SagError = type("SagError", (Exception,), {})
        wheel.send = mock.Mock(side_effect=KeyboardInterrupt)
        cancel = mock.Mock()
        with consented(), mock.patch.dict(sys.modules, {"sc_agent": wheel}):
            with self.assertRaises(KeyboardInterrupt):
                decidr_client.call_result("one", model="jev", project="judge-jev",
                                   agent_role="quality", abort_on=frozenset(),
                                   category_codes={}, cancel=cancel)
        cancel.cancel.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
