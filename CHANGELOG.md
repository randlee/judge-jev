# Changelog

`VERSION` is the single source of truth: every version in shipped metadata (plugin and marketplace manifests, `SKILL.md`, each reference, each agent, each registry) equals it exactly. A PR that changes shipped content raises `VERSION`, moves every version with it, and adds a `## X.Y.Z — date` section here. `scripts/check_version_sync.py` and `tests/sc-judge-jev/test_version_ssot.py` enforce it (see CONTRIBUTING.md).

## 0.3.0 — 2026-11-08

- The shipped quality trees (`quality-adr`, `quality-req`, `quality-nfr`, JSON
  and `quality-adr.ttl`) carry `approved: true`: Rand Lee approved the wave-1
  wording on 2026-11-08.
- `quality-req.ttl` and `quality-nfr.ttl` join `quality-adr.ttl`: the same
  trees as the JSON files (kept), wording byte-identical, validated by the
  SHACL shapes and compiled back to the same JSON in tests.
- `quality --questions <file>` and `validate --tree <file>` accept a `.ttl`
  tree as well as `.json` (by extension): it is loaded and SHACL-checked by
  `jev_graph`, so a refusal is `QUALITY.TREE` (with the violations) or
  `INPUT.MALFORMED` as before; the tree digest is that of the file's bytes.

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
  4300 digits, containers nested deeper than `JSON_MAX_DEPTH` (500) and lone
  surrogates are `INPUT.MALFORMED`; the depth limit is explicit because Python
  3.14's parser accepts any depth where 3.11-3.13 raise `RecursionError`).
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
- Quality trees can be written in Turtle (ADR-JEV-0006): `assets/ontology/judge-jev.ttl`
  (the `jj:` vocabulary), `assets/shapes/quality-tree.shacl.ttl` (SHACL shapes for
  the graph and its edges: one start that is a node, a wave's questions and
  same-kind rules, 2 to 255 options with a label and criterion, choices that are
  options of their question and asked by the same wave, `goto` inside the tree,
  integer unique ranks, an unconditional last rule, a leaf with only a verdict,
  no cycle through `goto`) and `assets/questions/quality-adr.ttl`, the shipped ADR
  tree with the same content as `quality-adr.json`, its questions IRIs any tree
  can ask.
