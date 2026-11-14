# Initial released-wheel integration evidence

This is real installed-skill execution on published **sc-decidr 0.1.0**,
Python **3.11**, consumer source
`168f6f1c661c2fd6fb03724f8f270a48637ef562`. The actual responding model was
**jev-1.14.0**. The installed script matches that source's strict template
render plus the installer's final newline; its SHA-256 is in
[provenance.json](provenance.json). No local or git wheel was used.

The reviewed source `460489393d6de65d0a0d02e13256a109fdb033b8` has identical
rendered `jev_judge.py`, `jev_errors.py`, batch-request schema and batch-result
schema bytes. `runtime_artifact_hashes` in provenance records three independently
computed SHA-256 values per file: installed evidence bytes, the original tested
source render, and the reviewed source render. Each triple matches the retained
installer lock, including the original recorded entrypoint digest. Rendering
uses package version 0.3.0 and the installer's final-newline rule; schemas are
copied unchanged. The original tested source is retained above, and this
identity update changes no runtime file or recorded live output.

Dev-sanity and QA consume this evidence for bjj-1 deliverable 4. It replaces
the temporary-only evidence that sanity could not review at the commit.
This committed copy can be removed once agt-r17 commits equivalent final B-1
published-wheel verification; the original run files remain retained. It is not a new release gate or a record-quality acceptance.

- [batch-input.jsonl](batch-input.jsonl) and [batch-results.jsonl](batch-results.jsonl):
  three real requests, three successful result lines, original item order retained.
- [quality-results.json](quality-results.json): representative REQ-JEV-0003 and
  ADR-JEV-0007 evaluation, verdicts **no** and **yes**. Those are observed model
  judgments, not claims that the records meet a three-run acceptance gate.
- [batch-log-query.json](batch-log-query.json) and
  [quality-log-query.json](quality-log-query.json): events read back through
  sc-observability 1.5.0 `Logger.query`, normalized by the existing test helper's
  typed-value conversion. Each run has three request, answer and result events.
  Quality also has two statement, wave and verdict events of each kind.
- [native-session-readback.json](native-session-readback.json): identity/correlation
  projection read from the real wheel's retained default session JSONL. Its final
  six rows (13:22:29–13:22:30 UTC) match all three batch and three quality raw
  responses in the query artifacts above. Each row has the expected repo,
  project and agent role, a canonical ULID session ID equal to its correlation
  ID, and matching answer/digest keys. Canonical response hashes match in both
  artifacts. One response also occurs in an earlier run; the recorded final-run
  window selects the matching row alongside the other five unique responses.
  Original row/whole-snapshot hashes and line numbers allow a local verifier to
  check the retained source. Payloads stay in the local native file.
- [real-wheel-offline-refusal.json](real-wheel-offline-refusal.json): published
  0.1.0 `send_batch` rejected malformed request JSON with native
  `decision.request_parse` before context/logger/credential setup. This new
  offline case used an explicit dummy ENV backstop; it sent nothing and read no
  keychain. The session readback above used existing live-run files.
- [dependency-tree.txt](dependency-tree.txt): the installed script's resolved
  dependency tree, including sc-decidr 0.1.0 and sc-observability 1.5.0.

Both live commands exited 0. The Raptor import read four source files and
imported 33 records with zero issues. Requests and complete answers are also
preserved in the queried events; credentials and raw transport diagnostics
are not included.

## Reproduce

The paths below are the actual paths used. `J` is the installed skill, not
the repository template. The owner consent is the existing committed setting
at f93ee5b; the scratch install has remote judging disabled and each command
explicitly selects the consented consumer repository.

```sh
REPO=/Users/randlee/github/judge-jev-worktrees/sprint/bjj-1-judge-jev
J=/tmp/sai-bjj-installed/.codex/skills/judge-jev/scripts/jev_judge.py
RAPTOR=/Users/randlee/github/raptor-worktrees/integration/judge-jev
cd "$REPO"
mkdir -p /tmp/sai-bjj-installed
uv run --no-project --python 3.11 --with pyyaml --with 'sc-compose>=1.7.0,<2' \
  python plugins/sc-judge-jev/install.py --dest /tmp/sai-bjj-installed \
  --target codex --no-remote-judge --overwrite
"$RAPTOR/.venv/bin/python" "$RAPTOR/scripts/extract.py" \
  --project-root . --output /tmp/sai-bjj-index.json
uv tree --python 3.11 --script "$J"
uv run --python 3.11 --script "$J" batch \
  --input plugins/sc-judge-jev/evidence/bjj-1-sc-decidr-0.1.0/batch-input.jsonl \
  --run-dir /tmp/sai-bjj-py311-batch --run-name bjj-stable-010-py311-batch \
  --repository-root "$REPO"
uv run --python 3.11 --script "$J" quality --adr ADR-JEV-0007 --req REQ-JEV-0003 \
  --index /tmp/sai-bjj-index.json --run-dir /tmp/sai-bjj-py311-quality \
  --run-name bjj-stable-010-py311-quality --repository-root "$REPO"
```

The original batch input path was `/tmp/sai-bjj-live-input.jsonl`; the
committed copy above is byte-identical. For log queries, open
`sc_observability.create_logger(LoggerConfig(service="judge-jev", log_root=...))`
for each run root, then call `Logger.query(LogQuery(service="judge-jev", limit=1000))`
and shut down the reader. The existing `tests/sc-judge-jev/jev_support.py`
`read_log` performs these steps and the typed-value conversion used here.
Re-running paid calls may yield different quality judgments.

## Still pending

Default native session identity/layout and persisted output are now read back
from the original real-wheel runs. This verifies default owned-log persistence;
it does not verify caller-owned injection/flush lifetime. Producer timeout
implementation `agt-b-1.8` is closed; publication `agt-2t0` and final pin/rechecks
`agt-r17` remain open. The installed API reference retains the parsed `--timeout`
option and explicitly says 0.1.0 does not forward it.

Native direct Logger injection/flushing, per-call timeout forwarding, the
final B-1 wheel pin and credential/retry rechecks remain pending the B-1
prerelease **agt-2t0**, owned by **agt-r17**. They were not exercised by these
successful default-logging runs and are not reported as passed. The lead's
initial consumer-exit ruling is 01M7D28SQ615B60CV4AA83XKG9.

The native session source is
`~/.sc-agent/logs/github.com/randlee/judge-jev/judge-jev/judge-jev/sessions.jsonl`.
For a readback, parse its JSONL, select the recorded six row timestamps, check
`service=sc-agent-session`, `target=sc_agent.session`, `action=session.row`,
`fields.session_id == correlation_id`, the identity fields and the response
hashes against the committed consumer answer events. JSON hashing uses the
encoding declared in the readback artifact. No service or credential lookup
is needed. New credentialed runs require lead approval and owner attendance.
