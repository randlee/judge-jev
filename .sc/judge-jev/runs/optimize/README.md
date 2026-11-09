# Record optimization loop: judge-jev REQ/NFR records

This is an iterative tuning of the 24 REQ records and 1 NFR record against
the `quality-req` and `quality-nfr` wave-1 trees, with live Jev throughout.

- **Code:** the skill rendered from 482d79a (0.3.0, before `rule_rank` and
  `record_iri`), at `dogfood-0.3.0/skill`.
- **Records:** the starting text is `docs/record-fixes` (d3f07f0), as
  `orig`, plus the first greedy definitions pass (11d672a), as `greedy`.
  The final text is judge-jev branch `docs/record-terms`: 887fca2 from the
  loop, then 53c1541 from the author review.

## Score per record

1. The number of failing statements: rule 1 or rule 2 fired.
2. The mean margin on the deciding answers.

An improvement counted only if it held when re-measured.

## Files

- `optimize-runs.tar.zst`: every run, 902 Jev runs and about 700 MB
  uncompressed. For each run it holds the stdout JSON, stderr, exit code and
  `runs/<run>/logs/judge-jev.log.jsonl`. Extract with
  `zstd -dc optimize-runs.tar.zst | tar -xf -`.
- `runs-index.jsonl`: one line per (run, record) with the stage, iteration,
  fails, margin, verdict and fired rules. Its paths point into the archive.
- `tweaks-index.jsonl`: one line per proposed tweak with the record,
  iteration, proposer model, text, measured score, and kept or dropped.
- `records/<id>.md`: per record, the original text, the final text, the
  diff, the scores and the kept tweaks.
- `records-summary.json`: per record, the original, greedy and final scores
  `[fails, margin, fail-runs]`, plus the definitions pruned.
- `final-decision.json`: per record, whether "fixes-only" or "pruned" won,
  with its fail runs and margins.
- `noise.json`: repeat-measurement noise.
- `iter1`..`iter4/`: the proposals and evaluations per iteration.
- `proposer-brief*.md`: the brief each proposer got.
- `scripts/`: the drivers.
- `author-check/`: two live runs of REQ-JEV-0205, 0206, 0207, 0210 and 0212
  after the author review. Five dropped passages were restored there: all
  five records give `yes` in both runs.

All 25 records end with 0 failing statements. REQ-JEV-0204, 0208 and 0210
each failed one of the repeated final measurements, which is Jev noise on
low-confidence answers.
