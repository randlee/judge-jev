"""Run offline test children with closed input and a failure-only hang backstop."""
import subprocess

CHILD_HANG_GUARD_SECONDS = 120


def run_child(args, **options):
    payload = options.pop("input", None)
    options.update(capture_output=True, timeout=CHILD_HANG_GUARD_SECONDS)
    if payload is None:
        options["stdin"] = subprocess.DEVNULL
    else:
        options["input"] = payload
    try:
        return subprocess.run(args, **options)
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            f"child exceeded the {CHILD_HANG_GUARD_SECONDS}s hang backstop: {error.cmd!r}\n"
            f"captured stdout: {error.stdout!r}\ncaptured stderr: {error.stderr!r}"
        ) from error
