# Iteration 3 packet: records with a statement that failed in a recent run


======== REQ-JEV-0008 ========

## CURRENT TEXT

```markdown
## REQ-JEV-0008: Logging through the sc-observability logger

**Status:** Draft  

### Requirement Statement

Definitions: The sc-observability logger is the sc-observability logger
package. A quality-tree branch is the next wave a quality decision tree's
rules select from Jev's answers.

**MUST statements:**

- judge-jev MUST write its run logs (requests, answers, quality-tree
  branches, verdicts) through the sc-observability logger, the logger
  sc-agent uses.

**MUST NOT statements:**

- judge-jev MUST NOT keep its own log format alongside it.

### Rationale

Rand (2026-11-08): "we will need to use sc-observability logger for both
(this is what sc-agent uses). we should implement in judge-jev first then
we can upgrade plan-anchor which is currently working solidly."

### Success Criteria

**Acceptance Criteria:**

- [ ] A live `check` run's requests, answers and verdicts appear in the
  sc-observability log.
- [ ] No judge-jev command writes `anchor-runs/tournament-*.jsonl`.

### Implementation Notes

Today the copied core writes its own `anchor-runs/tournament-<run>.jsonl`
(`jev_judge.py` `pump_batch`). plan-anchor moves to the same logger after
judge-jev.


```

## ORIGINAL TEXT (reference only)

```markdown
## REQ-JEV-0008: Logging through the sc-observability logger

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST write its run logs (requests, answers, quality-tree
  branches, verdicts) through the sc-observability logger, the logger
  sc-agent uses.

**MUST NOT statements:**

- judge-jev MUST NOT keep its own log format alongside it.

### Rationale

Rand (2026-11-08): "we will need to use sc-observability logger for both
(this is what sc-agent uses). we should implement in judge-jev first then
we can upgrade plan-anchor which is currently working solidly."

### Success Criteria

**Acceptance Criteria:**

- [ ] A live `check` run's requests, answers and verdicts appear in the
  sc-observability log.
- [ ] No judge-jev command writes `anchor-runs/tournament-*.jsonl`.

### Implementation Notes

Today the copied core writes its own `anchor-runs/tournament-<run>.jsonl`
(`jev_judge.py` `pump_batch`). plan-anchor moves to the same logger after
judge-jev.


```

## Statements that FAILED in at least one of 12 recent runs (some runs were on slightly different text of this record), with every run's answers:

- s1: 'judge-jev MUST write its run logs (requests, answers, quality-tree\nbranches, verdicts) through the sc-observability logger, the logger\nsc-agent uses.'
    - FAIL: obligations=1@0.87; joined_by=none@0.68; term=undefined acronym@0.27; check=CLI run@0.34
    - FAIL: obligations=1@0.85; joined_by=none@0.73; term=undefined acronym@0.31; check=CLI run@0.30
    - FAIL: obligations=1@0.89; joined_by=none@0.66; term=undefined acronym@0.31; check=CLI run@0.31
    - FAIL: obligations=1@0.85; joined_by=none@0.73; term=undefined acronym@0.32; check=CLI run@0.37
    - FAIL: obligations=1@0.83; joined_by=none@0.74; term=undefined acronym@0.30; check=CLI run@0.34
    - FAIL: obligations=1@0.88; joined_by=none@0.75; term=undefined acronym@0.34; check=CLI run@0.39
    - pass: obligations=1@0.77; joined_by=none@0.57; term=none@0.39; check=CLI run@0.39
    - pass: obligations=1@0.79; joined_by=none@0.73; term=none@0.32; check=CLI run@0.32
    - pass: obligations=1@0.75; joined_by=none@0.64; term=none@0.42; check=CLI run@0.35
    - pass: obligations=1@0.80; joined_by=none@0.68; term=none@0.36; check=CLI run@0.35
    - pass: obligations=1@0.72; joined_by=none@0.69; term=none@0.34; check=CLI run@0.26
    - pass: obligations=1@0.75; joined_by=none@0.69; term=none@0.37; check=CLI run@0.34

======== REQ-JEV-0101 ========

## CURRENT TEXT

