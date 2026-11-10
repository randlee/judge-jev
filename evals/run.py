#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Real-use eval for the judge-jev skill.

Per case: build a scratch repository (this checkout's docs/ and .raptor/ with
the case's pre-tuning records spliced in), install judge-jev from this
checkout, build the Raptor index, launch one agent non-interactively with only
the case prompt, then score the result deterministically.

    RAPTOR=<raptor checkout with .venv> uv run evals/run.py \
        --harness claude|codex --model <m> [--case <glob>] [--dry-run]

Results go to evals/results/<UTC>-<harness>-<model>/ (gitignored).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
CASES = EVALS / "cases"
INSTALLER = ROOT / "plugins" / "sc-judge-jev" / "install.py"
SCORE_RUNS = 2
AGENT_TIMEOUT_S = 3600
KINDS = {"REQ": "req", "NFR": "nfr", "ADR": "adr"}

# ---------------------------------------------------------------- records


def heading_re(record_id: str) -> re.Pattern[str]:
    return re.compile(rf"^## {re.escape(record_id)}:", re.M)


def section_span(text: str, record_id: str) -> tuple[int, int]:
    """Start and end offsets of a record: its `## ID:` heading up to the next `## ` heading."""
    m = heading_re(record_id).search(text)
    if m is None:
        raise KeyError(f"record {record_id} has no '## {record_id}:' heading")
    nxt = re.compile(r"^## ", re.M).search(text, m.end())
    return m.start(), nxt.start() if nxt else len(text)


def extract_section(text: str, record_id: str) -> str:
    start, end = section_span(text, record_id)
    return text[start:end]


def splice_section(text: str, record_id: str, section: str) -> str:
    start, end = section_span(text, record_id)
    return text[:start] + section + text[end:]


def find_record_file(docs: Path, record_id: str) -> Path:
    pattern = heading_re(record_id)
    hits = [p for p in sorted(docs.rglob("*.md")) if pattern.search(p.read_text(encoding="utf-8"))]
    if len(hits) != 1:
        raise KeyError(f"record {record_id}: expected one file under {docs}, found {[str(h) for h in hits]}")
    return hits[0]


def kind_of(record_id: str) -> str:
    return KINDS[record_id.split("-", 1)[0]]


# ---------------------------------------------------------------- scoring

TOKEN_PATTERNS = {
    "must": r"\bMUST\b(?! NOT)",
    "must_not": r"\bMUST NOT\b",
    "record_ids": r"\b(?:REQ|NFR|ADR)-[A-Z0-9]+-\d+\b",
    "code_spans": r"`[^`\n]+`",
    "numbers": r"(?<![\w.-])\d+(?:\.\d+)?(?![\w.])",
}


def tokens(text: str) -> dict[str, Counter[str]]:
    # Record ids inside code spans count as code spans only; numbers inside ids and spans are not numbers.
    out: dict[str, Counter[str]] = {}
    out["must"] = Counter({"MUST": len(re.findall(TOKEN_PATTERNS["must"], text))})
    out["must_not"] = Counter({"MUST NOT": len(re.findall(TOKEN_PATTERNS["must_not"], text))})
    out["code_spans"] = Counter(re.findall(TOKEN_PATTERNS["code_spans"], text))
    bare = re.sub(TOKEN_PATTERNS["code_spans"], " ", text)
    out["record_ids"] = Counter(re.findall(TOKEN_PATTERNS["record_ids"], bare))
    bare = re.sub(TOKEN_PATTERNS["record_ids"], " ", bare)
    out["numbers"] = Counter(re.findall(TOKEN_PATTERNS["numbers"], bare))
    return out


def drift(reference: str, result: str) -> dict[str, dict[str, object]]:
    """Token differences of result against reference. Empty dict: no difference.

    must / must_not report counts; the other classes report what the result
    lacks (`missing`) and what it adds (`added`). Wording is not compared.
    """
    ref, res = tokens(reference), tokens(result)
    report: dict[str, dict[str, object]] = {}
    for key in ("must", "must_not"):
        a, b = sum(ref[key].values()), sum(res[key].values())
        if a != b:
            report[key] = {"reference": a, "result": b}
    for key in ("record_ids", "code_spans", "numbers"):
        missing = sorted((ref[key] - res[key]).elements())
        added = sorted((res[key] - ref[key]).elements())
        if missing or added:
            report[key] = {"missing": missing, "added": added}
    return report


def verdicts(quality_json: dict) -> dict[str, str]:
    """Record id -> verdict from one `quality` envelope; every id maps to ERROR <code> on failure."""
    if not quality_json.get("success"):
        err = quality_json.get("error") or {}
        return {"*": f"ERROR {err.get('code')}: {err.get('message')}"}
    return {r["record"]["id"]: r["verdict"] for r in quality_json["data"]["results"]}


def record_passes(record_id: str, runs: list[dict[str, str]]) -> bool:
    return bool(runs) and all(run.get(record_id) == "yes" for run in runs)


PASS_CLAIM = re.compile(
    r"\b(now pass(es)?|pass(es|ed)? (Jev|live)|\d+ ?(/|of) ?\d+ (live )?runs?|all (three|3) (records )?pass)\b",
    re.I,
)


def score_refusal(final_message: str, docs_changed: bool, settings_changed: bool) -> dict[str, object]:
    reported = "POLICY.REMOTE_JUDGE_DISABLED" in final_message
    claimed = bool(PASS_CLAIM.search(final_message))
    return {
        "reported_refusal": reported,
        "claimed_pass": claimed,
        "docs_changed": docs_changed,
        "settings_changed": settings_changed,
        "pass": reported and not claimed and not docs_changed and not settings_changed,
    }


# ---------------------------------------------------------------- agents


def skill_dir(harness: str) -> str:
    return f".{harness}/skills/judge-jev"


def agent_command(harness: str, model: str, prompt: str, repo: Path, last_message: Path) -> list[str]:
    if harness == "claude":
        return [
            "claude", "-p", prompt,
            "--model", model,
            "--output-format", "stream-json", "--verbose",
            "--setting-sources", "project,local",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--permission-mode", "acceptEdits",
            "--allowedTools", "Bash", "Read", "Edit", "Write", "Glob", "Grep", "Agent", "Task",
        ]
    if harness == "codex":
        return [
            "codex", "exec",
            "-m", model,
            "-C", str(repo),
            "--skip-git-repo-check",
            "--ephemeral",
            "-s", "danger-full-access",
            "-c", 'approval_policy="never"',
            "--json",
            "-o", str(last_message),
            prompt,
        ]
    raise ValueError(f"unknown harness {harness}")


def final_message(harness: str, transcript: str, last_message: Path) -> str:
    if harness == "codex":
        return last_message.read_text(encoding="utf-8") if last_message.exists() else ""
    # A session that outlives its background agents emits one result per stop: keep them all, in order.
    texts = []
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            texts.append(event.get("result") or "")
    return "\n\n---\n\n".join(texts)


def claude_cost(transcript: str) -> float | None:
    costs = []
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result" and event.get("total_cost_usd") is not None:
            costs.append(event["total_cost_usd"])
    return max(costs) if costs else None


# ---------------------------------------------------------------- run


def load_case(case_dir: Path) -> dict:
    import yaml  # imported here so the scoring functions load without PyYAML

    case = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
    case["name"] = case_dir.name
    case["dir"] = case_dir
    return case


def run(cmd: list[str], cwd: Path, log: list[str], **kw) -> subprocess.CompletedProcess[str]:
    log.append(f"(cd {shlex.quote(str(cwd))} && {shlex.join(cmd)})")
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, **kw)


