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
response envelopes, commands, and outcomes from the live run. No fixture is
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

The complete executable shell pipeline is `PIPELINE` in
[scripts/decision_examples.py](../../../scripts/decision_examples.py). It calls
`decidr send | jq | guarded decidr send | jq`, records every boundary, and
stops on an error. REQ/NFR choices are split into literal terms by the skill's
Python script. ADR diagnostics use actual section names. A model is selected
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