```markdown
## REQ-JEV-0101: Record quality mode

**Status:** Proposed  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A quality decision tree is a data file of prompts (questions to Jev)
in waves; a wave is one set of questions. A verdict rule is a rule that
turns a wave's answers into a verdict. The walk is the sequence of waves;
its decision-tree path is the list of those waves' ids.

**MUST statements:**

- judge-jev MUST provide a mode that reports, for one requirement (REQ),
  non-functional requirement (NFR) or architecture decision record (ADR),
  the verdict of that record kind's quality decision tree.
- The mode MUST judge only records that Raptor imported without
  diagnostics.
- The mode MUST run as a decision tree of prompts: each wave sends several
  questions, and the answers to one wave select the next wave's questions.
- Every wave MUST report, as its reason, each of its questions with the
  question's id and text, Jev's choice and Jev's confidence.
- A wave the tree marks per statement MUST send one request for each MUST
  and MUST NOT statement of the record.
- Each per-statement request MUST carry its statement with the whole record
  as context.
- A per-statement wave's reason MUST list each statement's index and text
  with each question's id, choice and confidence.
- A per-statement wave's verdict rule MUST be able to fire when any one
  statement's answers match it.
- A per-statement wave's verdict MUST name the statements whose answers
  fired its rule.
- A per-statement request that gets no answer MUST fail with an error that
  names its statement.
- A wave after the first MUST refine the answers of the wave before it.
- A wave after the first MUST be designed from the observed live results
  of the wave before it.
- A wave with no next wave MUST end the walk, with its verdict given by a
  rule in the tree file over that wave's answers.
- The tree MUST ship with the tool as a data file a consumer can override
  (REQ-JEV-0205); answers select the branch and the verdict, never a model
  choosing the next questions.
- A failing answer MUST report the decision-tree path that failed.
- A live run MUST log every wave as output: its composed request, Jev's
  answers, its reason and the branch or verdict they selected.

**MUST NOT statements:**

- The mode MUST NOT check structure that Raptor's import checks.

### Rationale

Importing is part of complying with the schema: Raptor's import
diagnostics (REQ-RAP-0012) bring a document into the schema, then this
mode judges whether each imported record is well written. Prose evaluation
uses only records that pass both.

Rand (2026-11-08): "for the 'is this adr/nfr/req high quality' mode, I
would expect this to be a decision tree of prompts. each layer of the tree
would output several questions which based on the wave-1 outputs would
result in a new set of questions to narrow in." On a dry run showing only
wave 1: "as long as real run logs all info as output (sc-agent will do logging and is
almost ready to start testing)."

Rand (2026-11-08), after the first live run reported only fixed leaf text:
"every wave needs to provide some 'reason' the next wave is just to refine
it. You can't design wave-2 until you see wave-1 results so you know what
wave-2 should ask." The shipped trees therefore hold wave 1 only; a wave 2
is designed from wave 1's observed answers.

Rand (2026-11-08) approved per-statement waves: one request per MUST / MUST
NOT statement, with that statement plus the whole record as context, so a
failure names the statement to fix.

### Success Criteria

**Acceptance Criteria:**

- [ ] Fixed answers to a wave select the same next wave every run.
- [ ] Every wave's result lists each of its questions with id, text,
  choice and confidence.
- [ ] A live run's log holds each wave's request, answers, reason and
  selected branch or verdict.
- [ ] A REQ with two MUST statements and one SHOULD statement sends two
  wave-1 requests, one per MUST statement.
- [ ] A REQ whose third statement answers `check: none` reports `no`, names
  statement 3, and lists every statement's answers in wave 1's reason.
- [ ] A dry run shows the composed wave-1 request for every statement.
- [ ] A record Raptor rejected is not sent to Jev.

### Implementation Notes

Logging goes through the sc-observability logger (REQ-JEV-0008). A
per-statement node sets `"per": "statement"`, `statements` (the record
field holding the statements) and `modals` (the modals judged); each
statement is one request whose item text is `{statement, record}`. The
shipped REQ and NFR trees ask, per statement, `obligations`, `joined_by`,
`term` and `check`; the ADR tree asks, per record, `context`,
`alternatives` and `consequences`. Each option's criterion carries its fix
hint, and the reason reports it.

```

