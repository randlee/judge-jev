"""Run offline test children with closed input and a failure-only hang backstop."""
import subprocess

CHILD_HANG_GUARD_SECONDS = 120


def run_child(args, *, hang_guard=CHILD_HANG_GUARD_SECONDS, **options):
    for reserved in ("timeout", "capture_output"):
        if reserved in options:
            raise TypeError(f"run_child controls {reserved}")
    if not 0 < hang_guard <= CHILD_HANG_GUARD_SECONDS:
        raise ValueError("hang_guard must be positive and no greater than the suite backstop")
    payload = options.pop("input", None)
    options.update(capture_output=True, timeout=hang_guard)
    if payload is None:
        options["stdin"] = subprocess.DEVNULL
    else:
        options["input"] = payload
    try:
        return subprocess.run(args, **options)
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            f"child exceeded the {hang_guard}s hang backstop: {error.cmd!r}\n"
            f"captured stdout: {error.stdout!r}\ncaptured stderr: {error.stderr!r}"
        ) from error