- `scripts/jev_graph.py` is the tree side of the graph store port:
  `load_tree`, `validate_tree` (SHACL, refused as `QUALITY.TREE` with each
  violation's focus node, path and shape), `tree_to_quality_json`,
  `compile_wave` and `tree_digest` (SHA-256 of the RDFC-1.0 canonical N-Quads).
  It needs `pyoxigraph>=0.5,<0.6` and `pyshacl>=0.30,<1`.
- The tree graph layer refuses every bad input with a typed error (qa16). The
  shapes are closed (`sh:closed` on every `jj:` node shape, `rdf:type` the only
  ignored property; tree, wave, leaf, question, option and rule nodes must be IRIs)
  and two rules say every subject is one of the shaped classes and every `rdf:type`
  object is one of them (conditions chained through their type triples validated and
  took 77 s to digest at 1800 links), so a blank node can
  only be a condition: a 20000-deep blank-node chain riding beside a valid tree
  segfaulted `tree_digest`, and is now `QUALITY.TREE`. A tree file over
  `MAX_TREE_BYTES` (128 KiB) is `QUALITY.TREE` before it is parsed (a 900 KiB wave
  took 155 s to check). `tree_digest` returns a `Result` and validates first;
  `tree_to_quality_json` and `compile_wave` validate first and raise `TreeInvalid`.
- `jj:kind`, `jj:per` and `jj:modal` must be plain strings, so mixed `jj:modal`
  values are refused by the shapes instead of crashing `sorted()`.
- Run triples use the tree graph's own IRIs for the tree, nodes, questions,
  options and rules (`jev_graph.iri_index`), not names minted from the JSON, so
  `TRACE_QUERY` finds rows for any valid tree, and two labels with one slug
  ("A/B", "a b") stay two options. A JSON dict tree still mints the shipped names.
- `OxigraphGraphStore.compile_wave` returns a `Result` (`VALIDATION.INPUT` for an
  unknown wave); `query` answers SELECT only and refuses ASK, CONSTRUCT, DESCRIBE,
  updates and a non-string as `VALIDATION.INPUT`; `record_run` refuses non-quads.
- `rebuild_from_log` returns `LOG.READ` when the log does not match the tree (an
  unknown node, question or option) or a log line lacks a field, instead of a `KeyError`.
- SHACL violation text and order are the same on every run: a blank node is shown
  by where it hangs in the graph, never by its label. What rdflib logs or warns
  about an ill-typed literal is kept in the error (`data["log"]`) and no longer
  printed to stderr. `load_tree(None)` and other non-path arguments are `INPUT.MISSING`.
- An answers-file `{"__error__": ""}` is `INPUT.MALFORMED` at load (the code is 1
  to 64 characters). `batch` and `quality` check that the answers file has an
  entry (or a `*`) for every request they are about to send, and refuse with
  `FIXTURE.MISSING` and nothing sent: `batch` checks the whole stream, `quality`
  each wave before it is sent. A noul answer with a probability over 1 is
  `JEV.RESPONSE_INVALID` after the send (test restored).
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
- ADR-JEV-0007 seam: `jev_ports.py` holds the `Transport` port (only the batch request and
  result JSON crosses it; `PythonCoreTransport` over `pump_batch`, `FixtureTransport` for
  tests) and the `GraphStore` port (`OxigraphGraphStore` over `pyoxigraph` and `jev_graph`).
- ADR-JEV-0006 run side: `jev_runs.py` projects a quality run onto the `jj:Run`, `jj:WaveRun`,
  `jj:Answer` and `jj:OptionProbability` triples with deterministic IRIs (`run_triples`),
  rebuilds the same triples from the sc-observability log alone (`rebuild_from_log`), and
  carries `TRACE_QUERY`, which walks a verdict to its fired rule, each answer, its question
  and the chosen option's label and criterion.
- `redact_sensitive` no longer recurses: a container nested 600 deep raised
  `RecursionError` (`SCRIPT.INTERNAL`) from `validate --requests` and
  `batch --dry-run` (through the log-event size check), and `emit` printed a
  traceback and no JSON for a `RECORD.DIAGNOSTICS` issue with a deeply nested
  field. It is now iterative, and `emit` marks nesting deeper than 100 levels
  with `<truncated: nested deeper than 100 levels>` so it always prints JSON.
  The oversized request is `VALIDATION.INPUT` (the logger's depth limit of 32).
- The log-size check models the worst attempt message at its escaped size: 500
  astral characters (12 bytes each as ASCII-escaped JSON), not 500 `x`. A
  batch that passed the check and then failed with `LOG.WRITE` after a Jev
  request (an answers list of an invalid astral choice, then a valid answer)
  is now `JEV.CONTEXT_EXCEEDED` with nothing sent. Per-statement waves carry
  the same message and are covered.
- An answers-file `{"__error__": code}` code is at most 64 characters; the code
  was logged unclipped, so `{"*": {"__error__": "J" * 70000}}` was refused only
  after the send.
- One answers-file envelope, checked before the first request by `quality`,
  `batch` and `validate --answers`: an object of string keys, each an object or
  a non-empty list of objects; an `__error__` object holds only a string code
  within the bound. `{"*": {"__error__": 5}}` and `{"*": ["x"]}` are
  `INPUT.MALFORMED` at load for every command. An answer's own body stays
  Jev's response stand-in, checked after the send (`JEV.RESPONSE_INVALID`), so
  `validate --answers` no longer refuses a bad choice, probability or extra key
  inside an answer (it did, and `quality` did not agree).

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