## ORIGINAL TEXT (reference only)

```markdown
## REQ-JEV-0101: Record quality mode

**Status:** Proposed  

### Requirement Statement

**MUST statements:**

- judge-jev MUST provide a mode that reports, for one requirement (REQ),
  non-functional requirement (NFR) or architecture decision record (ADR),
  the verdict of that record kind's quality decision tree.
- The mode MUST judge only records that Raptor imported without
  diagnostics.
- The mode MUST run as a decision tree of prompts: each wave sends several
  questions, and the answers to one wave select the next wave's questions.
- Every wave MUST report, as its reason, each of its questions with the
  question's id and text, Jev's choice and Jev's confidence.
- A wave the tree marks per statement MUST send one request for each MUST
  and MUST NOT statement of the record, carrying that statement with the
  whole record as context.
- A per-statement wave's reason MUST list each statement's index and text
  with each question's id, choice and confidence.
- A per-statement wave's verdict rule MUST be able to fire when any one
  statement's answers match it.
- A per-statement wave's verdict MUST name the statements whose answers
  fired its rule.
- A per-statement request that gets no answer MUST fail with an error that
  names its statement.
- A wave after the first MUST refine the answers of the wave before it.
- A wave after the first MUST be designed from the observed live results
  of the wave before it.
- A wave with no next wave MUST end the walk, with its verdict given by a
  rule in the tree file over that wave's answers.
- The tree MUST ship with the tool as a data file a consumer can override
  (REQ-JEV-0205); answers select the branch and the verdict, never a model
  choosing the next questions.
- A failing answer MUST report the decision-tree path that failed.
- A live run MUST log every wave as output: its composed request, Jev's
  answers, its reason and the branch or verdict they selected.

**MUST NOT statements:**

- The mode MUST NOT check structure that Raptor's import checks.

### Rationale

Importing is part of complying with the schema: Raptor's import
diagnostics (REQ-RAP-0012) bring a document into the schema, then this
mode judges whether each imported record is well written. Prose evaluation
uses only records that pass both.

Rand (2026-11-08): "for the 'is this adr/nfr/req high quality' mode, I
would expect this to be a decision tree of prompts. each layer of the tree
would output several questions which based on the wave-1 outputs would
result in a new set of questions to narrow in." On a dry run showing only
wave 1: "as long as real run logs all info as output (sc-agent will do logging and is
almost ready to start testing)."

Rand (2026-11-08), after the first live run reported only fixed leaf text:
"every wave needs to provide some 'reason' the next wave is just to refine
it. You can't design wave-2 until you see wave-1 results so you know what
wave-2 should ask." The shipped trees therefore hold wave 1 only; a wave 2
is designed from wave 1's observed answers.

Rand (2026-11-08) approved per-statement waves: one request per MUST / MUST
NOT statement, with that statement plus the whole record as context, so a
failure names the statement to fix.

### Success Criteria

**Acceptance Criteria:**

- [ ] Fixed answers to a wave select the same next wave every run.
- [ ] Every wave's result lists each of its questions with id, text,
  choice and confidence.
- [ ] A live run's log holds each wave's request, answers, reason and
  selected branch or verdict.
- [ ] A REQ with two MUST statements and one SHOULD statement sends two
  wave-1 requests, one per MUST statement.
- [ ] A REQ whose third statement answers `check: none` reports `no`, names
  statement 3, and lists every statement's answers in wave 1's reason.
- [ ] A dry run shows the composed wave-1 request for every statement.
- [ ] A record Raptor rejected is not sent to Jev.

### Implementation Notes

Logging goes through the sc-observability logger (REQ-JEV-0008). A
per-statement node sets `"per": "statement"`, `statements` (the record
field holding the statements) and `modals` (the modals judged); each
statement is one request whose item text is `{statement, record}`. The
shipped REQ and NFR trees ask, per statement, `obligations`, `joined_by`,
`term` and `check`; the ADR tree asks, per record, `context`,
`alternatives` and `consequences`. Each option's criterion carries its fix
hint, and the reason reports it.

```

## Statements that FAILED in at least one of 12 recent runs (some runs were on slightly different text of this record), with every run's answers:

