# Iteration 4 packet: two statements that still fail in some runs of the final text


======== REQ-JEV-0210 s2 ========
fails rule 1 in 2 of 6 runs: obligations=2 @0.12-0.16 with joined_by=alternatives @0.51-0.64 (a choice of exactly one flag from a list). Identical text also failed in the greedy baseline.

## CURRENT TEXT

```markdown
## REQ-JEV-0210: Validate command

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. The model for an input kind is the
Pydantic model (a typed schema class) judge-jev validates that input with
(ADR-JEV-0005). A field path is the dotted path of keys and list indexes to
the refused field, such as `nodes.wave-1.questions.context.criteria`. An
answers file is a JSON file of Jev's answers, keyed by request, that
`--answers-file` gives judge-jev in place of a live call. Its envelope is
its outer structure: its keys and the type of each value.
`JEV.RESPONSE_INVALID` is the typed error code for an answer whose
questions, choices or probabilities do not match the request.

**MUST statements:**
- `judge-jev validate` MUST take one input file.
- `judge-jev validate` MUST take one input-kind flag with that file:
  `--tree` (quality tree), `--questions` (question set), `--answers`
  (answers file), `--index` (Raptor import index) or `--requests` (batch
  request stream).
- `judge-jev validate` MUST check the file with the model `judge-jev`
  applies to that input kind before its first Jev request (ADR-JEV-0005).
- Every refusal from `judge-jev validate` MUST name the field path.
- Every refusal from `judge-jev validate` MUST name the rule the field
  breaks.
- `judge-jev validate --answers` MUST apply the answers-file envelope that
  `--answers-file` applies before the first request.
- The answers-file envelope MUST require an object of string keys.
- The answers-file envelope MUST require each key's value to be an object
  or a non-empty list of objects.
- The answers-file envelope MUST require an object with `__error__` to hold
  only a string code of at most 64 characters.

**MUST NOT statements:**
- `judge-jev validate` MUST NOT call Jev.

### Rationale

A tree variation checked before a run costs nothing; one refused after a
paid call wastes it.

The answers file stands in for Jev's response, so what an answer holds
(its questions, choices and probabilities) is not part of the envelope; it
is checked after the send as `JEV.RESPONSE_INVALID`.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every input the sweep tests refuse in `quality` is refused by
  `judge-jev validate` with the same field path.
- [ ] The shipped trees and question sets pass `judge-jev validate`.

---


```

## ORIGINAL TEXT (reference)

```markdown
## REQ-JEV-0210: Validate command

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev validate` MUST take one input file.
- `judge-jev validate` MUST take one input-kind flag with that file:
  `--tree` (quality tree), `--questions` (question set), `--answers`
  (answers file), `--index` (Raptor import index) or `--requests` (batch
  request stream).
- `judge-jev validate` MUST check the file with the model `judge-jev`
  applies to that input kind before its first Jev request (ADR-JEV-0005).
- Every refusal from `judge-jev validate` MUST name the field path.
- Every refusal from `judge-jev validate` MUST name the rule the field
  breaks.
- `judge-jev validate --answers` MUST apply the answers-file envelope that
  `--answers-file` applies before the first request.
- The answers-file envelope MUST require an object of string keys.
- The answers-file envelope MUST require each key's value to be an object
  or a non-empty list of objects.
- The answers-file envelope MUST require an object with `__error__` to hold
  only a string code of at most 64 characters.

**MUST NOT statements:**
- `judge-jev validate` MUST NOT call Jev.

### Rationale

A tree variation checked before a run costs nothing; one refused after a
paid call wastes it.

The answers file stands in for Jev's response, so what an answer holds
(its questions, choices and probabilities) is not part of the envelope; it
is checked after the send as `JEV.RESPONSE_INVALID`.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every input the sweep tests refuse in `quality` is refused by
  `judge-jev validate` with the same field path.
- [ ] The shipped trees and question sets pass `judge-jev validate`.

---


```


======== REQ-JEV-0208 s3 ========
fails rule 1 in about 1 of 6 runs: obligations=2 @0.48-0.51 with joined_by=and-list @0.34-0.37 (compose every request + without calling Jev).

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

## ORIGINAL TEXT (reference)

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
