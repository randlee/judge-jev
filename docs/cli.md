# judge-jev CLI

Draft. Two primitive commands each compose single Jev requests; the profile
run calls the second primitive once per pair and aggregates the results.
Every command takes `--dry-run`.

## `judge-jev quality`

```
judge-jev quality (--req|--adr|--nfr <id>)... [--questions <file>] [--definitions <file>]... [--dry-run]
```

Judges whether each named record is well written (REQ-JEV-0101,
REQ-JEV-0209). `--req`, `--adr` and `--nfr` repeat and mix; one invocation
judges every named record under one run name.

- Input: the record text from Raptor. Only records Raptor imported without
  diagnostics are judged; every record is checked before the first request.
- Runs the record kind's quality decision tree, in waves. Each wave is one
  request: record text + that wave's questions. Every wave reports its
  reason: each question's id, text, Jev's choice, the chosen option's
  criterion (which carries its fix hint) and confidence. A wave's
  answers select the next wave, which refines them; a wave with no next
  wave ends the walk, and a rule in the tree (`verdict_rules`) turns its
  answers into the verdict.
- The shipped trees hold wave 1 only. A wave 2 is designed from wave 1's
  observed live answers.
- The tree ships with the tool; answers pick the branch and the verdict, no
  model chooses questions.
- Output: per record, the verdict, the path through the tree and every
  wave's reason.
- A per-statement wave (`"per": "statement"` in the tree) sends one request
  per MUST / MUST NOT statement: the statement plus the whole record as
  context, with all the wave's questions. The tree names the record field
  holding the statements (`statements`) and the modals judged (`modals`).
  Its reason lists each statement's index and text with every question's
  answer; a rule fires when any one statement matches it, and
  `matched_statements` names the statements that fired it. A statement that
  gets no answer is named in the error.
- `verdict_rules` match on `any` (one listed question got its choice) and
  `all` (every listed question did); a choice may be a list of choices.
- `--dry-run` reports each record's tree and composed wave-1 request, one
  per statement for a per-statement wave; later waves depend on live
  answers.
- A live run logs every wave as output: composed request, answers, reason,
  selected branch or verdict. A per-statement wave logs each statement's
  request and a `statement` event (statement, answers, reason), then a
  `wave` event with the request ids, matched statements and verdict. Logging goes through the sc-observability
  logger, the one sc-agent uses (REQ-JEV-0008), to
  `.sc/judge-jev/logs/judge-jev.log.jsonl`.

- `--definitions <file>` (repeatable) adds the definitions attached to each
  record to its requests (see Definitions); with no flag the repository's
  `.sc/judge-jev/` files are used. A record no definition reaches gets a
  request byte-identical to one without the feature.

Diagram: [diagrams/quality.md](diagrams/quality.md)

## `judge-jev check`

```
judge-jev check --req|--adr|--nfr <id> --location <loc> --mode prompt|skill|task|code
                [--vars <file>] [--questions <file>] [--dry-run]
```

Judges whether one location meets one record (REQ-JEV-0201).

- Request: record text + location text + the question set for
  (record kind × target class). Target class is agent text
  (`prompt`, `skill`, `task`) or code.
- `task` mode renders the template with sc-compose in strict mode from
  `--vars`, and sends two requests: raw template and rendered assignment
  (REQ-JEV-0203).
- Output: one verdict for the (record, location) pair (REQ-JEV-0206); two
  in `task` mode.

Diagram: [diagrams/check.md](diagrams/check.md)

## `judge-jev check --profile`

```
judge-jev check --profile <profile> [--questions <file>] [--dry-run]
```

Checks every pair the profile lists and aggregates the results
(REQ-JEV-0204).

- Runs `check` once per (record, location) pair, streamed as single
  requests (REQ-JEV-0202). Unlisted pairs are not judged.
- Output: every pair's verdict, aggregated:
  - per record: met at every listed location, or the failing locations;
  - per location: the records it meets and fails.

Diagram: [diagrams/check-profile.md](diagrams/check-profile.md)

## `judge-jev validate`

```
judge-jev validate --tree|--questions|--answers|--index|--requests <file>
```

Checks one input file with the model judge-jev applies to that input kind
before its first Jev request (REQ-JEV-0210, ADR-JEV-0005). `-` reads stdin.

- Kinds: `--tree` (quality tree), `--questions` (question set), `--answers`
  (answers file), `--index` (Raptor import index), `--requests` (batch
  request stream). Exactly one.