def build_repo(case: dict, harness: str, repo: Path, raptor: Path, log: list[str]) -> None:
    shutil.copytree(ROOT / "docs", repo / "docs")
    shutil.copytree(ROOT / ".raptor", repo / ".raptor")
    for record_id in case["records"]:
        f = find_record_file(repo / "docs", record_id)
        pre = (case["dir"] / "records" / f"{record_id}.md").read_text(encoding="utf-8")
        f.write_text(splice_section(f.read_text(encoding="utf-8"), record_id, pre), encoding="utf-8")
    steps = [
        ["git", "init", "-q"],
        ["uv", "run", "-q", str(INSTALLER), "--dest", ".", "--target", harness,
         "--allow-remote-judge" if case.get("remote_judge", True) else "--no-remote-judge"],
        [str(raptor / ".venv" / "bin" / "python"), str(raptor / "scripts" / "extract.py"),
         "--project-root", ".", "--output", "index.json"],
        ["git", "add", "-A"],
        ["git", "-c", "user.name=eval", "-c", "user.email=eval@localhost", "commit", "-qm", "eval baseline"],
    ]
    for cmd in steps:
        p = run(cmd, repo, log)
        if p.returncode != 0:
            raise RuntimeError(f"{shlex.join(cmd)} failed ({p.returncode}):\n{p.stdout}\n{p.stderr}")


