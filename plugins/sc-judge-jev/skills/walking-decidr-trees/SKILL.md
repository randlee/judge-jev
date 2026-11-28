---
name: walking-decidr-trees
description: Walk a question tree with decidr and jq, sending one wave of questions per stage. Use when building a staged decision pipeline, routing uncertain gate answers to a which-part question, or comparing Jev and Haiku on the same request.
metadata:
  version: "0.9.1"
---

# Walking decidr question trees

## Step 1 — Verify dependencies

The shell pipeline requires a POSIX environment with Bash (macOS or Linux).
On Windows use WSL with Linux Python and CLIs; native Windows is unsupported.

```bash
command -v bash && bash --version
command -v decidr && decidr --version
command -v jq && jq --version
command -v python3 && python3 --version
```

Stop if a dependency is missing. Check existing decidr locations before installing:

```bash
for p in "$HOME/.local/bin/decidr" /opt/homebrew/bin/decidr /usr/local/bin/decidr; do
  if [ -x "$p" ]; then "$p" --version; break; fi
done
```

Put the discovered directory on PATH for the child scripts too. Install the
CLI from [sc-agent releases](https://github.com/randlee/sc-agent/releases) or
`brew install randlee/tap/decidr`; the sc-decidr Python wheel is a different
entry point. Install jq and Python 3 with the platform's package manager.

## Contract

`decidr send` reads one request from stdin when no input file is given and
writes one JSON line: `{"ok":true,"value":…}` or `{"ok":false,"error":…}`.
It exits 0 or 1; choose the model separately on every call. Supply a project
and an agent role. Credentials stay in decidr's environment, repository `.env`
or keychain, never in request files or reports.

The item file contains `id`, `title` and `text`. For REQ/NFR, `text` is JSON
with `statement:{index,text}` and the whole `record` as context. The default
first wave asks `obligations`, `term` and `checkable` together. Accepted choices
are `1`, `yes`, `yes`, each with confidence at least the supplied bar.

| Stage outcome | Action |
|---|---|
| `ok:false` | Print the actual error to stderr, exit nonzero, send nothing further. |
| Every gate meets the bar | Print `verdict:yes`; the tree ends and makes no second call. |
| A choice or confidence is under the bar | Ask `which_part` about the first such gate, with the item supplied from its file. |

One wave is one decidr call containing all that wave's questions. `next.jq`
uses `.value.answers`, not an assumed echo of the request. Its next request
gets the original item from `--slurpfile item`. `terms.py` splits the
statement into runs of words between stopwords and punctuation, preserves
whole backticked names and negation, and adds `none`. ADR examples offer actual
section names. An optional `--slurpfile tree` supplies the example's ADR/NFR
policy; omitting it uses the default three REQ gates.

The terminal `review` is a follow-up state: an answer missed an accepted
choice or the confidence bar (0.8 in the example). It is **not** a judge-jev
quality failure. The which-part stage localizes the uncertainty; it does not
explain it. A top-probability tie with `none` reports `which_part:none`,
`model_choice` and `tied_with_none:true`, without altering the raw response.

## Step 2 — Prepare an item and request

Resolve `skill_dir` to this SKILL.md's folder in the plugin. Claude Code
provides `${CLAUDE_PLUGIN_ROOT}/skills/walking-decidr-trees`; in another
harness use this file's location. Run from the consumer repository.

For the documented REQ-SAG-0104.s3 example, supply the REQ-SAG-0104 Markdown
from sc-agent `plan/phase-j` as `record.md`. The helper extracts the third
MUST statement and writes the item and three-question request into a **new**
output directory; it refuses to overwrite an existing directory.

```bash
python3 "$skill_dir/scripts/prepare.py" record.md "$run_dir"
python3 "$skill_dir/scripts/terms.py" "$run_dir/item.json" > "$run_dir/terms.json"
```

## Step 3 — Send one wave, build the next, then print the verdict

Set `project` and `agent_role` for this run. Choose `first_model` and
`second_model` independently (`jev` or `haiku`, for example).

```bash
set -o pipefail
decidr send --project "$project" --agent-role "$agent_role" --model "$first_model" < "$run_dir/request.json" \
  | tee "$run_dir/gates.jsonl" \
  | jq -c --slurpfile item "$run_dir/item.json" --slurpfile terms "$run_dir/terms.json" --argjson bar 0.8 -f "$skill_dir/scripts/next.jq" \
  | tee "$run_dir/next.jsonl" \
  | bash "$skill_dir/scripts/send-next.sh" "$second_model" --project "$project" --agent-role "$agent_role" \
  | tee "$run_dir/stage2.jsonl" \
  | jq -c -f "$skill_dir/scripts/verdict.jq"
```

`send-next.sh MODEL` accepts `--project` / `--agent-role` or the environment
variables `SC_PROJECT` / `DECIDR_AGENT_ROLE`; explicit flags override the
environment. Empty input and an early leaf make zero calls, including a
final JSON line without a trailing newline. A request requires all three
values. The guard is necessary: bare `decidr send` on an empty stream would
produce a parse error. Keep `pipefail` so downstream empty streams cannot
hide a failed call. jq may exit 5 even though decidr's failure exit was 1.

Both jq stages check `ok:false`. Stop on configuration, credential or
provider errors; do not convert them into failed answers or automatically
retry them. A failed Haiku call is not a model comparison. Preserve the raw
result lines; report commands, stdout/stderr and exit codes. Use only text
authorized for the provider. Helpers write supplied
run files; decidr sends text remotely and writes its own session logs.
