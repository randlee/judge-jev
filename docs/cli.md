# judge-jev CLI

Draft. Two primitive commands each compose single Jev requests; the profile
run calls the second primitive once per pair and aggregates the results.
Every command takes `--dry-run`.

## `judge-jev quality`

```
judge-jev quality (--req|--adr|--nfr <id>)... [--questions <file>] [--dry-run]
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
- Never calls Jev, needs no key, writes no log.
- Output: one JSON object. Success names the kind, the path and the file's
  sha256.
- A refusal is the typed error (`QUALITY.TREE`, `INPUT.MALFORMED`,
  `VALIDATION.INPUT`, ...) naming the field path and the rule it breaks.

Diagram: [diagrams/validate.md](diagrams/validate.md)

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