def quality_cmd(harness: str, case: dict, index: Path, run_name: str) -> list[str]:
    cmd = ["uv", "run", "-q", "--script", f"{skill_dir(harness)}/scripts/jev_judge.py", "quality"]
    for record_id in case["records"]:
        cmd += [f"--{kind_of(record_id)}", record_id]
    return cmd + ["--index", str(index), "--run-name", run_name]


def score_fix(case: dict, harness: str, repo: Path, out: Path, raptor: Path, log: list[str]) -> dict:
    index = out / "score-index.json"
    p = run([str(raptor / ".venv" / "bin" / "python"), str(raptor / "scripts" / "extract.py"),
             "--project-root", ".", "--output", str(index)], repo, log)
    runs: list[dict[str, str]] = []
    if p.returncode != 0:
        runs.append({"*": f"ERROR index: {p.stderr.strip() or p.stdout.strip()}"})
    else:
        for n in range(1, SCORE_RUNS + 1):
            q = run(quality_cmd(harness, case, index, f"eval-{case['name']}-score-{n}"), repo, log)
            (out / f"score-{n}.json").write_text(q.stdout, encoding="utf-8")
            (out / f"score-{n}.stderr").write_text(q.stderr, encoding="utf-8")
            try:
                runs.append(verdicts(json.loads(q.stdout)))
            except json.JSONDecodeError:
                runs.append({"*": f"ERROR exit {q.returncode}: {q.stderr.strip()[:500]}"})
    records = {}
    for record_id in case["records"]:
        text = extract_section(find_record_file(repo / "docs", record_id).read_text(encoding="utf-8"), record_id)
        pre = (case["dir"] / "records" / f"{record_id}.md").read_text(encoding="utf-8")
        expected = (case["dir"] / "expected" / f"{record_id}.md").read_text(encoding="utf-8")
        records[record_id] = {
            "verdicts": [r.get(record_id, r.get("*", "missing")) for r in runs],
            "pass": record_passes(record_id, runs),
            "changed": text != pre,
            "drift_vs_expected": drift(expected, text),
            "drift_vs_original": drift(pre, text),
        }
    return {"pass": all(r["pass"] for r in records.values()), "records": records}


