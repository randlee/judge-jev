"""A Jev call that got no answer is a tool failure, never a negative result; an interrupt is CANCELED and exit 130.

Ported from plan-anchor's tests/sc-plan-anchor/test_jev_failures.py. Every case runs a real process.
Live failures use a refused connection (``urlopen`` patched to raise it; ``JEV_URL`` still points at the
closed local port 127.0.0.1:9) with a dummy key in the child only, and consent recorded in a scratch
repository. Jev is never called.
"""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

from jev_support import SCRIPTS, log_lines
from test_jev_judge import jsonl, request_line

JJ = SCRIPTS / "jev_judge.py"
ERROR_KEYS = {"code", "message", "recoverable", "suggested_action"}
DUMMY_KEY = "sk-test-closed-port-0000"  # never a real key: nothing is ever sent with it
# jev_judge.main with every Jev call refused and no back-off sleep; the retries themselves still run. urlopen
# raises the refusal itself, so the result never depends on what listens on port 9 or how a firewall answers;
# JEV_URL still names a closed local port, so even an unpatched call could not leave the host.
# argv[1] is the scripts directory, the rest is the command line.
REFUSED_RUNNER = (
    "import errno, sys, urllib.error, urllib.request\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import jev_judge\n"
    "def refused(*args, **kwargs):\n"
    "    raise urllib.error.URLError(ConnectionRefusedError(errno.ECONNREFUSED, 'Connection refused'))\n"
    "urllib.request.urlopen = refused\n"
    "jev_judge.JEV_URL = 'http://127.0.0.1:9/v1/systemone'\n"
    "jev_judge._sleep = lambda seconds: None\n"
    "raise SystemExit(jev_judge.main(sys.argv[2:]))\n"
)
# Runs a CLI as __main__ and interrupts it exactly where it reads one input file: the first Path.read_text of
# argv[2] sends SIGINT to the process itself. kill() to the calling single-threaded process delivers the
# signal before it returns, so Python's SIGINT handler raises KeyboardInterrupt at the next bytecode, inside
# that read. If the signal is ignored or lost, the runner exits 3 instead, and the test fails on the exit code.
# argv[1] is the CLI script, argv[2] the input file, the rest is the CLI's command line.
INTERRUPT_RUNNER = (
    "import os, pathlib, runpy, signal, sys\n"
    "script, target = sys.argv[1], os.path.realpath(sys.argv[2])\n"
    "real_read_text = pathlib.Path.read_text\n"
    "def read_text(self, *args, **kwargs):\n"
    "    if os.path.realpath(self) == target:\n"
    "        os.kill(os.getpid(), signal.SIGINT)\n"
    "        sys.stderr.write('SIGINT was not delivered\\n')\n"
    "        os._exit(3)\n"
    "    return real_read_text(self, *args, **kwargs)\n"
    "pathlib.Path.read_text = read_text\n"
    "sys.argv = [script, *sys.argv[3:]]\n"
    "sys.path.insert(0, os.path.dirname(script))\n"
    "runpy.run_path(script, run_name='__main__')\n"
)
try:
    import yaml  # noqa: F401 - consent lives in settings.yaml, which the settings module reads with PyYAML
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


def child_env(**extra):
    environment = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
    environment.update(extra)
    return environment


@unittest.skipUnless(HAVE_YAML, "live-path cases read allow_remote_judge from settings.yaml (PyYAML)")
class LiveBatchWithoutAnswers(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.d)], check=True)
        proc = subprocess.run([sys.executable, str(SCRIPTS / "judge_jev_settings.py"), "set", "allow_remote_judge", "true"],
                              cwd=str(self.d), env=child_env(), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_refused_connection_is_exit_2_with_every_line_and_the_envelope_on_stderr(self):
        (self.d / "in.jsonl").write_text(jsonl([request_line("s1"), request_line("s2")]), encoding="utf-8")
        proc = subprocess.run([sys.executable, "-c", REFUSED_RUNNER, str(SCRIPTS), "batch", "--input", "in.jsonl",
                               "--run-dir", "runs", "--run-name", "r1"],
                              cwd=str(self.d), env=child_env(TYPESAFE_API_KEY=DUMMY_KEY), capture_output=True, text=True,
                              encoding="utf-8", timeout=300)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        lines = [json.loads(x) for x in proc.stdout.splitlines()]
        self.assertEqual([x["item_id"] for x in lines], ["s1", "s2"])
        for line in lines:
            self.assertEqual((line["ok"], line["verdict"], line["retry_count"], line["error"]["code"]), (False, None, 1, "JEV.NETWORK"))
            self.assertTrue(line["error"]["message"].startswith("Could not reach Jev: "), line["error"])
            self.assertIn("Connection refused", line["error"]["message"])
        envelope = json.loads(proc.stderr)
        self.assertEqual((envelope["success"], set(envelope["error"]), envelope["error"]["code"]), (False, ERROR_KEYS, "JEV.NETWORK"))
        self.assertTrue(envelope["error"]["message"].startswith("2 request(s) got no answer; first batch/s1/ANC-001/cur/r1"))
        self.assertEqual(log_lines(self.d / "runs"), lines)
        self.assertNotIn(DUMMY_KEY, proc.stdout + proc.stderr)


def _default_sigint():
    """In the child before exec: a parent that ignores SIGINT (a background ``&`` job) would pass the ignore on,
    and Python then installs no KeyboardInterrupt handler."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)


@unittest.skipUnless(os.name == "posix", "the runner signals itself with os.kill and the child resets SIGINT (POSIX)")
class Interrupts(unittest.TestCase):
    """SIGINT while a command reads its input: the CANCELED envelope on stdout and exit 130, from each CLI.

    Each CLI runs under INTERRUPT_RUNNER, which raises SIGINT inside the read of ``input_rel``; nothing is timed.
    """

    def interrupt(self, argv, input_rel, env=None, git=False):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td).resolve()
            if git:
                subprocess.run(["git", "init", "-q", str(d)], check=True)
            target = d / input_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{}\n", encoding="utf-8")
            script, *rest = argv
            rest = [str(a).replace("{INPUT}", str(target)) for a in rest]
            proc = subprocess.run([sys.executable, "-c", INTERRUPT_RUNNER, str(script), str(target), *rest], cwd=str(d),
                                  env=child_env(**(env or {})), preexec_fn=_default_sigint, capture_output=True,
                                  text=True, encoding="utf-8", timeout=120)  # a hang guard only
        out, err = proc.stdout, proc.stderr
        self.assertEqual(proc.returncode, 130, out + err)
        envelope = json.loads(out)
        self.assertEqual((envelope["success"], envelope["data"]), (False, None))
        self.assertEqual((envelope["error"]["code"], envelope["error"]["recoverable"]), ("CANCELED", True))
        self.assertEqual(set(envelope["error"]), ERROR_KEYS)
        self.assertNotIn("Traceback", err)

    def test_jev_judge(self):
        # a dry-run batch is interrupted reading its request stream: no settings file, no PyYAML, no request is ever built
        self.interrupt([JJ, "batch", "--input", "{INPUT}", "--run-dir", "runs", "--dry-run"], "in.jsonl", git=True)

    @unittest.skipUnless(HAVE_YAML, "the settings file is read with PyYAML")
    def test_judge_jev_settings(self):
        self.interrupt([SCRIPTS / "judge_jev_settings.py", "show"], ".sc/judge-jev/settings.yaml", git=True)


if __name__ == "__main__":
    unittest.main()