- s17: "The mode MUST NOT check structure that Raptor's import checks."
    - pass: obligations=1@0.97; joined_by=none@0.79; term=none@0.16; check=unit test@0.31
    - FAIL: obligations=1@0.99; joined_by=none@0.84; term=undefined acronym@0.16; check=unit test@0.35
    - pass: obligations=1@0.99; joined_by=none@0.80; term=none@0.31; check=unit test@0.32
    - pass: obligations=1@0.99; joined_by=none@0.80; term=none@0.19; check=unit test@0.36
    - pass: obligations=1@0.97; joined_by=none@0.81; term=none@0.29; check=unit test@0.35
    - pass: obligations=1@0.97; joined_by=none@0.76; term=none@0.25; check=unit test@0.37
    - pass: obligations=1@0.97; joined_by=none@0.81; term=none@0.21; check=unit test@0.36
    - pass: obligations=1@0.96; joined_by=none@0.74; term=none@0.29; check=unit test@0.45
    - pass: obligations=1@0.97; joined_by=none@0.82; term=none@0.32; check=unit test@0.44
    - pass: obligations=1@0.99; joined_by=none@0.81; term=none@0.37; check=unit test@0.41
    - pass: obligations=1@0.96; joined_by=none@0.86; term=none@0.30; check=unit test@0.32
    - pass: obligations=1@0.99; joined_by=none@0.76; term=none@0.26; check=unit test@0.35

======== REQ-JEV-0207 ========

## CURRENT TEXT

```markdown
## REQ-JEV-0207: Location syntax

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool. sc-agent is the agent tool.
Tree-sitter grammars are the parsers.

**MUST statements:**
- A location MUST take one of three forms: `path`, `path#Heading` or
  `path::Symbol`.
- A `path` location MUST select the whole file.
- A `path#Heading` location MUST select a Markdown section, from the
  heading to the next heading of the same or higher level.
- A `path::Symbol` location MUST select a code symbol resolved by
  sc-agent's tree-sitter grammars.
- Markdown sections MUST be parsed by the same rules Raptor uses.

**MUST NOT statements:**
- A location MUST NOT be a line range.

### Rationale

Line ranges drift on every edit; headings and symbols survive. One
Markdown parsing rule keeps judge-jev and Raptor agreeing on what a
section is.

### Success Criteria

**Acceptance Criteria:**
- [ ] `path#Heading` selects the same text Raptor attributes to that
  heading.
- [ ] A heading or symbol that does not resolve is a typed error naming the
  location.

### Implementation Notes

Open: which Raptor parser and heading rules judge-jev matches, and whether
paths in a profile are relative to the profile or to the repository root.

---


```

## ORIGINAL TEXT (reference only)

```markdown
## REQ-JEV-0207: Location syntax

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- A location MUST take one of three forms: `path`, `path#Heading` or
  `path::Symbol`.
- A `path` location MUST select the whole file.
- A `path#Heading` location MUST select a Markdown section, from the
  heading to the next heading of the same or higher level.
- A `path::Symbol` location MUST select a code symbol resolved by
  sc-agent's tree-sitter grammars.
- Markdown sections MUST be parsed by the same rules Raptor uses for the
  same file.

**MUST NOT statements:**
- A location MUST NOT be a line range.

### Rationale

Line ranges drift on every edit; headings and symbols survive. One
Markdown parsing rule keeps judge-jev and Raptor agreeing on what a
section is.

### Success Criteria

**Acceptance Criteria:**
- [ ] `path#Heading` selects the same text Raptor attributes to that
  heading.
- [ ] A heading or symbol that does not resolve is a typed error naming the
  location.

### Implementation Notes

Open: which Raptor parser and heading rules judge-jev matches, and whether
paths in a profile are relative to the profile or to the repository root.

---


