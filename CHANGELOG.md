# Changelog

`VERSION` is the single source of truth: every version in shipped metadata (plugin and marketplace manifests, `SKILL.md`, each reference, each agent, each registry) equals it exactly. A PR that changes shipped content raises `VERSION`, moves every version with it, and adds a `## X.Y.Z — date` section here. `scripts/check_version_sync.py` and `tests/sc-judge-jev/test_version_ssot.py` enforce it (see CONTRIBUTING.md).

## 0.2.1 — 2026-11-08

- Every JSON input is parsed into a strict pydantic v2 model (ADR-JEV-0005;
  `pydantic>=2.7,<3` joins the script's inline dependencies and CI): the quality
  tree (tree, wave, leaf, choice question, `next` and `verdict_rules` rules),
  the question set, the answers file and Jev's answers (choice and noul), the
  Raptor import index (records stay open) and the batch request line (the
  `jev-batch-request` wire contract is unchanged). The hand-written checks are
  gone; every refusal keeps its code (`QUALITY.TREE`, `INPUT.MALFORMED`,
  `VALIDATION.INPUT`, `QUESTIONS.ROLES`, `JEV.RESPONSE_INVALID`, `RECORD.*`) and
  names pydantic's field path and rule, e.g.
  `nodes.wave-1.questions.context.criteria: Dictionary should have at least 2
  items`. `strict_loads` still parses first (NaN and Infinity, integers over
  4300 digits, deep nesting and lone surrogates are `INPUT.MALFORMED`).
  Stricter than before: a tree, question or rule with an unknown field, a
  `version`, `approved` or `note` of the wrong type, or a Raptor record without
  a string `id`; an anchor `kind` outside the schema's enum is refused.
- New `validate` command (REQ-JEV-0210): exactly one of `--tree`, `--questions`,
  `--answers`, `--index` or `--requests <file>` (`-` is stdin) runs the model
  and checks the other commands apply before their first Jev request. It never
  calls Jev, needs no API key and writes no log. It prints the kind, path and
  sha256 of an accepted file, or the typed error with the field path.
  `--requests` also takes `--gate` and `--max-request-bytes`, as `batch` does.
- Invalid UTF-8 (or a closed stream) on stdin is `INPUT.MALFORMED` for every
  command that reads stdin; it was `SCRIPT.INTERNAL`.
- A request whose log events the sc-observability logger would refuse is
  `JEV.CONTEXT_EXCEEDED` before any call, in `--dry-run` too (REQ-JEV-0211). The
  request event, the largest answer event (every option with a probability), the
  result event and, for `quality`, the statement, wave and verdict events are
  each measured as the logger measures them (typed fields, compact JSON, 65536
  bytes) and the message names the event and its size. A valid tree whose
  request fitted `--max-request-bytes` was refused after Jev had answered.
- No input crashes `jev_judge.py`. Every JSON input (tree, question set, index,
  answers file, request stream, Jev's response) is refused as `INPUT.MALFORMED`
  (or `JEV.RESPONSE_INVALID`) when it holds NaN or Infinity, an integer over
  4300 digits, nesting too deep to parse, or a lone surrogate escape. A leaf
  with `next`, `verdict_rules`, `per`, `statements` or `modals` is
  `QUALITY.TREE`. An answer whose `choice` is not a string is
  `JEV.RESPONSE_INVALID`, and the noul rule is one rule for validation and
  reading. A non-UTF-8 argument is `VALIDATION.INPUT`. Output is JSON even when
  a value holds a lone surrogate.
- The run log must be writable before any call (`LOG.WRITE` otherwise). A run
  whose log did not grow is `LOG.WRITE`, and that error still carries the
  results.
- `quality` checks the whole tree before any call (and in `--dry-run`): each
  question is a `choice` question with instructions and 2 to 255 criteria; each
  rule's choices are options of their question; each wave's last rule has no
  condition; no cycle through `next`; every later wave's statements and size.
  A tree that crashed the script (`start` a list, a question not an object) or
  failed only after paid calls is now `QUALITY.TREE` naming the wave, question or
  rule.
- `quality` refuses, with `QUALITY.TREE` before any call: a `verdict_rules`
  entry that is not an object, `modals` given as a string (it could match by
  substring), and a `--questions` tree whose `kind` differs from the record's.
- `quality`: every wave reports its reason, each question's `id`, `text`,
  Jev's `choice` and `confidence`, in `data.results[].waves[].reason` and the
  `wave` log event (REQ-JEV-0101). A wave may end the walk with
  `verdict_rules` in the tree (`{any: {question: choice}, verdict}`, first
  match wins) instead of `next`; leaves still work. The leaf's fixed
  `reason` text is no longer reported.
- Per-statement waves: a tree node with `"per": "statement"` sends one
  request per statement of the record (`statements` names the record field,
  `modals` the modals judged), item `<record>.s<index>` whose text is
  `{statement, record}`. Its reason lists each statement (index, modal,
  text) with every question's answer; its rules fire when any one statement
  matches, and `matched_statements` names the statements that fired it. A
  statement without an answer is named in the error. `--dry-run` shows every
  statement's wave-1 request. A record with no judged statement is
  `RECORD.STATEMENTS`.
- `verdict_rules` take `all` beside `any`, and a listed choice may be a list
  of choices. Every reason entry carries the chosen option's `criterion`,
  which holds its fix hint.
- The shipped trees hold wave 1 only (`approved: false`, draft pending Rand
  approval). REQ and NFR ask per MUST / MUST NOT statement: `obligations`,
  `joined_by`, `term`, `check`; `no` when a statement has 2+ obligations
  joined by an and-list, alternatives or a rationale, an undefined or vague
  term, or a check that needs a measure or none. ADR asks per record:
  `context`, `alternatives`, `consequences`; `no` on any option with a fix.
- `quality` takes repeated, mixed `--req/--adr/--nfr` ids and judges them all
  under one run name; output is `data.results`, one entry per record.
- The `quality` log is `.sc/judge-jev/logs/judge-jev.log.jsonl` (default
  `--run-dir` is now `.sc/judge-jev`; it was `.sc/judge-jev/logs`, which put
  the file under `logs/logs/`).

## 0.2.0 — 2026-11-08

- `jev_judge.py batch` logs through the sc-observability logger
  (`sc-observability==1.5.0`, REQ-JEV-0008) instead of its own
  `anchor-runs/tournament-<run>.jsonl`: each result line is a `request`,
  `answer` and `result` event in `<run-dir>/logs/judge-jev.log.jsonl`. Stdout is
  unchanged. The script carries PEP 723 metadata (`uv run --script`) and needs
  Python 3.11 or newer; a missing package is `DEPENDENCY.SC_OBSERVABILITY`, a refused
  event `LOG.WRITE`.
- `jev_judge.py quality --req|--adr|--nfr <id> --index <raptor index>
  [--questions <file>] [--dry-run]` (REQ-JEV-0101, REQ-JEV-0209): judges one
  record from a Raptor import index with its kind's decision tree,
  `assets/questions/quality-{req,adr,nfr}.json` (drafts, `approved: false`), one
  batch request per wave; answers pick the next wave, a leaf gives the verdict
  and the path. Records with import diagnostics are refused. Every result and
  log event carries the tree id and the file's sha256.
- `batch` accepts a request line without `anchor`: it sends only the item,
  needs no roles and gets a null verdict. Anchored lines are gated as before.

## 0.1.0 — 2026-11-07

- The judge-jev marketplace: `.claude-plugin/`, `.cursor-plugin/` and
  `.agents/plugins/` catalogs list one plugin, `sc-judge-jev`, which ships only
  the `judge-jev-installer` skill and a SessionStart hook.
- `install.py` installs the `judge-jev` skill into a repository or a parent
  folder (`.claude/`, `.codex/`, `.cursor/`), with the install lock
  `.sc/judge-jev/install-lock.json`, sha256 ownership, `--overwrite` backups,
  `--dry-run`, `--status`, `--allow-remote-judge` / `--no-remote-judge`, and
  `target_reasons` / `missing_targets`. Global destinations are refused with
  `INSTALL.DEST_GLOBAL`.
- `judge_jev_settings.py` reads and sets `.sc/judge-jev/settings.yaml`
  (`schema_version`, `allow_remote_judge`).
