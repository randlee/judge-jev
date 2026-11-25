# Walk this repository's records with decidr and jq

This example reads a Raptor index and runs one request per MUST / MUST NOT
statement for REQ and NFR records, or one request per ADR. Its first wave asks
three gate questions. An answer with an unacceptable choice or confidence below
0.8 asks `which_part` next; otherwise the walk ends with `yes`. A diagnostic
ends with `review`. This example's bar is separate from judge-jev quality's
choice-based verdict rules.

The checked-in [HTML report](report.html) contains D2 diagrams and selectable
results. [report.md](report.md) contains the same observed paths as embedded
Mermaid diagrams. [recorded.json](recorded.json) holds the actual requests,
response envelopes, commands, and outcomes (execution locations use placeholders) from the live run. No fixture is
presented as a model response.

## Replay without sending text

Requires Python 3, D2 and sc-compose on PATH. Tested with Python 3.14.7,
D2 0.9.0 and sc-compose 1.9.0. Check them first:

```bash
python3 --version
d2 --version
sc-compose --version
python3 site/examples/decidr-pipeline/run.py --output /tmp/decidr-replay
open /tmp/decidr-replay/report.html /tmp/decidr-replay/report.md
```

Use a new output directory each time. The runner refuses to overwrite one.
Replay reruns the D2 and sc-compose rendering, with zero decision calls.
D2 can be installed with `brew install d2` on macOS; sc-compose's
[installation guide](https://github.com/randlee/sc-compose) covers its CLI.

## Run live on this checkout

Use only randlee/raptor's `integration/judge-jev` branch, pinned at
`8ce2be8363318be2f7c2e2b79d1f646399cab2fd`; the owner's local checkout is
`~/github/raptor-worktrees/integration-judge-jev`. Do not use Raptor develop.

Also requires `decidr`, `jq`, Bash, a working TypeSafe key, and Raptor's
pinned integration checkout with its Python environment. The repository's
README describes that Raptor installation. The runner reads records only
from Raptor's JSON export; it never parses record Markdown.

```bash
command -v decidr && decidr --version
command -v jq && jq --version
export RAPTOR=/path/to/raptor-integration-judge-jev
python3 site/examples/decidr-pipeline/run.py --live --raptor "$RAPTOR" \
  --first-model jev --second-model jev --bar 0.8 \
  --output /tmp/decidr-live
```

The default sample is `REQ-JEV-0001` (three statements), `ADR-JEV-0001`
(one record), and `NFR-JEV-0001` (four statements). Select other records with
repeated `--record ID`. To use an existing Raptor export, replace `--raptor`
with `--index /path/to/index.json`.

The initial Raptor import reported one existing `MODAL_MISMATCH` on
`REQ-JEV-0003`. The example reports that diagnostic and refuses to send a
selected record with diagnostics. It can still use the other clean records.
It does not edit the repository's records.

The second-stage guard accepts `--project` and `--agent-role` (or
`SC_PROJECT` and `DECIDR_AGENT_ROLE`); the example supplies them explicitly.
A tie with `none` is reported as unresolved, preserving the model choice.

The complete executable shell pipeline is `PIPELINE` in
[scripts/decision_examples.py](../../../scripts/decision_examples.py). It calls
`decidr send | jq | guarded decidr send | jq`, records every boundary, and
stops on an error. REQ/NFR choices are split into literal terms by the skill's
Python script, with prose stopwords removed. ADR diagnostics use actual section names. A model is selected
on each call. For Haiku in stage one, pass `--first-model haiku` and make its
credential available; a keychain timeout is an error, never a verdict.

## Diagram output modes

The same JSON tree drives the jq policy and the diagram renderer. Output
contains each tree JSON, D2 source, rendered SVG, and Mermaid source under
`diagrams/`, plus `run.json`, `report-data.json`, `report.html` and `report.md`.
The report is composed from
[the XHTML template](../../../templates/decision-report/report.xhtml.j2) using
`sc-compose render --var-file ... --check-render`.

The renderer also accepts the shipped quality-tree JSON:

```bash
python3 scripts/gen_tree_diagrams.py \
  --tree plugins/sc-judge-jev/install/templates/skills/judge-jev/assets/questions/quality-req.json \
  --format mmd --output /tmp/quality-req.mmd
```

`--format md` wraps the diagram in a Markdown Mermaid fence; `--format d2`
outputs D2 source. Add `--result /path/to/view.json` to highlight the actual
path recorded in a report view (an element of `recorded.json`'s `views`).

## Published reports

These example sources and their checked-in reports live under `site/examples/`.
After this PR reaches `main`, Pages publishes them in place. The dependency-free
`scripts/build-site.py` links this HTML report from the generated
[diagrams index](https://randlee.github.io/judge-jev/diagrams/index.html).
It makes no provider calls and does not need rendering tools in Pages CI.

The published HTML will be [this example](https://randlee.github.io/judge-jev/examples/decidr-pipeline/report.html).

To update a recorded example, rerun with a fresh output directory, copy
`run.json` to `recorded.json`, and copy `report.html` and `report.md` beside
this README. Commit those three files together. The Pages workflow watches
`site/**`, so a merged report update republishes the site.

## Recorded REQ-SAG-0104.s3 transcript

This is the original 2026-11-25 capture, before stopword filtering and the
configurable second-stage flags. Local execution paths are replaced with
placeholders; model response values and session identifiers are preserved.
The original which-part response tied `Cancel` and `none` at 0.22. The current
`verdict.jq` reports that tie as `which_part:none`, retains `model_choice:Cancel`,
and sets `tied_with_none:true`. The historical verdict below is retained as
original output, not presented as the current helper's interpretation.
Use the skill's current pipeline when running new requests.


Recorded on 2026-11-25, from sc-agent `plan/phase-j` at
`4c10054ffdb6c8e1475419f92aba4778e5437683`, file
`docs/sc-agent-types/requirements/REQ-SAG-0104.md`. The exact s3 statement is:

> When the user interrupts a command-line tool built on `sc-agent`, that tool MUST cancel the `Cancel` its operation holds.

These setup commands were run in the judge-jev worktree. In a consumer,
set `skill_dir` to the plugin skill folder and `sc_agent_repo` to your local
sc-agent clone. Keep the source revision pinned to reproduce the input.

```bash
skill_dir=plugins/sc-judge-jev/skills/walking-decidr-trees
sc_agent_repo={sc-agent}
run_root={sag-run}
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
{"item": "{sag-run}/example/item.json", "request": "{sag-run}/example/request.json"}
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

[The jq filter](../../../plugins/sc-judge-jev/skills/walking-decidr-trees/scripts/next.jq) consumes decidr's **envelope**, so answers
are at `.value.answers`. It gets the item from `--slurpfile item`, never
from a presumed echo in the result. It gets the script-generated terms from
`--slurpfile terms`. Its output is either a request or a terminal verdict.
[send-next.sh](../../../plugins/sc-judge-jev/skills/walking-decidr-trees/scripts/send-next.sh) guards the second decidr call: an empty
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
