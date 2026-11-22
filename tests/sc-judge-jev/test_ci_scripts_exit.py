"""0.8.3: the repository CI scripts exit 2 with a message, never 1 and never a traceback.

check_version_sync.py runs as a real process: on a scratch copy of the repository for version drift and a
malformed manifest. gen_install_data.py and install_sc_compose_ci.py are driven
in-process with the failing call stubbed (a failing git command, a corrupt
legacy-owned.json, an unexpected exception), since provoking those for real needs a
broken clone or a network.
"""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
from child_support import run_child
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(f"ci_{name}", SCRIPTS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repo_copy(dest: Path) -> Path:
    """The repository's files (no .git, no caches) under ``dest``, for checks that must not touch the real tree."""
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".venv", "node_modules"))
    return dest


class CheckVersionSync(unittest.TestCase):
    def run_check(self, root: Path, *argv):
        proc = run_child([sys.executable, str(root / "scripts" / "check_version_sync.py"), *argv], cwd=str(root),
                              text=True, encoding="utf-8")
        self.assertNotIn("Traceback", proc.stderr)
        return proc

    def test_version_drift_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            root = repo_copy(Path(td) / "repo")
            self.assertEqual(self.run_check(root).returncode, 0)  # the copy is in sync before the edit
            (root / "VERSION").write_text("99.0.0\n", encoding="utf-8")
            proc = self.run_check(root)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("99.0.0", proc.stdout + proc.stderr)

    def test_a_malformed_manifest_exits_2_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            root = repo_copy(Path(td) / "repo")
            for rel, text in (("plugins/sc-judge-jev/plugin.json", "{"), (".claude-plugin/marketplace.json", "[1]")):
                with self.subTest(rel):
                    original = (root / rel).read_text(encoding="utf-8")
                    (root / rel).write_text(text, encoding="utf-8")
                    try:
                        proc = self.run_check(root)
                    finally:
                        (root / rel).write_text(original, encoding="utf-8")
                    self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                    self.assertIn(rel, proc.stderr)