```

## Statements that FAILED in at least one of 12 recent runs (some runs were on slightly different text of this record), with every run's answers:

- s4: "A `path::Symbol` location MUST select a code symbol resolved by\nsc-agent's tree-sitter grammars."
    - FAIL: obligations=1@0.84; joined_by=none@0.91; term=project term defined nowhere@0.39; check=unit test@0.76
    - pass: obligations=1@0.79; joined_by=none@0.91; term=none@0.49; check=unit test@0.79
    - pass: obligations=1@0.85; joined_by=none@0.90; term=none@0.40; check=unit test@0.75
    - pass: obligations=1@0.77; joined_by=none@0.87; term=none@0.36; check=unit test@0.65
    - pass: obligations=1@0.83; joined_by=none@0.84; term=none@0.40; check=unit test@0.71
    - pass: obligations=1@0.80; joined_by=none@0.92; term=none@0.44; check=unit test@0.76
    - pass: obligations=1@0.87; joined_by=none@0.91; term=none@0.66; check=unit test@0.70
    - pass: obligations=1@0.84; joined_by=none@0.90; term=none@0.64; check=unit test@0.75
    - pass: obligations=1@0.81; joined_by=none@0.91; term=none@0.65; check=unit test@0.70
    - pass: obligations=1@0.85; joined_by=none@0.90; term=none@0.56; check=unit test@0.73
    - pass: obligations=1@0.79; joined_by=none@0.92; term=none@0.65; check=unit test@0.71
    - pass: obligations=1@0.76; joined_by=none@0.87; term=none@0.64; check=unit test@0.69

======== REQ-JEV-0208 ========

## CURRENT TEXT

```markdown
## REQ-JEV-0208: Dry run audits the composed request

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. Raptor is the requirements tool that imports Markdown records
(ADR-JEV-0002). A dry run is a run with `--dry-run`: it composes every
request and sends none. The digest of a text is its SHA-256. A mode (target
mode) names what a location holds: `prompt` (prompt text), `skill` (a skill
file), `task` (a task template) or `code` (source code). A question set is
the data file of questions sent to Jev; its shipped id is the `id` of a set
shipped with the tool, its override path the file given with `--questions`.
A vars file holds the values of a task template's variables. The request
limit is 24000 bytes by default. A quality decision tree is the data file of
questions that judges whether a record is well written: waves of questions
(REQ-JEV-0101). The wave-1 request is the request for its first wave.

**MUST statements:**
- `judge-jev quality` MUST accept `--dry-run`.
- `judge-jev check` MUST accept `--dry-run`.
- A dry run MUST compose every request without calling Jev.
- Each dry-run entry MUST report the record id.
- Each dry-run entry MUST report the record's Raptor source.
- Each dry-run entry MUST report the resolved location as its path, section
  or symbol.
- Each dry-run entry MUST report the digest of the location's selected
  text.
- Each dry-run entry MUST report the mode.
- Each dry-run entry MUST report the question set as its shipped id or its
  override path.
- In `task` mode, each dry-run entry MUST report the vars file.
- In `task` mode, each dry-run entry MUST report the rendered text.
- Each dry-run entry MUST report the full composed request.
- Each dry-run entry MUST report the composed request's size against the
  request limit.
- For `quality`, the dry run MUST report the decision tree.
- For `quality`, the dry run MUST report the composed wave-1 request.
- A dry run MUST fail with a typed error on anything that would make the
  live request wrong: an unresolved record or location, a render failure,
  or an oversize request.

### Rationale

The caller must know the prompt will be built correctly before any text
leaves the machine. A `quality` dry run stops at wave 1 because later
waves depend on live answers.

### Success Criteria

**Acceptance Criteria:**
- [ ] A dry run makes no network call and reports one entry per request a
  live run would send.
- [ ] A dry run over a task location with a missing variable fails naming
  the variable.

---