- `--requests` also takes `--gate` and `--max-request-bytes`, as `batch`
  does, so a stream is checked against the same set and size limit.
- `--tree` checks the tree alone; the checks that need a record (its
  statements, request size, log-event size) run in `quality`, before the
  first call and in `--dry-run`.
- `--answers` checks the envelope only, the same one `--answers-file` checks
  before the first request in `batch` and `quality`: an object of string keys,
  each an object or a non-empty list of objects; an `__error__` object holds a
  string code of at most 64 characters and nothing else (`INPUT.MALFORMED`
  otherwise). An answer's own body (its choice, probabilities, extra keys) is
  Jev's response stand-in and is checked after the send
  (`JEV.RESPONSE_INVALID`), so a test can feed an invalid answer on purpose.
- Never calls Jev, needs no key, writes no log.
- Output: one JSON object. Success names the kind, the path and the file's
  sha256.
- A refusal is the typed error (`QUALITY.TREE`, `INPUT.MALFORMED`,
  `VALIDATION.INPUT`, ...) naming the field path and the rule it breaks.

Diagram: [diagrams/validate.md](diagrams/validate.md)

## Definitions

ADR-JEV-0008, REQ-JEV-0212. A definition tells Jev what a term means for one
record, or for one place in it, without changing a question. It is data in the
request state: `state.definitions` is a list of `{term, text}` sorted by term.

A definitions file is Turtle (the closed shapes are
`assets/shapes/definitions.shacl.ttl`, the classes `jj:Definition` and
`jj:Attachment` are in the ontology):

```turtle
@prefix jj: <urn:judge-jev:ontology#> .
@prefix d:  <urn:judge-jev:definition:> .
@prefix a:  <urn:judge-jev:attachment:> .

d:fast a jj:Definition ; jj:term "fast" ; jj:text "Finishes within 5 s on the reference host." ;
    jj:source "docs/requirements/perf.md" ;
    jj:attachedTo a:fast-1 , a:fast-2 .
a:fast-1 a jj:Attachment ; jj:record <urn:raptor:repo:atm-core#REQ-ATM-0042> .
a:fast-2 a jj:Attachment ; jj:record <urn:raptor:repo:atm-core#REQ-ATM-0043> ;
    jj:location "docs/requirements/perf.md#Fast" .
```

- A definition has exactly one `jj:term` (one line, at most 128 characters),
  `jj:text` (at most 2000 characters) and `jj:source` (a path relative to the
  repository), and zero or more `jj:attachedTo` attachments. One with none is
  valid but unused: `doctor` warns.
- An attachment has exactly one IRI `jj:record` (the Raptor record IRI,
  `<repository URN>#<record id>`) and at most one `jj:location`.
- A record-only attachment puts the definition in every request about that
  record. A record-and-location attachment puts it only in a request made at
  that location (`compare-definition --location`); `quality` judges a whole
  record, so it carries record-only definitions.
- Files are `definitions.ttl` or `<name>.definitions.ttl` under
  `.sc/judge-jev/` (directly in that folder, not in a subfolder). They load as their own named graph: a tree's digest
  never changes because a definitions file exists. The same definition IRI
  in two files is `DEFINITIONS.INVALID` naming both.
- Definitions are never truncated. They count toward the 24000-byte request
  limit and the log-event size check, before any call
  (`JEV.CONTEXT_EXCEEDED`).
- Every request, answer, result, wave and verdict event, and each record's
  result, carries `definitions: [{iri, term, digest}]` (the digest is the
  SHA-256 of term, text and source); the run's triples link the run to each
  definition IRI with `jj:carriedDefinition`.
- A bad file is a typed error before the first request, never a traceback:
  `INPUT.MISSING`, `INPUT.MALFORMED` (not Turtle, not UTF-8), or
  `DEFINITIONS.INVALID` (oversize, a blank-node definition, a literal
  record, an attachment with two records, a term over its limit, an
  absolute or `..` path, any shape violation).

Locations use the forms in Locations below.

Diagram: [diagrams/definitions.md](diagrams/definitions.md)

## `judge-jev compare-definition`

```
judge-jev compare-definition (--req|--adr|--nfr <id>) --index <file> --definition <iri>...
    [--definitions <file>]... [--location <loc>] [--threshold <p>] [--questions <file>]
    [--dry-run | --answers-file <file>] [--run-dir <dir>] [--run-name <name>]
```

