"""The child guard is a backstop, never an elapsed-time acceptance condition."""
import subprocess
import sys
import unittest
from unittest import mock

from child_support import CHILD_HANG_GUARD_SECONDS, run_child


class ChildSupport(unittest.TestCase):
    def test_unused_input_is_closed_and_supplied_input_is_preserved(self):
        command = [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"]
        for payload, expected in [(None, b""), (b"controlled stdin", b"controlled stdin")]:
            with self.subTest(payload=payload):
                result = run_child(command, input=payload)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected, b""))

    def test_timeout_failure_contains_both_captured_streams(self):
        def timeout(args, **options):
            self.assertEqual(options["timeout"], 120)
            self.assertEqual(options["timeout"], CHILD_HANG_GUARD_SECONDS)
            self.assertEqual(options["stdin"], subprocess.DEVNULL)
            self.assertTrue(options["capture_output"])
            raise subprocess.TimeoutExpired(args, options["timeout"], output=b"partial stdout", stderr=b"partial stderr")
        with mock.patch("child_support.subprocess.run", side_effect=timeout):
            with self.assertRaises(AssertionError) as caught:
                run_child(["controlled-child"])
        self.assertIn("partial stdout", str(caught.exception))
        self.assertIn("partial stderr", str(caught.exception))
        self.assertIn("controlled-child", str(caught.exception))
        self.assertIsInstance(caught.exception.__cause__, subprocess.TimeoutExpired)


if __name__ == "__main__":
    unittest.main()