```

## ORIGINAL TEXT (reference only)

```markdown
## REQ-JEV-0208: Dry run audits the composed request

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev quality` MUST accept `--dry-run`.
- `judge-jev check` MUST accept `--dry-run`.
- A dry run MUST compose every request without calling Jev.
- Each dry-run entry MUST report the record id.
- Each dry-run entry MUST report the record's Raptor source.
- Each dry-run entry MUST report the resolved location as its path, section
  or symbol.
- Each dry-run entry MUST report the digest of the location's selected
  text.
- Each dry-run entry MUST report the mode.
- Each dry-run entry MUST report the question set as its shipped id or its
  override path.
- In `task` mode, each dry-run entry MUST report the vars file.
- In `task` mode, each dry-run entry MUST report the rendered text.
- Each dry-run entry MUST report the full composed request.
- Each dry-run entry MUST report the composed request's size against the
  request limit.
- For `quality`, the dry run MUST report the decision tree.
- For `quality`, the dry run MUST report the composed wave-1 request.
- A dry run MUST fail with a typed error on anything that would make the
  live request wrong: an unresolved record or location, a render failure,
  or an oversize request.

### Rationale

The caller must know the prompt will be built correctly before any text
leaves the machine. A `quality` dry run stops at wave 1 because later
waves depend on live answers.

### Success Criteria

**Acceptance Criteria:**
- [ ] A dry run makes no network call and reports one entry per request a
  live run would send.
- [ ] A dry run over a task location with a missing variable fails naming
  the variable.

---


```

## Statements that FAILED in at least one of 12 recent runs (some runs were on slightly different text of this record), with every run's answers:

- s3: 'A dry run MUST compose every request without calling Jev.'
    - pass: obligations=2@0.39; joined_by=none@0.57; term=none@0.71; check=CLI run@0.50
    - pass: obligations=2@0.41; joined_by=none@0.34; term=none@0.71; check=CLI run@0.62
    - pass: obligations=2@0.39; joined_by=none@0.57; term=none@0.73; check=CLI run@0.54
    - pass: obligations=2@0.45; joined_by=none@0.35; term=none@0.70; check=CLI run@0.50
    - pass: obligations=1@0.32; joined_by=none@0.41; term=none@0.73; check=CLI run@0.54
    - pass: obligations=1@0.36; joined_by=none@0.37; term=none@0.71; check=CLI run@0.54
    - pass: obligations=2@0.52; joined_by=none@0.39; term=none@0.84; check=CLI run@0.66
    - pass: obligations=2@0.45; joined_by=none@0.36; term=none@0.84; check=CLI run@0.66
    - pass: obligations=2@0.45; joined_by=none@0.40; term=none@0.79; check=CLI run@0.70
    - pass: obligations=2@0.45; joined_by=none@0.46; term=none@0.82; check=CLI run@0.64
    - pass: obligations=2@0.47; joined_by=none@0.37; term=none@0.84; check=CLI run@0.60
    - FAIL: obligations=2@0.57; joined_by=and-list@0.52; term=none@0.81; check=CLI run@0.66
- s16: 'A dry run MUST fail with a typed error on anything that would make the\nlive request wrong: an unresolved record or location, a render failure,\nor an oversize request.'
    - pass: obligations=3@0.37; joined_by=condition+obligation@0.49; term=none@0.36; check=CLI run@0.74
    - pass: obligations=3@0.35; joined_by=condition+obligation@0.40; term=none@0.34; check=CLI run@0.73
    - FAIL: obligations=3@0.23; joined_by=condition+obligation@0.64; term=project term defined nowhere@0.30; check=CLI run@0.75
    - FAIL: obligations=3@0.21; joined_by=condition+obligation@0.42; term=project term defined nowhere@0.34; check=CLI run@0.73
    - pass: obligations=3@0.25; joined_by=condition+obligation@0.35; term=none@0.35; check=CLI run@0.75
    - pass: obligations=3@0.27; joined_by=condition+obligation@0.46; term=none@0.32; check=CLI run@0.70
    - pass: obligations=3@0.33; joined_by=condition+obligation@0.51; term=none@0.42; check=CLI run@0.73
    - pass: obligations=3@0.23; joined_by=condition+obligation@0.59; term=none@0.32; check=CLI run@0.76
    - pass: obligations=3@0.31; joined_by=condition+obligation@0.52; term=none@0.44; check=CLI run@0.77
    - pass: obligations=3@0.24; joined_by=condition+obligation@0.54; term=none@0.45; check=CLI run@0.76
    - pass: obligations=3@0.33; joined_by=condition+obligation@0.52; term=none@0.31; check=CLI run@0.75
    - pass: obligations=3@0.20; joined_by=condition+obligation@0.54; term=none@0.35; check=CLI run@0.76