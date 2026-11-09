# Packet group C (iteration 1)


======== REQ-JEV-0209 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0209: Record quality command

**Status:** Draft  

### Requirement Statement

Definitions: A run name is the name every log event of one invocation
carries (`--run-name`).

**MUST statements:**
- `judge-jev quality` MUST take one or more record ids.
- `judge-jev quality` MUST take each record id with one record-kind flag:
  `--req` (requirement), `--adr` (architecture decision record) or `--nfr`
  (non-functional requirement).
- Every record-kind flag of `judge-jev quality` MUST be repeatable.
- `judge-jev quality` MUST judge each record with its kind's quality
  decision tree (REQ-JEV-0101).
- All records of one `judge-jev quality` invocation MUST be logged under
  one run name.

### Rationale

Quality and compliance are separate questions about separate inputs. One
run name per invocation groups a measurement over many records in the
log.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every request `judge-jev quality --req <id>` sends carries only the
  record and questions from the REQ quality tree.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0209: Record quality command

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev quality` MUST take one or more record ids.
- `judge-jev quality` MUST take each record id with one record-kind flag:
  `--req` (requirement), `--adr` (architecture decision record) or `--nfr`
  (non-functional requirement).
- Every record-kind flag of `judge-jev quality` MUST be repeatable.
- `judge-jev quality` MUST judge each record with its kind's quality
  decision tree (REQ-JEV-0101).
- All records of one `judge-jev quality` invocation MUST be logged under
  one run name.

### Rationale

Quality and compliance are separate questions about separate inputs. One
run name per invocation groups a measurement over many records in the
log.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every request `judge-jev quality --req <id>` sends carries only the
  record and questions from the REQ quality tree.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: '`judge-jev quality` MUST take one or more record ids.'
    - pass: obligations=1@0.84; joined_by=none@0.73; term=none@0.45; check=CLI run@0.84
    - pass: obligations=1@0.87; joined_by=none@0.74; term=none@0.45; check=CLI run@0.86
    - pass: obligations=1@0.92; joined_by=none@0.70; term=none@0.47; check=CLI run@0.85
- s2: '`judge-jev quality` MUST take each record id with one record-kind flag:\n`--req` (requirement), `--adr` (architecture decision record) or `--nfr`\n(non-functional requirement).'
    - pass: obligations=1@0.49; joined_by=alternatives@0.47; term=none@0.52; check=CLI run@0.77
    - pass: obligations=1@0.44; joined_by=alternatives@0.45; term=none@0.47; check=CLI run@0.79
    - pass: obligations=1@0.49; joined_by=alternatives@0.50; term=none@0.49; check=CLI run@0.76
- s3: 'Every record-kind flag of `judge-jev quality` MUST be repeatable.'
    - FAIL R2: obligations=1@0.88; joined_by=none@0.94; term=project term defined nowhere@0.34; check=CLI run@0.76
    - FAIL R2: obligations=1@0.81; joined_by=none@0.94; term=project term defined nowhere@0.27; check=CLI run@0.74
    - pass: obligations=1@0.89; joined_by=none@0.96; term=none@0.31; check=CLI run@0.77
- s4: "`judge-jev quality` MUST judge each record with its kind's quality\ndecision tree (REQ-JEV-0101)."
    - pass: obligations=1@0.93; joined_by=none@0.98; term=none@0.25; check=unit test@0.41
    - pass: obligations=1@0.92; joined_by=none@0.98; term=none@0.32; check=CLI run@0.37
    - pass: obligations=1@0.91; joined_by=none@0.96; term=none@0.36; check=unit test@0.36
- s5: 'All records of one `judge-jev quality` invocation MUST be logged under\none run name.'
    - pass: obligations=1@0.97; joined_by=none@0.86; term=none@0.84; check=inspection or grep@0.79
    - pass: obligations=1@0.96; joined_by=none@0.84; term=none@0.85; check=inspection or grep@0.75
    - pass: obligations=1@0.96; joined_by=none@0.82; term=none@0.81; check=inspection or grep@0.73


======== REQ-JEV-0210 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

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

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

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

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: '`judge-jev validate` MUST take one input file.'
    - pass: obligations=1@0.95; joined_by=none@0.98; term=none@0.77; check=CLI run@0.89
    - pass: obligations=1@0.96; joined_by=none@0.99; term=none@0.73; check=CLI run@0.86
    - pass: obligations=1@0.95; joined_by=none@0.99; term=none@0.75; check=CLI run@0.86
- s2: '`judge-jev validate` MUST take one input-kind flag with that file:\n`--tree` (quality tree), `--questions` (question set), `--answers`\n(answers file), `--index` (Raptor import index) or `--requests` (batch\nrequest stream).'
    - pass: obligations=1@0.16; joined_by=alternatives@0.61; term=none@0.56; check=CLI run@0.89
    - pass: obligations=1@0.25; joined_by=alternatives@0.62; term=none@0.59; check=CLI run@0.89
    - pass: obligations=1@0.16; joined_by=alternatives@0.62; term=none@0.59; check=CLI run@0.87
- s3: '`judge-jev validate` MUST check the file with the model `judge-jev`\napplies to that input kind before its first Jev request (ADR-JEV-0005).'
    - pass: obligations=1@0.75; joined_by=condition+obligation@0.51; term=none@0.69; check=unit test@0.30
    - pass: obligations=1@0.63; joined_by=condition+obligation@0.44; term=none@0.71; check=unit test@0.26
    - pass: obligations=1@0.69; joined_by=condition+obligation@0.51; term=none@0.71; check=unit test@0.32
- s4: 'Every refusal from `judge-jev validate` MUST name the field path.'
    - pass: obligations=1@0.93; joined_by=condition+obligation@0.54; term=none@0.76; check=CLI run@0.49
    - pass: obligations=1@0.93; joined_by=condition+obligation@0.44; term=none@0.76; check=CLI run@0.46
    - pass: obligations=1@0.89; joined_by=condition+obligation@0.52; term=none@0.74; check=CLI run@0.42
- s5: 'Every refusal from `judge-jev validate` MUST name the rule the field\nbreaks.'
    - pass: obligations=1@0.87; joined_by=condition+obligation@0.50; term=none@0.69; check=CLI run@0.62
    - pass: obligations=1@0.89; joined_by=condition+obligation@0.52; term=none@0.56; check=CLI run@0.66
    - pass: obligations=1@0.92; joined_by=condition+obligation@0.49; term=none@0.61; check=CLI run@0.59
- s6: '`judge-jev validate --answers` MUST apply the answers-file envelope that\n`--answers-file` applies before the first request.'
    - pass: obligations=1@0.87; joined_by=none@0.73; term=none@0.85; check=CLI run@0.49
    - pass: obligations=1@0.91; joined_by=none@0.66; term=none@0.84; check=CLI run@0.47
    - pass: obligations=1@0.91; joined_by=none@0.74; term=none@0.85; check=CLI run@0.37
- s7: 'The answers-file envelope MUST require an object of string keys.'
    - pass: obligations=1@0.84; joined_by=none@0.98; term=none@0.90; check=unit test@0.57
    - pass: obligations=1@0.84; joined_by=none@0.95; term=none@0.90; check=unit test@0.55
    - pass: obligations=1@0.87; joined_by=none@0.98; term=none@0.89; check=unit test@0.54
- s8: "The answers-file envelope MUST require each key's value to be an object\nor a non-empty list of objects."
    - pass: obligations=1@0.61; joined_by=alternatives@0.74; term=none@0.80; check=unit test@0.52
    - pass: obligations=1@0.65; joined_by=alternatives@0.79; term=none@0.84; check=unit test@0.54
    - pass: obligations=1@0.67; joined_by=alternatives@0.77; term=none@0.82; check=unit test@0.46
- s9: 'The answers-file envelope MUST require an object with `__error__` to hold\nonly a string code of at most 64 characters.'
    - pass: obligations=3@0.29; joined_by=none@0.50; term=none@0.85; check=unit test@0.55
    - pass: obligations=3@0.39; joined_by=none@0.60; term=none@0.86; check=unit test@0.54
    - pass: obligations=3@0.36; joined_by=none@0.59; term=none@0.85; check=unit test@0.46
- s10: '`judge-jev validate` MUST NOT call Jev.'
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.87; check=unit test@0.32
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.84; check=unit test@0.35
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.84; check=unit test@0.37


======== REQ-JEV-0211 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0211: A typed result for every input

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. A `judge-jev` command's result is
the JSON object it prints on success. A typed error is a JSON error object
with a stable `code` (such as `INPUT.MALFORMED`), a `message` and a
`suggested_action`. A tree is a quality decision tree file, a question set a
file of questions, an index a Raptor import index, a request stream the
request lines of the batch command, and a run directory the folder that
holds a run's log. A log event is one event written through the
sc-observability logger; the logger's event size limit is 65536 bytes
(sc-observability 1.5.0).

**MUST statements:**
- For every input, every `judge-jev` command MUST print exactly one JSON
  object.
- The JSON object a `judge-jev` command prints MUST be its result or a
  typed error.
- `judge-jev` MUST refuse an invalid tree, question set, index, request
  stream or run directory before its first Jev request.
- `judge-jev` MUST check that every log event of a request (the request,
  Jev's largest possible answer and the result) fits the logger's event
  size limit before sending the request.

### Rationale

Rand Lee, 2026-11-08: "Crash is not acceptable for any input." A refusal
after a paid call wastes the call; a crash loses its answer.

### Success Criteria

**Acceptance Criteria:**
- [ ] The sweep tests (every field of a tree, index and answers file
  replaced by each of a fixed list of wrong values, deleted or given an
  extra key, and raw JSON no value expresses) produce no `SCRIPT.INTERNAL`
  and no refusal after a request is sent.
- [ ] Invalid UTF-8 on stdin is refused with `INPUT.MALFORMED`.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0211: A typed result for every input

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- For every input, every `judge-jev` command MUST print exactly one JSON
  object.
- The JSON object a `judge-jev` command prints MUST be its result or a
  typed error.
- `judge-jev` MUST refuse an invalid tree, question set, index, request
  stream or run directory before its first Jev request.
- `judge-jev` MUST check that every log event of a request (the request,
  Jev's largest possible answer and the result) fits the logger's event
  size limit before sending the request.

### Rationale

Rand Lee, 2026-11-08: "Crash is not acceptable for any input." A refusal
after a paid call wastes the call; a crash loses its answer.

### Success Criteria

**Acceptance Criteria:**
- [ ] The sweep tests (every field of a tree, index and answers file
  replaced by each of a fixed list of wrong values, deleted or given an
  extra key, and raw JSON no value expresses) produce no `SCRIPT.INTERNAL`
  and no refusal after a request is sent.
- [ ] Invalid UTF-8 on stdin is refused with `INPUT.MALFORMED`.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'For every input, every `judge-jev` command MUST print exactly one JSON\nobject.'
    - pass: obligations=1@0.17; joined_by=none@0.75; term=none@0.64; check=CLI run@0.84
    - pass: obligations=1@0.19; joined_by=none@0.77; term=none@0.61; check=CLI run@0.84
    - pass: obligations=1@0.16; joined_by=none@0.77; term=none@0.57; check=CLI run@0.81
- s2: 'The JSON object a `judge-jev` command prints MUST be its result or a\ntyped error.'
    - pass: obligations=1@0.81; joined_by=alternatives@0.85; term=none@0.80; check=CLI run@0.77
    - pass: obligations=1@0.85; joined_by=alternatives@0.84; term=none@0.80; check=CLI run@0.82
    - pass: obligations=1@0.85; joined_by=alternatives@0.84; term=none@0.82; check=CLI run@0.82
- s3: '`judge-jev` MUST refuse an invalid tree, question set, index, request\nstream or run directory before its first Jev request.'
    - FAIL R1: obligations=4+@0.35; joined_by=alternatives@0.29; term=none@0.76; check=CLI run@0.74
    - pass: obligations=1@0.32; joined_by=alternatives@0.30; term=none@0.75; check=CLI run@0.75
    - pass: obligations=1@0.47; joined_by=condition+obligation@0.31; term=none@0.74; check=CLI run@0.77
- s4: "`judge-jev` MUST check that every log event of a request (the request,\nJev's largest possible answer and the result) fits the logger's event\nsize limit before sending the request."
    - pass: obligations=1@0.52; joined_by=none@0.47; term=none@0.74; check=unit test@0.56
    - pass: obligations=1@0.56; joined_by=none@0.47; term=none@0.64; check=unit test@0.55
    - pass: obligations=1@0.56; joined_by=none@0.50; term=none@0.73; check=unit test@0.55


======== REQ-JEV-0212 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0212: Targeted definitions

**Status:** Draft  

### Requirement Statement

Definitions: A definition is a term with its meaning, from a
`.sc/judge-jev/*.definitions.ttl` file (ADR-JEV-0008). It is attached to a
record, or to a record and a location (the file, Markdown section or code
symbol being judged). A request's state is the data it sends to Jev next to
the questions, which holds the record. The size limit of a request is 24000
bytes. A definition's digest is the SHA-256 of its term, text and source.

**MUST statements:**
- A definition MUST be attachable to a record alone, or to a record and
  one location under evaluation.
- A request about a record MUST carry, in its state next to the record, only
  the definitions attached to that record alone, plus those attached to
  that record and the request's location.
- A request with no matching definition MUST be identical to the request
  sent without definitions.
- `judge-jev` MUST refuse, before sending, a request whose definitions take
  it over the size limit.
- Every request's log event MUST record the digest of each definition it
  carried.

**MUST NOT statements:**
- `judge-jev` MUST NOT truncate a definition.

### Rationale

Rand Lee, 2026-11-08: "we can NOT write a single definition file and add it
to every prompt" when running over 1000 to 2000 records with 1 to 200
locations each. A record-only definition "makes the req/nfr/adr w/ confusing
term carry the definition w/ it for all jev calls"; a record-and-location
definition "would only be added to specific data (code/prompt/skill) which
requires clarification".

### Success Criteria

**Acceptance Criteria:**
- [ ] With definitions linked to record A only, the requests for record B
  are byte-identical to a run without definitions.
- [ ] The requests for record A carry exactly A's definitions, and their log
  events list those definitions' digests.
- [ ] A definition attached to record A and location X is carried by A's
  request for X and by no other request about A.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0212: Targeted definitions

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- A definition MUST be attachable to a record alone, or to a record and
  one location under evaluation.
- A request about a record MUST carry, in its state next to the record, only
  the definitions attached to that record alone, plus those attached to
  that record and the request's location.
- A request with no matching definition MUST be identical to the request
  sent without definitions.
- `judge-jev` MUST refuse, before sending, a request whose definitions take
  it over the size limit.
- Every request's log event MUST record the digest of each definition it
  carried.

**MUST NOT statements:**
- `judge-jev` MUST NOT truncate a definition.

### Rationale

Rand Lee, 2026-11-08: "we can NOT write a single definition file and add it
to every prompt" when running over 1000 to 2000 records with 1 to 200
locations each. A record-only definition "makes the req/nfr/adr w/ confusing
term carry the definition w/ it for all jev calls"; a record-and-location
definition "would only be added to specific data (code/prompt/skill) which
requires clarification".

### Success Criteria

**Acceptance Criteria:**
- [ ] With definitions linked to record A only, the requests for record B
  are byte-identical to a run without definitions.
- [ ] The requests for record A carry exactly A's definitions, and their log
  events list those definitions' digests.
- [ ] A definition attached to record A and location X is carried by A's
  request for X and by no other request about A.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'A definition MUST be attachable to a record alone, or to a record and\none location under evaluation.'
    - pass: obligations=1@0.65; joined_by=alternatives@0.87; term=none@0.62; check=unit test@0.51
    - pass: obligations=1@0.65; joined_by=alternatives@0.85; term=none@0.70; check=unit test@0.49
    - pass: obligations=1@0.64; joined_by=alternatives@0.89; term=none@0.69; check=unit test@0.52
- s2: "A request about a record MUST carry, in its state next to the record, only\nthe definitions attached to that record alone, plus those attached to\nthat record and the request's location."
    - pass: obligations=1@0.41; joined_by=and-list@0.30; term=none@0.64; check=unit test@0.92
    - pass: obligations=1@0.40; joined_by=and-list@0.24; term=none@0.57; check=unit test@0.90
    - pass: obligations=1@0.41; joined_by=and-list@0.21; term=none@0.59; check=unit test@0.90
- s3: 'A request with no matching definition MUST be identical to the request\nsent without definitions.'
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.95; term=none@0.49; check=unit test@0.90
    - pass: obligations=1@0.96; joined_by=condition+obligation@0.95; term=none@0.45; check=unit test@0.84
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.96; term=none@0.44; check=unit test@0.86
- s4: '`judge-jev` MUST refuse, before sending, a request whose definitions take\nit over the size limit.'
    - pass: obligations=1@0.83; joined_by=condition+obligation@0.95; term=none@0.70; check=unit test@0.49
    - pass: obligations=1@0.75; joined_by=condition+obligation@0.95; term=none@0.74; check=unit test@0.50
    - pass: obligations=1@0.81; joined_by=condition+obligation@0.94; term=none@0.71; check=unit test@0.59
- s5: "Every request's log event MUST record the digest of each definition it\ncarried."
    - pass: obligations=1@0.77; joined_by=none@0.85; term=none@0.57; check=inspection or grep@0.34
    - pass: obligations=1@0.71; joined_by=none@0.84; term=none@0.54; check=unit test@0.41
    - pass: obligations=1@0.67; joined_by=none@0.84; term=none@0.54; check=inspection or grep@0.37
- s6: '`judge-jev` MUST NOT truncate a definition.'
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.69; check=unit test@0.60
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.57; check=unit test@0.61
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.60; check=unit test@0.66


======== REQ-JEV-0213 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0213: A definition is kept only when it changes an answer

**Status:** Draft  

### Requirement Statement

Definitions: A definition is a term with its meaning, attached to a record
(ADR-JEV-0008); a candidate definition is one being tested. The comparison
is `judge-jev compare-definition`. The requests a candidate would reach are
the requests about the records it is attached to. An answer is Jev's choice
for one question, with its confidence from 0 to 1. The decision threshold is
0.6 unless `--threshold` sets it; a confidence at or above it decides.

**MUST statements:**
- `judge-jev` MUST provide a comparison of one or more candidate
  definitions.
- The comparison MUST run the requests the candidate definitions would
  reach with the candidates.
- The comparison MUST run the same requests without the candidates.
- The comparison MUST report each answer's choice with and without the
  candidates.
- The comparison MUST report each answer's confidence with and without the
  candidates.
- The comparison MUST report the candidates as material when an answer's
  choice flips or its confidence crosses the decision threshold, and as not
  material when every change stays on the same side of the threshold.
- The comparison MUST record the threshold it applied.

### Rationale

Rand Lee, 2026-11-08: "if adding the definition does not impact the scores
used in the rubric, they aren't necessary to add"; "Moving from 90->95
confidence doesn't matter. A change from 20%->50% would be material if
other changes get it over the threshold."

### Success Criteria

**Acceptance Criteria:**
- [ ] With fixture answers where the definition flips one answer, the
  comparison reports it as material.
- [ ] With fixture answers that are the same with and without the
  definition, the comparison reports it as not material.
- [ ] A confidence move from 0.90 to 0.95 on the same side of the threshold
  is not material. Two candidates that each move an answer part of the way,
  and together across the threshold, are material when compared together.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0213: A definition is kept only when it changes an answer

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev` MUST provide a comparison of one or more candidate
  definitions.
- The comparison MUST run the requests the candidate definitions would
  reach with the candidates.
- The comparison MUST run the same requests without the candidates.
- The comparison MUST report each answer's choice with and without the
  candidates.
- The comparison MUST report each answer's confidence with and without the
  candidates.
- The comparison MUST report the candidates as material when an answer's
  choice flips or its confidence crosses the decision threshold, and as not
  material when every change stays on the same side of the threshold.
- The comparison MUST record the threshold it applied.

### Rationale

Rand Lee, 2026-11-08: "if adding the definition does not impact the scores
used in the rubric, they aren't necessary to add"; "Moving from 90->95
confidence doesn't matter. A change from 20%->50% would be material if
other changes get it over the threshold."

### Success Criteria

**Acceptance Criteria:**
- [ ] With fixture answers where the definition flips one answer, the
  comparison reports it as material.
- [ ] With fixture answers that are the same with and without the
  definition, the comparison reports it as not material.
- [ ] A confidence move from 0.90 to 0.95 on the same side of the threshold
  is not material. Two candidates that each move an answer part of the way,
  and together across the threshold, are material when compared together.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: '`judge-jev` MUST provide a comparison of one or more candidate\ndefinitions.'
    - pass: obligations=1@0.91; joined_by=none@0.77; term=none@0.66; check=CLI run@0.77
    - pass: obligations=1@0.91; joined_by=none@0.79; term=none@0.66; check=CLI run@0.79
    - pass: obligations=1@0.92; joined_by=none@0.75; term=none@0.62; check=CLI run@0.75
- s2: 'The comparison MUST run the requests the candidate definitions would\nreach with the candidates.'
    - pass: obligations=1@0.96; joined_by=none@0.85; term=none@0.80; check=CLI run@0.47
    - pass: obligations=1@0.95; joined_by=none@0.87; term=none@0.81; check=CLI run@0.45
    - pass: obligations=1@0.95; joined_by=none@0.89; term=none@0.85; check=CLI run@0.47
- s3: 'The comparison MUST run the same requests without the candidates.'
    - pass: obligations=1@0.93; joined_by=none@0.90; term=none@0.87; check=CLI run@0.54
    - pass: obligations=1@0.92; joined_by=none@0.90; term=none@0.85; check=CLI run@0.50
    - pass: obligations=1@0.91; joined_by=none@0.91; term=none@0.82; check=CLI run@0.60
- s4: "The comparison MUST report each answer's choice with and without the\ncandidates."
    - pass: obligations=1@0.56; joined_by=none@0.44; term=none@0.76; check=CLI run@0.69
    - pass: obligations=1@0.53; joined_by=none@0.42; term=none@0.80; check=CLI run@0.70
    - pass: obligations=1@0.56; joined_by=none@0.42; term=none@0.85; check=CLI run@0.74
- s5: "The comparison MUST report each answer's confidence with and without the\ncandidates."
    - pass: obligations=1@0.55; joined_by=none@0.62; term=none@0.90; check=CLI run@0.71
    - pass: obligations=1@0.69; joined_by=none@0.55; term=none@0.89; check=CLI run@0.76
    - pass: obligations=1@0.56; joined_by=none@0.46; term=none@0.90; check=CLI run@0.74
- s6: "The comparison MUST report the candidates as material when an answer's\nchoice flips or its confidence crosses the decision threshold, and as not\nmaterial when every change stays on the same side of the threshold."
    - pass: obligations=2@0.72; joined_by=condition+obligation@0.76; term=none@0.65; check=CLI run@0.45
    - pass: obligations=2@0.57; joined_by=condition+obligation@0.76; term=none@0.66; check=CLI run@0.52
    - pass: obligations=2@0.65; joined_by=condition+obligation@0.79; term=none@0.65; check=CLI run@0.46
- s7: 'The comparison MUST record the threshold it applied.'
    - pass: obligations=1@0.95; joined_by=none@0.96; term=none@0.82; check=CLI run@0.30
    - pass: obligations=1@0.92; joined_by=none@0.96; term=none@0.81; check=CLI run@0.39
    - pass: obligations=1@0.95; joined_by=none@0.95; term=none@0.82; check=CLI run@0.36


======== REQ-JEV-0214 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0214: Question ids are unique within a scope

**Status:** Draft  

### Requirement Statement

Definitions: A question IRI (Internationalized Resource Identifier) is the
URN that names a question, such as `urn:judge-jev:question:req.term`. A tree
file is a Turtle file of quality decision trees. A consumer extension is a
tree file that a repository using judge-jev adds. `jj:id` is a question's
short id within its tree.

**MUST statements:**
- Every question IRI in one scope (by default the repository) MUST be
  declared in one tree file only, across judge-jev's trees and every
  consumer extension's.
- Every `jj:id` in judge-jev's trees and in every consumer extension's
  MUST be unique within its tree.

### Rationale

A question's identity is its IRI.

Rand Lee, 2026-11-08: "We would need to make sure all questions in
judge-jev AND in consumer extensions follow a naming policy for uniqueness
w/in that scope (repo is typical scope)."

### Success Criteria

**Acceptance Criteria:**
- [ ] A question IRI declared in two tree files of one scope is reported
  as an error naming both files; two questions of one tree with the same
  `jj:id` are an error.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0214: Question ids are unique within a scope

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- Every question IRI in one scope (by default the repository) MUST be
  declared in one tree file only, across judge-jev's trees and every
  consumer extension's.
- Every `jj:id` in judge-jev's trees and in every consumer extension's
  MUST be unique within its tree.

### Rationale

A question's identity is its IRI.

Rand Lee, 2026-11-08: "We would need to make sure all questions in
judge-jev AND in consumer extensions follow a naming policy for uniqueness
w/in that scope (repo is typical scope)."

### Success Criteria

**Acceptance Criteria:**
- [ ] A question IRI declared in two tree files of one scope is reported
  as an error naming both files; two questions of one tree with the same
  `jj:id` are an error.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: "Every question IRI in one scope (by default the repository) MUST be\ndeclared in one tree file only, across judge-jev's trees and every\nconsumer extension's."
    - pass: obligations=1@0.89; joined_by=none@0.70; term=none@0.49; check=inspection or grep@0.22
    - pass: obligations=1@0.84; joined_by=none@0.77; term=none@0.39; check=inspection or grep@0.29
    - pass: obligations=1@0.89; joined_by=none@0.73; term=none@0.52; check=inspection or grep@0.24
- s2: "Every `jj:id` in judge-jev's trees and in every consumer extension's\nMUST be unique within its tree."
    - pass: obligations=1@0.75; joined_by=none@0.37; term=none@0.70; check=unit test@0.26
    - pass: obligations=1@0.68; joined_by=none@0.37; term=none@0.62; check=unit test@0.25
    - pass: obligations=1@0.60; joined_by=none@0.39; term=none@0.66; check=unit test@0.22


======== REQ-JEV-0215 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0215: Doctor command

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. The scope is the trees and question
sets shipped with judge-jev, the tree and definitions files at the top level
of `.sc/judge-jev/`, and each path given to `judge-jev doctor`. A tree is a
quality decision tree file; a question set is a file of questions; a
definitions file is a `.definitions.ttl` file of definitions, each a term
with its meaning and the `source` file it comes from. A file's schema is the
model that checks its fields. The ontology's shapes are the SHACL (Shapes
Constraint Language) files in `assets/shapes/`; an edge is a link from one
node of a tree to another, and a cycle is a chain of edges that leads back
to its start. An attachment links a definition to a record, or to a record
and a location (a file, Markdown section or code symbol). The Raptor index
is the record file Raptor's import writes.

**MUST statements:**
- `judge-jev doctor` MUST validate every tree in the scope against its
  schema.
- `judge-jev doctor` MUST validate every question set in the scope against
  its schema.
- `judge-jev doctor` MUST validate every definitions file in the scope
  against its schema.
- `judge-jev doctor` MUST validate every tree, question set and definitions
  file in the scope against the ontology's shapes, including edges and
  cycles.
- `judge-jev doctor` MUST report each validation failure as an error.
- `judge-jev doctor` MUST report a definition with no attachment as a
  warning.
- `judge-jev doctor` MUST report an attachment to a record the Raptor index
  does not hold as a warning.
- `judge-jev doctor` MUST report an attachment to a location that does not
  exist as a warning.
- `judge-jev doctor` MUST report a definition whose source does not exist
  as a warning.

**MUST NOT statements:**
- `judge-jev doctor` MUST NOT call Jev.
- A `judge-jev doctor` warning MUST NOT fail the command.

### Rationale

Rand Lee, 2026-11-08: "I would expect judge-jev doctor to report orphans/dead
links as warnings, it would also run schema validation and verify ontology
followed and no cycles."

### Success Criteria

**Acceptance Criteria:**
- [ ] A scope with one orphan definition exits 0 with one warning naming it.
- [ ] A scope with a tree that has a cycle exits non-zero with an error
  naming the cycle.

```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0215: Doctor command

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev doctor` MUST validate every tree in the scope against its
  schema.
- `judge-jev doctor` MUST validate every question set in the scope against
  its schema.
- `judge-jev doctor` MUST validate every definitions file in the scope
  against its schema.
- `judge-jev doctor` MUST validate every tree, question set and definitions
  file in the scope against the ontology's shapes, including edges and
  cycles.
- `judge-jev doctor` MUST report each validation failure as an error.
- `judge-jev doctor` MUST report a definition with no attachment as a
  warning.
- `judge-jev doctor` MUST report an attachment to a record the Raptor index
  does not hold as a warning.
- `judge-jev doctor` MUST report an attachment to a location that does not
  exist as a warning.
- `judge-jev doctor` MUST report a definition whose source does not exist
  as a warning.

**MUST NOT statements:**
- `judge-jev doctor` MUST NOT call Jev.
- A `judge-jev doctor` warning MUST NOT fail the command.

### Rationale

Rand Lee, 2026-11-08: "I would expect judge-jev doctor to report orphans/dead
links as warnings, it would also run schema validation and verify ontology
followed and no cycles."

### Success Criteria

**Acceptance Criteria:**
- [ ] A scope with one orphan definition exits 0 with one warning naming it.
- [ ] A scope with a tree that has a cycle exits non-zero with an error
  naming the cycle.

```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: '`judge-jev doctor` MUST validate every tree in the scope against its\nschema.'
    - pass: obligations=1@0.96; joined_by=none@0.89; term=none@0.80; check=CLI run@0.85
    - pass: obligations=1@0.95; joined_by=none@0.91; term=none@0.82; check=CLI run@0.84
    - pass: obligations=1@0.95; joined_by=none@0.94; term=none@0.80; check=CLI run@0.84
- s2: '`judge-jev doctor` MUST validate every question set in the scope against\nits schema.'
    - pass: obligations=1@0.99; joined_by=none@0.87; term=none@0.90; check=CLI run@0.73
    - pass: obligations=1@0.99; joined_by=none@0.87; term=none@0.90; check=CLI run@0.74
    - pass: obligations=1@0.97; joined_by=none@0.90; term=none@0.90; check=CLI run@0.71
- s3: '`judge-jev doctor` MUST validate every definitions file in the scope\nagainst its schema.'
    - pass: obligations=1@0.93; joined_by=none@0.96; term=none@0.91; check=CLI run@0.77
    - pass: obligations=1@0.95; joined_by=none@0.95; term=none@0.91; check=CLI run@0.74
    - pass: obligations=1@0.89; joined_by=none@0.96; term=none@0.92; check=CLI run@0.79
- s4: "`judge-jev doctor` MUST validate every tree, question set and definitions\nfile in the scope against the ontology's shapes, including edges and\ncycles."
    - FAIL R1: obligations=3@0.23; joined_by=and-list@0.76; term=none@0.89; check=CLI run@0.84
    - FAIL R1: obligations=3@0.19; joined_by=and-list@0.75; term=none@0.89; check=CLI run@0.84
    - pass: obligations=1@0.15; joined_by=and-list@0.82; term=none@0.89; check=CLI run@0.86
- s5: '`judge-jev doctor` MUST report each validation failure as an error.'
    - pass: obligations=1@0.97; joined_by=none@0.69; term=none@0.82; check=CLI run@0.89
    - pass: obligations=1@1.00; joined_by=none@0.66; term=none@0.80; check=CLI run@0.91
    - pass: obligations=1@0.99; joined_by=none@0.66; term=none@0.85; check=CLI run@0.92
- s6: '`judge-jev doctor` MUST report a definition with no attachment as a\nwarning.'
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.57; term=none@0.89; check=CLI run@0.92
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.55; term=none@0.86; check=CLI run@0.92
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.70; term=none@0.85; check=CLI run@0.94
- s7: '`judge-jev doctor` MUST report an attachment to a record the Raptor index\ndoes not hold as a warning.'
    - pass: obligations=1@0.97; joined_by=none@0.39; term=none@0.85; check=CLI run@0.90
    - pass: obligations=1@0.97; joined_by=none@0.40; term=none@0.87; check=CLI run@0.85
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.42; term=none@0.85; check=CLI run@0.86
- s8: '`judge-jev doctor` MUST report an attachment to a location that does not\nexist as a warning.'
    - pass: obligations=1@0.95; joined_by=none@0.66; term=none@0.89; check=CLI run@0.90
    - pass: obligations=1@0.95; joined_by=none@0.60; term=none@0.89; check=CLI run@0.94
    - pass: obligations=1@0.93; joined_by=none@0.79; term=none@0.85; check=CLI run@0.90
- s9: '`judge-jev doctor` MUST report a definition whose source does not exist\nas a warning.'
    - pass: obligations=1@0.93; joined_by=condition+obligation@0.41; term=none@0.94; check=CLI run@0.92
    - pass: obligations=1@0.89; joined_by=none@0.41; term=none@0.92; check=CLI run@0.91
    - pass: obligations=1@0.87; joined_by=none@0.40; term=none@0.92; check=CLI run@0.92
- s10: '`judge-jev doctor` MUST NOT call Jev.'
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.91; check=unit test@0.29
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.86; check=unit test@0.31
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.89; check=unit test@0.30
- s11: 'A `judge-jev doctor` warning MUST NOT fail the command.'
    - pass: obligations=1@0.99; joined_by=none@0.95; term=none@0.82; check=CLI run@0.95
    - pass: obligations=1@0.99; joined_by=none@0.91; term=none@0.86; check=CLI run@0.96
    - pass: obligations=1@0.99; joined_by=none@0.98; term=none@0.75; check=CLI run@0.95
