# Run judge-jev quality on this repository's records

This example runs the installed `judge-jev quality` implementation against
`REQ-JEV-0001`, `ADR-JEV-0001`, and `NFR-JEV-0001`. It renders the **shipped
quality trees**, including later waves that this particular run did not visit,
and highlights the paths recorded by quality. REQ/NFR waves ask each MUST /
MUST NOT statement; ADR waves ask the whole record. Diagnostic questions are
shown but never gate the quality verdict.

Review [report.html](report.html) for D2 diagrams and all question results.
The runner also generates `report.md` with embedded Mermaid. The actual
quality command, stdout, stderr, and result envelopes (with portable execution
path placeholders) are in
[recorded.json](recorded.json). Its three recorded verdicts are `yes`.
Confidence is displayed; the shipped tree's choice rules determine verdicts.

## Replay without provider calls

Requires Python 3, D2 and sc-compose. Check installation as described in the
[first example](../decidr-pipeline/README.md).

```bash
python3 site/examples/judge-jev-quality/run.py --output /tmp/quality-replay
open /tmp/quality-replay/report.html /tmp/quality-replay/report.md
```

Choose a new output directory for each run. This replays the recorded result
through the same D2 and sc-compose XHTML renderer used by the live run.

## Run live

Use only randlee/raptor's `integration/judge-jev` branch, pinned at
`8ce2be8363318be2f7c2e2b79d1f646399cab2fd`; the owner's local checkout is
`~/github/raptor-worktrees/integration-judge-jev`. Do not use Raptor develop.

Use a trusted installed copy of `jev_judge.py` (the implementation of
`judge-jev quality`). The example never edits the judge-jev skill or
`jev_gate.py` in this checkout. To create an isolated installation for this
example:

```bash
install_dir=$(mktemp -d)
uv run --python 3.11 --script plugins/sc-judge-jev/install.py \
  --dest "$install_dir" --target claude --allow-remote-judge
judge_script="$install_dir/.claude/skills/judge-jev/scripts/jev_judge.py"
```

The live request sends this repository's record text to Jev. Use the
repository's committed remote-judge setting and your existing TypeSafe
credential. The example does not print keys or change that setting.

```bash
export RAPTOR=/path/to/raptor-integration-judge-jev
python3 site/examples/judge-jev-quality/run.py --live --raptor "$RAPTOR" \
  --judge "$judge_script" --output /tmp/quality-live
```

To use an existing Raptor export, pass `--index /path/to/index.json` instead
of `--raptor`. Select other records with repeated `--record ID`.
The actual quality invocation uses the standard installed-script form:

```bash
SC_PROJECT=decidr-question-tree uv run --python 3.11 --script "$judge_script" quality \
  --index /path/to/index.json --repository-root . --run-name quality-example-live \
  --req REQ-JEV-0001 --adr ADR-JEV-0001 --nfr NFR-JEV-0001
```

Raptor's export in the recorded run reported one diagnostic on the unselected
`REQ-JEV-0003`. Selected records with diagnostics are refused before calls.
The runner preserves quality's raw output and uses the tree's first matching
rule over the recorded answers to mark the path. It does not add the first
example's confidence bar to quality.

Both examples share [the renderer](../../../scripts/render_decision_report.py)
and [sc-compose XHTML template](../../../templates/decision-report/report.xhtml.j2).
Every output contains `run.json`, D2/SVG/Mermaid diagrams, `report.html`, and
`report.md`. The diagram CLI supports `--format mmd`, `md`, or `d2`:

```bash
python3 scripts/gen_tree_diagrams.py \
  --tree plugins/sc-judge-jev/install/templates/skills/judge-jev/assets/questions/quality-adr.json \
  --format md --output /tmp/quality-adr.md
```
