# judge-jev 0.3.0 run logs

Real runs against live Jev, byte copies of what the tool wrote. Nothing here is edited.
Rendered skill: `sc-compose render --strict --var version=0.3.0` of every `*.py.j2` and `*.md.j2`, plus `assets/`.

## Folders

| Folder / file | Code commit | Notes |
|---|---|---|
| `earlier-482d79a/` | 482d79a (feat: definitions, compare-definition and doctor) | 0.3.0 code before the rule_rank and record_iri layer. Its events carry neither `rule_rank` nor `record_iri`. |
| `quality-adr*`, `quality-nfr*`, `quality-req*` | 2512943 (fix/windows-ttl-digest, top of stack) | `quality` on every ADR, NFR and REQ of this branch's `docs/`. Includes rule_rank and record_iri. |
| `compare-1..3` | 2512943 | `compare-definition` runs; definitions in `../definitions.ttl`. 1: REQ-JEV-0202 + `jev`; 2: NFR-JEV-0001 + `jev`; 3: REQ-JEV-0203 + `target-mode` and `raptor` together. |
| `doctor.*` | 2512943 | `doctor --index .sc/judge-jev/runs/index.json --repository-root <worktree>`. |
| `<run-dir>/logs/judge-jev.log.jsonl` | 2512943 | The tool's log of each run, written under its `--run-dir`. |

## Commands

2512943 runs, from the worktree root (`jjpy` is the Python used; compare: `compare-definition --req|--nfr <id> --index ... --definition <iri>... --run-dir .sc/judge-jev/runs/compare-<n> --run-name compare-<n>-0.3.0`):

    PYTHONDONTWRITEBYTECODE=1 jjpy <rendered skill>/scripts/jev_judge.py quality --<kind> <id>... \
        --index .sc/judge-jev/runs/index.json --run-dir .sc/judge-jev/runs/quality-<kind> \
        --run-name quality-<kind>-0.3.0 --repository-root <worktree> > quality-<kind>.json 2> quality-<kind>.stderr.txt

The index is `extract.py --project-root <worktree> --output .sc/judge-jev/runs/index.json` (Raptor, 33 records, 0 diagnostics).
`.sc/judge-jev/settings.yaml` sets `allow_remote_judge: true`.

`earlier-482d79a/`: same `quality` command with run names `dogfood-<kind>-<n>`, `dogfood-r2-...`, `dogfood-r3-...`; see each `runs/` and the `.json` / `.stderr.txt` / `.exit` files. The scripts that drove them (`run-kind.sh`, `round3/apply_defs.py`) are copied alongside.

## Record text revision

- 2512943 runs: the `docs/` records as committed at 2512943.
- `earlier-482d79a/` top level: the `docs/` records at 482d79a. `round2/` ran after record fixes and `round3/` after a Definitions paragraph was inserted into records (`round3/apply_defs.py`), on scratch copies of `docs/` (the `repo/` copies are not included).

## Predates rule_rank and record_iri

`earlier-482d79a/` ran before events carried `rule_rank` and `record_iri`. Do not look for them there.
