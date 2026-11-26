# Walk this repository's records with decidr and jq

One request per REQ/NFR MUST or MUST NOT statement, or per ADR, asks three
gate questions. An unacceptable choice or confidence below 0.8 asks
`which_part`; otherwise the walk ends with `yes`. `review` means follow-up,
not a judge-jev quality failure.

[report.html](report.html) shows D2 diagrams and selectable results;
[recorded.json](recorded.json) contains the captured requests and responses
with execution locations replaced by placeholders.
The site publishes both examples in place and links them from the [diagrams index](https://randlee.github.io/judge-jev/diagrams/index.html).

## Replay

Requires Python 3, D2 and sc-compose on PATH. Use a new output directory:

```bash
python3 --version
d2 --version
sc-compose --version
python3 site/examples/decidr-pipeline/run.py --output /tmp/decidr-replay
open /tmp/decidr-replay/report.html
```

Replay renders saved results without decision calls. Install D2 with
`brew install d2` on macOS; see [sc-compose](https://github.com/randlee/sc-compose)
for its CLI installation.

## Run live

Also requires decidr, jq, Bash and a TypeSafe key. Use Raptor's
`integration/judge-jev` branch at `8ce2be8363318be2f7c2e2b79d1f646399cab2fd`,
not develop; the owner's checkout is `~/github/raptor-worktrees/integration-judge-jev`.

```bash
command -v decidr && decidr --version
command -v jq && jq --version
export RAPTOR=/path/to/raptor-integration-judge-jev
python3 site/examples/decidr-pipeline/run.py --live --raptor "$RAPTOR" \
  --first-model jev --second-model jev --bar 0.8 \
  --output /tmp/decidr-live
```

The default sample is REQ-JEV-0001 (three statements), ADR-JEV-0001 (one
record), and NFR-JEV-0001 (four statements). Repeat `--record ID` to select
others. Replace `--raptor` with `--index /path/to/index.json` for an existing
Raptor export. A selected record with import diagnostics is refused.

The [runner](../../../scripts/decision_examples.py) executes
`decidr send | jq | guarded decidr send | jq`. REQ/NFR diagnostic choices are
phrases between stopwords, with backticked names kept whole; ADR choices are
section names. The guard accepts
`--project` / `--agent-role` or `SC_PROJECT` / `DECIDR_AGENT_ROLE`.
For Haiku in stage one, pass `--first-model haiku` and supply its credential.

## Diagram modes

Output includes tree JSON, D2 source, SVG and Mermaid under `diagrams/`,
plus `run.json`, `report.html` and `report.md`. The HTML is composed from
[the XHTML template](../../../templates/decision-report/report.xhtml.j2).

```bash
python3 scripts/render_tree_graph.py \
  --tree plugins/sc-judge-jev/install/templates/skills/judge-jev/assets/questions/quality-req.json \
  --format mmd --output /tmp/quality-req.mmd
```

Use `--format md` for a Markdown Mermaid fence or `--format d2` for D2 source.
Add `--result /path/to/view.json` to highlight a recorded view's path.