class GenInstallData(unittest.TestCase):
    def setUp(self):
        self.gen = load("gen_install_data")

    def main(self, *argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = self.gen.main(list(argv))
        return code, err.getvalue()

    def test_a_failing_git_command_exits_2(self):
        real = subprocess.run

        def fake_run(cmd, *args, **kwargs):
            if kwargs.get("check"):  # _git's calls; _has_commit's (check=False) still answer
                raise subprocess.CalledProcessError(128, cmd, output=b"", stderr=b"fatal: bad object")
            return real(cmd, *args, **kwargs)

        with mock.patch.object(self.gen.subprocess, "run", fake_run):
            code, err = self.main("--check")
        self.assertEqual(code, 2)
        self.assertIn("exited 128: fatal: bad object", err)

    def test_git_children_have_closed_stdin_and_bounded_timeouts(self):
        completed = subprocess.CompletedProcess(["git"], 0, stdout=b"value")
        with mock.patch.object(self.gen.subprocess, "run", return_value=completed) as run:
            self.assertEqual(self.gen._git("show"), b"value")
            self.assertIs(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(run.call_args.kwargs["timeout"], self.gen.GIT_TIMEOUT_SECONDS)
            self.gen._git("cat-file", stdin=b"payload")
            self.assertEqual(run.call_args.kwargs["input"], b"payload")
            self.assertNotIn("stdin", run.call_args.kwargs)
        with mock.patch.object(self.gen.subprocess, "run", return_value=subprocess.CompletedProcess(["git"], 0, stdout="revision\n")) as run:
            self.assertEqual(self.gen._has_commit("HEAD"), "revision")
            self.assertIs(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(run.call_args.kwargs["timeout"], self.gen.GIT_TIMEOUT_SECONDS)

    def test_git_timeouts_fail_with_typed_message(self):
        for method in (lambda: self.gen._git("show"), lambda: self.gen._has_commit("HEAD")):
            with self.subTest(method=method), mock.patch.object(self.gen.subprocess, "run", side_effect=subprocess.TimeoutExpired(["git"], 60)):
                with self.assertRaisesRegex(self.gen.Failure, "timed out after 60s"):
                    method()

    def test_a_corrupt_legacy_owned_json_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            corrupt = Path(td) / "legacy-owned.json"
            for text, says in (("{", "is not valid JSON"), ("[]", "is not a legacy-ownership record")):
                with self.subTest(text=text):
                    corrupt.write_text(text, encoding="utf-8")
                    with mock.patch.object(self.gen, "LEGACY", corrupt), \
                            mock.patch.object(self.gen, "history_commits", return_value=([], [])), \
                            mock.patch.object(self.gen, "legacy", return_value={"skill": {}, "agents": {}}):
                        code, err = self.main("--check")
                    self.assertEqual(code, 2)
                    self.assertIn(says, err)


class InstallMatchedWheels(unittest.TestCase):
    def setUp(self):
        self.ci = load("install_sc_decidr_ci")
        self.source = '#   "sc-decidr==7.1.2",\n'
        self.env = mock.patch.dict(os.environ, {"RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_published_wheel_uses_runtime_pin(self):
        with mock.patch.object(Path, "read_text", return_value=self.source), \
                mock.patch.object(self.ci, "urlopen"), mock.patch.object(self.ci, "run_child") as run:
            self.ci.main()
        self.assertEqual(run.call_args.args[0][-3:], ["--index-url", "https://pypi.org/simple", "sc-decidr==7.1.2"])

    def test_prerelease_checksum_is_checked_before_install(self):
        import hashlib
        from urllib.error import HTTPError
        payload = b"verified wheel"
        asset = "sc_decidr-7.1.2-cp311-abi3-manylinux_2_28_x86_64.whl"
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            return self.source if path.name == "jev_judge.py.j2" else original_read(path, *args, **kwargs)
        def child(argv):
            if argv[0] == "gh":
                root = Path(argv[-1])
                (root / asset).write_bytes(payload)
                (root / "checksums.txt").write_text(f"{hashlib.sha256(payload).hexdigest()}  {asset}\n")
        with mock.patch.object(Path, "read_text", read), \
                mock.patch.object(self.ci, "urlopen", side_effect=HTTPError("url", 404, "missing", {}, None)), \
                mock.patch.object(self.ci, "run_child", side_effect=child) as run:
            self.ci.main()
        self.assertEqual(run.call_args_list[0].args[0][3], "prerelease/v7.1.2")
        self.assertIn("--no-index", run.call_args_list[1].args[0])

    def test_bad_checksum_is_refused(self):
        from urllib.error import HTTPError
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            return self.source if path.name == "jev_judge.py.j2" else original_read(path, *args, **kwargs)
        def child(argv):
            root = Path(argv[-1])
            (root / "checksums.txt").write_text("0" * 64 + "  sc_decidr-7.1.2-cp311-abi3-manylinux_2_28_x86_64.whl\n")
            (root / "sc_decidr-7.1.2-cp311-abi3-manylinux_2_28_x86_64.whl").write_bytes(b"different")
        with mock.patch.object(Path, "read_text", read), \
                mock.patch.object(self.ci, "urlopen", side_effect=HTTPError("url", 404, "missing", {}, None)), \
                mock.patch.object(self.ci, "run_child", side_effect=child) as run:
            with self.assertRaisesRegex(SystemExit, "Checksum verification failed"):
                self.ci.main()
        self.assertEqual(run.call_count, 1)

    def test_unsupported_runner_and_timeout_fail(self):
        with mock.patch.dict(os.environ, {"RUNNER_OS": "Plan9", "RUNNER_ARCH": "RISC-V"}), \
                mock.patch.object(Path, "read_text", return_value=self.source):
            with self.assertRaisesRegex(SystemExit, "No sc-decidr wheel for"):
                self.ci.main()
        with mock.patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired(["child"], 300)), \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit) as caught:
                self.ci.run_child(["child"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("timed out after 300s", stderr.getvalue())


class InstallScComposeCi(unittest.TestCase):
    def test_download_and_version_probe_timeouts_are_bounded(self):
        import hashlib
        ci = load("install_sc_compose_ci")
        payload = b"controlled archive"
        for platform in ("darwin", "win32"):
            for fail_version in (False, True):
                with self.subTest(platform=platform, fail_version=fail_version), tempfile.TemporaryDirectory() as td:
                    def child(argv, **kwargs):
                        if argv[0] == "gh":
                            if not fail_version:
                                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
                            Path(argv[-1], "archive.tar.gz").write_bytes(payload)
                            return subprocess.CompletedProcess(argv, 0)
                        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

                    def extract(_archive, destination):
                        (destination / ci.executable_name()).write_bytes(b"binary")

                    assets = {(platform, ci.normalized_machine()): ("archive.tar.gz", hashlib.sha256(payload).hexdigest())}
                    stderr = io.StringIO()
                    fake_sys = mock.Mock(wraps=sys, platform=platform, stderr=stderr)
                    with mock.patch.object(ci, "sys", fake_sys), mock.patch.dict(ci.ASSETS, assets, clear=True), \
                            mock.patch.dict(os.environ, {"RUNNER_TEMP": td}), \
                            mock.patch.object(ci, "extract", side_effect=extract), \
                            mock.patch.object(subprocess, "run", side_effect=child) as run:
                        self.assertEqual(ci.run(), 2)
                    self.assertIn("install_sc_compose_ci: subprocess timed out", stderr.getvalue())
                    self.assertEqual(len(run.call_args_list), 2 if fail_version else 1)
                    for call in run.call_args_list:
                        self.assertIs(call.kwargs["stdin"], subprocess.DEVNULL)
                        self.assertEqual(call.kwargs["timeout"], 300 if call.args[0][0] == "gh" else 30)

    def test_any_failure_exits_2_with_a_message(self):
        ci = load("install_sc_compose_ci")
        for exc in (RuntimeError("unsupported CI platform"), ValueError("bad digest field"), KeyError("assets")):
            with self.subTest(type(exc).__name__):
                def boom(exc=exc):
                    raise exc
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    code = ci.run(boom)
                self.assertEqual(code, 2)
                self.assertTrue(err.getvalue().startswith("install_sc_compose_ci: "), err.getvalue())


if __name__ == "__main__":
    unittest.main()