REQ-JEV-0213. Runs one record's walk twice, without and with the named
candidate definitions (one or more, compared together), and reports every
answer's choice and confidence on both sides. Each candidate must be
attached to the record (and to `--location` when it is attached with one);
a candidate that no request reaches is `DEFINITIONS.NOT_ATTACHED`, an unknown
IRI `DEFINITIONS.NOT_FOUND`. The record's other definitions are in both arms.

- The candidates are **material** when an answer's choice flips, or its
  confidence crosses the decision threshold (`--threshold`, default 0.6: a
  confidence at or above it decides). A move on the same side (0.90 to
  0.95) is not material. The threshold applied is in `data.threshold` and in
  the `compare` log event, so a ruling is reproducible.
- Output: `material`, `answers_compared`, `answers_material`, one `answers`
  entry per question (node, statement, question, both choices and
  confidences, `choice_changed`, `confidence_change`, `crosses_threshold`,
  `material`), and each arm's verdict, path, run name and definitions.
- Each arm is logged under its own run name, `<run>.without` and
  `<run>.with`; a `compare` event under `<run>` holds the summary.
- `--dry-run` shows both arms' composed requests and calls nothing.
- `--answers-file` keys tell the arms apart: `with/<record>/<node>` and
  `without/<record>/<node>` (and `with/*`, `without/*`) belong to one arm
  and win; unprefixed `<record>/<node>`, `<node>` and `*` serve both arms,
  so a fixture of only unprefixed keys gives identical answers and is never
  material. A live comparison needs the same key and `allow_remote_judge`
  as `quality`, checked before the first call.

Diagram: [diagrams/compare.md](diagrams/compare.md)

## `judge-jev drift`

```
judge-jev drift --old-index <file> --new-index <file> (--req|--adr|--nfr <id>... | --changed)
    [--form diff|full] [--controls <n>] [--threshold <p>]
    [--dry-run | --answers-file <file>] [--run-dir <dir>] [--run-name <name>]
```

Does a rewritten record still require exactly what the original required?
Reads both versions from two Raptor import indexes and sends one Jev request
per record: the original's normative text (REQ/NFR statement, statements and
success criteria; ADR decision) and, with `--form diff` (the default), a
unified diff to the rewrite; `--form full` sends both texts whole.

- Questions: one `keep_<n>` per obligation of the original (REQ/NFR
  statements; ADR numbered decision items or paragraphs), answered `same`,
  `narrowed`, `changed` or `dropped`; `added` (does the rewrite require
  anything new: obligation, condition, threshold, measure, limit or
  definition); and, for REQ/NFR, `verification` (were checks removed,
  weakened, strengthened or added).
- Verdict per record: `drift` when any answer is a drift choice at or above
  `--threshold` (default 0.6); `uncertain` when none is but an answer is
  below it; else `no-drift`. `findings` lists each such answer, with the
  obligation text for a keep question.
- `--changed` compares every record whose normative text differs; ids only
  in the old index are listed `deleted`, only in the new `added`, equal ones
  `unchanged`. A record with Raptor diagnostics is refused.
- Controls: for the first `--controls` records (default 3), the original
  against itself must be `no-drift` and the original with its first
  obligation removed must be `drift` on that obligation. A failed control or
  a failed request makes `valid` false: the verdicts are then not evidence.
- Answers-file keys: `<record>/drift`, `<record>.ctl-same/drift`,
  `<record>.ctl-drop-<n>/drift`, or `*`. A live run needs the key and
  `allow_remote_judge`, checked before the first call. Every request and
  answer is logged like `batch`; a `drift` event holds the summary.

## `judge-jev doctor`

```
judge-jev doctor [<path>...] [--index <raptor index>] [--repository-root <dir>]
```

REQ-JEV-0214, REQ-JEV-0215. Checks everything judge-jev loads in a
repository and calls nothing: no Jev, no key, no log, no file written.
The scope is the shipped trees and question sets, every tree and definitions
file at the top level of `<repository root>/.sc/judge-jev/` (its subfolders
are not searched), and each argument: a file, or a directory searched through
all its subfolders except `logs`, `anchor-runs`, `node_modules` and `.git`.

