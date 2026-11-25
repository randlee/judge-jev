---
name: walking-decidr-trees
description: Walk a question tree with decidr and jq, sending one wave of questions per stage. Use when building or explaining a staged decision pipeline, routing low-confidence gate answers to a which-part question, or comparing Jev and Haiku on the same request.
metadata:
  version: "0.8.0"
---

# Walking decidr question trees

## Step 1 — Verify CLI dependencies

```bash
command -v decidr && decidr --version
command -v jq && jq --version
command -v python3 && python3 --version
command -v git && git --version
```

Recorded environment: decidr 0.3.6, jq 1.7.1-apple, Python 3.14.7,
git 2.55.0. These are tested versions, not claimed minimum versions.
If a CLI is missing, stop and use the inline troubleshooting below. Do this
before preparing inputs or sending requests.

### Installation and troubleshooting

The author's requested package contains one SKILL.md plus executable scripts,
so installation guidance is inline instead of a separate reference file.
Check existing installs before installing anything:

```bash
for p in "$HOME/.local/bin/decidr" "$HOME/.venvs/decidr/bin/decidr" \
  /opt/homebrew/bin/decidr /usr/local/bin/decidr; do
  if [ -x "$p" ]; then "$p" --version; break; fi
done
```

Add the discovered directory to this session's PATH; the child scripts also
resolve decidr and jq through PATH. Claude Code's PATH can differ from the
interactive shell. Use the [sc-agent binary releases](https://github.com/randlee/sc-agent/releases)
for Linux or other platforms, `brew install randlee/tap/decidr` on macOS, or
`winget install --id randlee.decidr --exact` on Windows (run this Bash pipeline
in a Bash environment). The sc-decidr Python wheel is not the decidr CLI.
Install jq, Python 3 and Git with the platform's package manager if missing,
then rerun the four version checks. Do not silently substitute another client.

Supply `--project` and `--agent-role` on every send. The fresh worktree lacked
a default project. Credentials come from decidr's environment, repository
`.env`, or platform keychain. Do not print keys or put them in request files.
For `secrets.keyring_timeout`, stop and follow the returned action; never
interpret the error as a failed gate answer or automatically retry it.

## Contract and tree

Run from the consumer repository. Resolve `skill_dir` to this SKILL.md's
folder in the installed plugin; with Claude Code it is
`${CLAUDE_PLUGIN_ROOT}/skills/walking-decidr-trees`. No files belong in this
repository's `.claude/` or `.codex/`. This skill is exposed directly by the
marketplace plugin, independently of the judge-jev installer.

Inputs: an item JSON file (`id`, `title`, and `text`), where `text` is JSON
containing `statement: {index, text}` and the full `record` as context; a
request containing `state.item` and three questions; and a numeric `bar` in
[0,1]. The example helper reads the supplied REQ-SAG-0104 Markdown, extracts
its third MUST bullet, and writes `item.json` and `request.json` into a **new**
output directory. It refuses to overwrite that directory.

This example tree accepts `obligations=1`, `term=yes`, `checkable=yes` only
when every answer's confidence is at least the bar (0.8 here). A different
choice or confidence below the bar selects the first failing gate in that
order and asks one `which_part` question next. This is a demonstration policy,
not the existing judge-jev quality tree or confidence aggregator.

| Stage outcome | Action |
|---|---|
| `ok:false` | Print the actual error to stderr, exit nonzero, send nothing further. |
| All gates pass | The tree ends early: print `verdict:yes`; there is no next request. |
| An answer is under the bar | Build a request with the original item from its file and `which_part` choices made from the statement's literal terms plus `none`. |

One wave is one decidr call containing all of that stage's questions. No
model is assigned to the whole pipeline: each send chooses its own model.
A terminal JSON object travels through the guard so it can be printed on
stdout without being sent to a model. The second stage returns `review`
with the selected term and its confidence; it does not turn a tentative
localization into a proof or a free-text explanation. `none` also means review.

The helpers read only supplied files and stdin. `prepare.py` writes the two
example input files; the shell examples write their named run files. decidr
sends the record to the selected provider and writes its own session logs.
Use text authorized for that provider. No helper edits records or either
judge-jev implementation. Keep run files in a temporary directory. A replay
of saved JSON makes no first-stage call; rerunning a send makes a new call.

## Prepare the real example

Recorded on 2026-11-25, from sc-agent `plan/phase-j` at
`4c10054ffdb6c8e1475419f92aba4778e5437683`, file
`docs/sc-agent-types/requirements/REQ-SAG-0104.md`. The exact s3 statement is:

> When the user interrupts a command-line tool built on `sc-agent`, that tool MUST cancel the `Cancel` its operation holds.

These setup commands were run in the judge-jev worktree. In a consumer,
set `skill_dir` to the plugin skill folder and `sc_agent_repo` to your local
sc-agent clone. Keep the source revision pinned to reproduce the input.

```bash
skill_dir=plugins/sc-judge-jev/skills/walking-decidr-trees
sc_agent_repo=/Users/randlee/github/sc-agent
run_root=/tmp/decidr-question-tree.JGEvtz
run_dir="$run_root/example"
git -C "$sc_agent_repo" show 4c10054ffdb6c8e1475419f92aba4778e5437683:docs/sc-agent-types/requirements/REQ-SAG-0104.md > "$run_root/record.md"
python3 "$skill_dir/scripts/prepare.py" "$run_root/record.md" "$run_dir"
python3 "$skill_dir/scripts/terms.py" "$run_dir/item.json" > "$run_dir/terms.json"
cat "$run_dir/terms.json"
```

For a new run choose a fresh temporary `run_root` (for example with
`mktemp -d`); the recorded output directory already exists on the author's
machine. Setup printed:

```json
{"item": "/tmp/decidr-question-tree.JGEvtz/example/item.json", "request": "/tmp/decidr-question-tree.JGEvtz/example/request.json"}
["When", "the", "user", "interrupts", "a", "command-line", "tool", "built", "on", "sc-agent", "that", "MUST", "cancel", "Cancel", "its", "operation", "holds", "none"]
```

`terms.py` performs the splitting, **not jq**: backtick names stay intact,
hyphenated words stay intact, duplicates are removed, and case is preserved
(`cancel` and `Cancel` differ). These are lexical terms, including ordinary
words, not invented semantic phrases. The sentinel is `none`.

The complete request below is the actual `request.json` used in the run;
its three questions were copied from quality-req's gate wave, without the
two diagnostic questions. `record` includes the source's definitions.

```json
{
  "state": {
    "item": {
      "id": "REQ-SAG-0104.s3",
      "title": "Cancel token",
      "text": "{\"statement\": {\"index\": 3, \"text\": \"When the user interrupts a command-line tool built on `sc-agent`, that tool MUST cancel the `Cancel` its operation holds.\"}, \"record\": \"# Requirement: Cancel token\\n\\n**Status:** Approved  \\n**Version:** 0.3.0  \\n**Created:** 2026-11-09  \\n**Last Updated:** 2026-11-25  \\n**Owner:** Rand Lee  \\n\\n---\\n\\n## REQ-SAG-0104: Cancel token\\n\\n**Status:** Approved  \\n\\n### Requirement Statement\\n\\nDefinitions: `Cancel` is the Rust type in the `sc-agent` crate that carries one cancellation signal; code cancels it, and every operation holding it stops. An operation is a call `sc-agent` is running. An operation stops when it returns the `decision.cancelled` error without finishing its work. A crate is a Rust package in this repository. A command-line tool built on `sc-agent` is a binary in this repository that calls the `sc-agent` crate; today `decidr` and `sitr`. PyO3 is the Rust library that builds the `sc_agent` Python module from Rust code; the PyO3 bindings are that module. A user interrupts a command-line tool by pressing Ctrl-C or sending it SIGTERM.\\n\\n**MUST statements:**\\n\\n- `sc-agent` MUST provide a `Cancel` type.\\n- Cancelling a `Cancel` MUST stop an operation that holds it and runs in another crate.\\n- When the user interrupts a command-line tool built on `sc-agent`, that tool MUST cancel the `Cancel` its operation holds.\\n- The PyO3 bindings MUST let Python code cancel the `Cancel` an operation holds.\\n\\n### Rationale\\n\\nEvery crate that runs an `sc-agent` call must agree on one cancellation signal, so a cancel from a command-line tool or from Python reaches every crate doing the work.\\n\\nOwner ruling 2026-11-21: records follow docs/plans/reduction-plan.md.\\n\\n### Success Criteria\\n\\n**Acceptance Criteria:**\\n\\n- [ ] A unit test creates a `Cancel` in one crate, cancels it, and shows an operation in another crate stops.\\n- [ ] A CLI run interrupted by the user stops its running operation and exits.\\n- [ ] A Python test cancels a running operation through the bindings and shows it stops.\"}"
    }
  },
  "questions": {
    "obligations": {
      "type": "choice",
      "instructions": "`item.text` is JSON: `statement` is one MUST or MUST NOT statement of the requirement record in `record`. Judge only `statement`; use `record` as context. How many independent obligations does this statement impose?",
      "criteria": {
        "1": "One obligation.",
        "2": "Two independent obligations.",
        "3": "Three independent obligations.",
        "4+": "Four or more independent obligations."
      }
    },
    "term": {
      "type": "choice",
      "instructions": "`item.text` is JSON: `statement` is one MUST or MUST NOT statement of the requirement record in `record`. Judge only `statement`; use `record` as context. Is every term in this statement common usage, defined in this record, or defined in a linked record?",
      "criteria": {
        "yes": "Every term is common usage, defined in this record, or defined in a linked record.",
        "no": "At least one term is none of these."
      }
    },
    "checkable": {
      "type": "choice",
      "instructions": "`item.text` is JSON: `statement` is one MUST or MUST NOT statement of the requirement record in `record`. Judge only `statement`; use `record` as context. Can a tester decide whether this statement holds?",
      "criteria": {
        "yes": "Yes, by a test, a command run, or reading files.",
        "needs a measure": "A check exists only once a measure is stated.",
        "no": "Nothing could check it."
      }
    }
  }
}
```

## Execute one stage per wave

This is the executable form of:

```text
decidr send < request.json | jq (build next request) | decidr send | jq (verdict)
```

[The jq filter](scripts/next.jq) consumes decidr's **envelope**, so answers
are at `.value.answers`. It gets the item from `--slurpfile item`, never
from a presumed echo in the result. It gets the script-generated terms from
`--slurpfile terms`. Its output is either a request or a terminal verdict.
[send-next.sh](scripts/send-next.sh) guards the second decidr call: an empty
stream causes no call, and a leaf is printed unchanged. This guard is needed
because starting bare `decidr send` on an early-ending stream would send
empty stdin and produce a parse error. `pipefail` preserves failures even
when downstream stages receive no data. Do not use `set -e` to discard the
first call's error envelope before jq can read it.

The following identical pipeline was run with Jev and with Haiku in stage
one; stage two explicitly uses Jev in both. The `tee` files are unmodified
recordings of each boundary. Neither jq script wraps CLI JSON in Markdown;
only the skill's human-facing report fences JSON.

```bash
set -o pipefail
first_model=jev # then run again with first_model=haiku
decidr send --project decidr-question-tree --model "$first_model" --agent-role skill-author < "$run_dir/request.json" \
  | tee "$run_dir/$first_model-gates.jsonl" \
  | jq -c --slurpfile item "$run_dir/item.json" --slurpfile terms "$run_dir/terms.json" --argjson bar 0.8 -f "$skill_dir/scripts/next.jq" \
  | tee "$run_dir/$first_model-next.jsonl" \
  | bash "$skill_dir/scripts/send-next.sh" jev \
  | tee "$run_dir/$first_model-stage2.jsonl" \
  | jq -c -f "$skill_dir/scripts/verdict.jq" > "$run_dir/$first_model-verdict.jsonl"
decidr_rc=$?
cat "$run_dir/$first_model-gates.jsonl" "$run_dir/$first_model-stage2.jsonl" "$run_dir/$first_model-verdict.jsonl"
printf 'pipeline_exit=%s\n' "$decidr_rc"
```

Jev: real first-stage result line, real second-stage result line, then
jq's final verdict:

```json
{"ok":true,"value":{"answers":{"checkable":{"choice":"yes","confidence":0.98,"probabilities":{"needs a measure":0.01,"no":0.0,"yes":0.99},"type":"choice"},"obligations":{"choice":"1","confidence":0.91,"probabilities":{"1":0.93,"2":0.05,"3":0.02,"4+":0.0},"type":"choice"},"term":{"choice":"yes","confidence":0.76,"probabilities":{"no":0.12,"yes":0.88},"type":"choice"}},"attempts":1,"model":"jev-1.14.0","question_digests":{"checkable":"9383dc5dd6b0f339c53586651dcd507bcfddbd62ba22f9826d1278220bb40f88","obligations":"aebc21aa34a049bbf29154a60207b73cf734f1c12a48123309488ae46cecad80","term":"fa0c939f0fdfbd5e51eacbd37f0e88d4e3b7999a7402c9d731677548292c5650"},"session_id":"01M8A35RJEXWRFXKEXEVJSQG1N","usage":{"input_tokens":1224,"output_tokens":114}}}
{"ok":true,"value":{"answers":{"which_part":{"choice":"Cancel","confidence":0.17,"probabilities":{"Cancel":0.22,"MUST":0.16,"When":0.01,"a":0.01,"built":0.0,"cancel":0.11,"command-line":0.0,"holds":0.03,"interrupts":0.04,"its":0.09,"none":0.22,"on":0.0,"operation":0.03,"sc-agent":0.03,"that":0.01,"the":0.02,"tool":0.01,"user":0.01},"type":"choice"}},"attempts":1,"model":"jev-1.14.0","question_digests":{"which_part":"9327b4dd90307f0f52a2fb257aaf74ec717d20214172b0eff12dcc864364e807"},"session_id":"01M8A35RR21MEBFM4QK4PGNVD4","usage":{"input_tokens":1511,"output_tokens":149}}}
{"verdict":"review","stage":"which-part","which_part":"Cancel","confidence":0.17,"model":"jev-1.14.0"}
```

```text
pipeline_exit=0
```

To inspect what the jq filter actually built:

```bash
jq -c '.state.gate, (.questions.which_part.criteria | keys)' "$run_dir/jev-next.jsonl"
```

Actual output (the next request also contains the original file-supplied item):

```json
{"question":"term","answer":{"choice":"yes","confidence":0.76,"probabilities":{"no":0.12,"yes":0.88},"type":"choice"},"cause":"confidence"}
["Cancel","MUST","When","a","built","cancel","command-line","holds","interrupts","its","none","on","operation","sc-agent","that","the","tool","user"]
```

Haiku: the same pipeline was attempted with `--model haiku`. It returned
this real first-stage result, **not an answer**:

```json
{"error":{"action":"Approve keychain access, or set the environment variable or .env key.","category":"auth","id":"secrets.keyring_timeout","message":"OS keychain did not answer for ANTHROPIC_API_KEY; it may be waiting for approval. Approve access or set ANTHROPIC_API_KEY in the environment or .env.","session_id":"01M8A35S19JG04JTZCVGD940SQ"},"ok":false}
```

The CLI exited 1. `next.jq` printed that error object with jq's error prefix
to stderr, emitted nothing, and exited 5. The pipeline therefore printed
`pipeline_exit=5`; `haiku-next.jsonl`, `haiku-stage2.jsonl` and
`haiku-verdict.jsonl` were empty. No second model call was made. A successful
Haiku gate comparison remains unverified until its credential is available;
do not present this run as agreement between models.

## Exercise early termination and failure without another model call

The saved **real** Jev gate result ends early when replayed with bar 0.6:

```bash
jq -c --slurpfile item "$run_dir/item.json" --slurpfile terms "$run_dir/terms.json" --argjson bar 0.6 -f "$skill_dir/scripts/next.jq" "$run_dir/jev-gates.jsonl" \
  | bash "$skill_dir/scripts/send-next.sh" jev \
  | jq -c -f "$skill_dir/scripts/verdict.jq"
```

Actual stdout, exit 0:

```json
{"verdict":"yes","stage":"gates","item":"REQ-SAG-0104.s3"}
```

The same filter's error path was also replayed from the real Haiku error:

```bash
jq -c --slurpfile item "$run_dir/item.json" --slurpfile terms "$run_dir/terms.json" --argjson bar 0.8 -f "$skill_dir/scripts/next.jq" "$run_dir/haiku-gates.jsonl"
```

It printed the actual error above to stderr with a `jq: error` prefix,
produced zero stdout, and exited 5. `verdict.jq` independently checks
`ok:false` for failures in stage two as well.

Deterministic validation used saved live JSON and controlled inputs: all
three routing outcomes, confidence exactly at the bar, an unacceptable
choice at high confidence, missing answers, and stage-two failures. A
controlled decidr executable verified that a leaf or empty input makes
zero calls. No sleeps, event-loop ordering, races, or live model answer
assertions are used as tests.

## Observations about the CLI facts

No supplied fact was contradicted. With no input-file flag, each send read
the request from stdin and wrote one JSON line with `ok` and `value` or
`error`; observed send exits were 0 and 1. `--model` is per call. Required
`--agent-role` and a configured or explicit project are additional
prerequisites; the first attempt without `--project` returned
`config.missing_project`. jq's pipeline exit 5 is separate from decidr's
exit 1. Success envelopes include model, session, usage and digest data;
preserve those raw lines instead of reconstructing them.

Report the actual commands, their stdout/stderr and exit codes, and any
contradiction in fenced code blocks. Keep failed calls distinct from
verdicts. Stop on errors; do not fabricate a missing model result.

## Runnable repository examples

The source repository contains two examples, each with recorded live responses,
a runnable replay script, an HTML report composed with sc-compose, and a
Markdown report with embedded Mermaid diagrams. D2 renders the HTML diagrams.
Run these from the source repository with fresh output directories:

```bash
python3 site/examples/decidr-pipeline/run.py --output /tmp/decidr-example-replay
python3 site/examples/judge-jev-quality/run.py --output /tmp/quality-example-replay
```

`site/examples/decidr-pipeline/README.md` documents the direct staged CLI walk on
REQ, ADR, and NFR records obtained from Raptor. Its optional `--slurpfile tree`
input to `next.jq` supplies each kind's policy; REQ/NFR split literal terms,
while ADRs offer actual section names. The original REQ-SAG-0104 pipeline
above still works without that optional input.

`site/examples/judge-jev-quality/README.md` runs the installed quality command and
renders its shipped trees and recorded paths. It preserves quality's
choice-based verdicts. Both examples replay by default; `--live` sends new
requests. These examples belong to the source repository and are not assumed
to be present in a consumer's installed skill directory.

## Why stage (not yet available)

A free-form “why does this term cause the problem?” stage needs the `text`
answer kind in sc-agent. The inspected `Answer` enum in
`crates/sc-agent/src/lib.rs` supports `choice`, `score`, `noul` and `box`,
not `text`. The which-part stage can select a literal term or `none`; it
cannot supply that explanation. Do not advertise or emulate a why stage
through an invented choice answer.