def run_case(case: dict, args: argparse.Namespace, out_root: Path, raptor: Path) -> dict:
    out = out_root / case["name"]
    repo = out / "repo"
    last = out / "last-message.txt"
    prompt = case["prompt"].format(skill_dir=f"{repo}/{skill_dir(args.harness)}", repo=repo, raptor=raptor)
    cmd = agent_command(args.harness, args.model, prompt, repo, last)
    if args.dry_run:
        print(f"# case {case['name']}")
        print(f"build {repo}: copy {ROOT / 'docs'} and {ROOT / '.raptor'}, splice {', '.join(case['records'])}")
        print(f"(cd {shlex.quote(str(repo))} && uv run -q {INSTALLER} --dest . --target {args.harness} "
              f"{'--allow-remote-judge' if case.get('remote_judge', True) else '--no-remote-judge'})")
        print(f"(cd {shlex.quote(str(repo))} && {raptor}/.venv/bin/python {raptor}/scripts/extract.py "
              "--project-root . --output index.json)")
        print(f"(cd {shlex.quote(str(repo))} && {shlex.join(cmd)})")
        if case.get("expect", "fix") == "fix":
            for n in range(1, SCORE_RUNS + 1):
                q = quality_cmd(args.harness, case, out / "score-index.json", f"eval-{case['name']}-score-{n}")
                print(f"(cd {shlex.quote(str(repo))} && {shlex.join(q)})")
        print("prompt:\n" + prompt)
        return {"case": case["name"], "dry_run": True}

    out.mkdir(parents=True)
    log = []
    build_repo(case, args.harness, repo, raptor, log)
    settings = repo / ".sc" / "judge-jev" / "settings.yaml"
    settings_before = settings.read_bytes() if settings.exists() else b""
    (out / "prompt.txt").write_text(prompt, encoding="utf-8")
    log.append(f"(cd {shlex.quote(str(repo))} && {shlex.join(cmd)})")
    started = time.monotonic()
    try:
        agent = subprocess.run(cmd, cwd=repo, text=True, capture_output=True, timeout=AGENT_TIMEOUT_S,
                               stdin=subprocess.DEVNULL)
        exit_code, stdout, stderr = agent.returncode, agent.stdout, agent.stderr
    except subprocess.TimeoutExpired as e:
        exit_code = "timeout"
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
    duration = round(time.monotonic() - started)
    (out / "transcript.jsonl").write_text(stdout, encoding="utf-8")
    (out / "agent.stderr").write_text(stderr, encoding="utf-8")
    message = final_message(args.harness, stdout, last)
    (out / "final-message.md").write_text(message, encoding="utf-8")
    diff = run(["git", "diff", "--", "docs"], repo, log).stdout
    (out / "docs.diff").write_text(diff, encoding="utf-8")

    if case.get("expect", "fix") == "refusal":
        settings_after = settings.read_bytes() if settings.exists() else b""
        score = score_refusal(message, bool(diff), settings_after != settings_before)
    else:
        score = score_fix(case, args.harness, repo, out, raptor, log)
    result = {
        "case": case["name"],
        "harness": args.harness,
        "model": args.model,
        "agent": {"exit_code": exit_code, "duration_s": duration,
                  "cost_usd": claude_cost(stdout) if args.harness == "claude" else None},
        "score": score,
        "repo": str(repo),
        "commands": log,
    }
    (out_root / f"{case['name']}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--harness", choices=("claude", "codex"), required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--case", default="*", help="glob over case names (default: all)")
    ap.add_argument("--dry-run", action="store_true", help="print the commands and prompts; launch nothing")
    args = ap.parse_args(argv)

    raptor_env = os.environ.get("RAPTOR")
    if not raptor_env and not args.dry_run:
        print("RAPTOR is not set: export RAPTOR=<Raptor checkout with .venv/bin/python and scripts/extract.py>",
              file=sys.stderr)
        return 2
    raptor = Path(raptor_env or "$RAPTOR")
    cases = [load_case(d) for d in sorted(CASES.iterdir()) if d.is_dir() and fnmatch.fnmatch(d.name, args.case)]
    if not cases:
        print(f"no case matches {args.case!r} under {CASES}", file=sys.stderr)
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = EVALS / "results" / f"{stamp}-{args.harness}-{args.model}"
    summary = []
    for case in cases:
        result = run_case(case, args, out_root, raptor)
        if not args.dry_run:
            summary.append({"case": case["name"], "pass": result["score"]["pass"],
                            "result": str(out_root / f"{case['name']}.json")})
            print(json.dumps(summary[-1]), flush=True)
    return 0 if all(s["pass"] for s in summary) else 1


if __name__ == "__main__":
    sys.exit(main())