- **Errors** (exit 2; the report is `data`, each entry has `severity`,
  `code`, `file`, `message`): a schema or pydantic failure, a SHACL
  violation (an edge to nothing, a cycle, a closed shape), a definitions
  file that does not load, a definition IRI in two files, and
  `QUESTIONS.DUPLICATE_IRI` and `QUESTIONS.DUPLICATE_ID`.
- **Warnings** (exit 0): `DEFINITION.UNATTACHED`, `DEFINITION.RECORD_UNKNOWN`
  (the index does not hold the record; with `--index` only),
  `DEFINITION.LOCATION_MISSING` and `DEFINITION.SOURCE_MISSING`.
- **Notes**: `DOCTOR.INDEX_SKIPPED` when no `--index` is given (attachments
  were then not checked against an index); `DOCTOR.SYMBOL_UNCHECKED` for a
  `path::Symbol` location, whose file is checked but not the symbol.
- A question's identity is its IRI. A question IRI declared in more than one
  tree file of the scope (judge-jev's or a consumer extension's) is
  `QUESTIONS.DUPLICATE_IRI` naming every file: the declarations would merge
  silently in the store. Within one tree a `jj:id` is unique
  (`QUESTIONS.DUPLICATE_ID`). The shipped IRIs are
  `urn:judge-jev:question:<kind>.<id>`, so they never collide. JSON trees are
  not checked for this.
- `data` holds `ok`, `errors`, `warnings`, `notes`, `checked` (file and kind)
  and `counts`.

## Locations

REQ-JEV-0207:

| Form | Selects |
| --- | --- |
| `path` | the whole file |
| `path#Heading` | a Markdown section: the heading to the next heading of the same or higher level, parsed by Raptor's rules |
| `path::Symbol` | a code symbol, resolved by sc-agent's tree-sitter grammars |

No line ranges. judge-jev never defines tree-sitter grammars; sc-agent owns
them, and they may not be complete yet. `code` mode waits for them
(ADR-JEV-0004).

## Profile

One TOML file holds every record kind; each record id carries its kind.

```toml
[[location]]
loc     = "skills/atm-bd-lite/hooks/task-assign.md"
mode    = "prompt"
records = ["REQ-CORE-0010", "REQ-LITE-0004"]

[[location]]
loc     = "skills/atm-bd-lite/templates/dev.xml.j2"
mode    = "task"
vars    = "tests/fixtures/dev-vars.json"
records = ["REQ-CORE-0038"]
```

## Question sets

Question sets are the tool's system prompts and ship with it
(REQ-JEV-0205):

- `check`: one per record kind × target class, 6 in total;
- `quality`: one decision tree per record kind, 3 in total.

Sets and trees are data files; no question, branch or wave is written in
code. Rand approves shipped wording.

### Tuning

Making the questions production-worthy will take weeks and thousands of
variations, run against the released tool:

- A variation is a file. `--questions <file>` overrides a set or tree on the
  released build; no code change or rebuild.
- A quality tree override whose `kind` differs from the record's kind is
  refused with `QUALITY.TREE` before any call.
- A variation is checked with `judge-jev validate --tree <file>`
  (REQ-JEV-0210). It is checked whole before any call, and `--dry-run` reports the
  same error: a malformed question, a rule choice that is not an option, a
  wave without a final unconditional rule, or a cycle is `QUALITY.TREE`
  naming the wave, question or rule. No tree crashes the tool.
- Every result and log entry carries the set id and the file's content
  digest, so variations of the same set are compared by digest in the
  sc-observability log.
- Sweeping many variations is a loop over files calling `check` or
  `quality`; judge-jev needs no sweep command.

## `--dry-run`

Composes every request and calls no Jev (REQ-JEV-0208). One entry per
request a live run would send:

- record id and Raptor source;
- resolved location: path, section or symbol, digest of the selected text;
- mode and target class;
- question set: shipped id or override path;
- `task` mode: vars file and rendered text (the sc-compose strict render is
  the variable validation);
- the full composed request and its size against the request limit.

Typed errors on an unresolved record or location, a render failure or an
oversize request.

Every input yields one JSON object, its result or a typed error. An invalid
tree, question set, index, request stream or run directory, and a log event
that exceeds the logger's size limit, are refused before the first Jev
request (REQ-JEV-0211).

## Open

1. Profile paths: relative to the profile file, or to the repository root?
2. Which Raptor parser and heading rules `path#Heading` must match.
3. First question-set wording, worked out with agents and approved by Rand.
