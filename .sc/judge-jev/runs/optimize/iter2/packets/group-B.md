# Packet group B (iteration 2)


======== REQ-JEV-0201 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0201: One record per check

**Status:** Draft  

### Requirement Statement

Definitions: A record is one requirement (REQ), non-functional requirement
(NFR) or architecture decision record (ADR) REQ, NFR and ADR are its record
kinds. A location is the text judged against a record: a whole file
(`path`), a Markdown section (`path#Heading`) or a code symbol
(`path::Symbol`) (REQ-JEV-0207). A question set is the data file of
questions judge-jev sends to Jev about a location for one record kind and
target class. `--profile` names a profile: a TOML file listing locations to
check (REQ-JEV-0204).

**MUST statements:**
- `judge-jev check` MUST take one of two argument forms: a single record
  with a location and a mode, or a `--profile`.
- In the single-record form, `judge-jev check` MUST take one record id,
  given with exactly one record-kind flag: `--req` (requirement), `--adr`
  (architecture decision record) or `--nfr` (non-functional requirement).
- In the single-record form, `judge-jev check` MUST take exactly one
  `--location`.
- In the single-record form, `judge-jev check` MUST take exactly one
  `--mode`.
- Each record kind MUST use its own question set.

### Rationale

A requirement, a decision and a non-functional requirement are each
violated in a different way.

### Success Criteria

**Acceptance Criteria:**
- [ ] The same location checked with `--req` and with `--adr` sends
  different question sets.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0201: One record per check

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev check` MUST take one of two argument forms: a single record
  with a location and a mode, or a `--profile`.
- In the single-record form, `judge-jev check` MUST take one record id,
  given with exactly one record-kind flag: `--req` (requirement), `--adr`
  (architecture decision record) or `--nfr` (non-functional requirement).
- In the single-record form, `judge-jev check` MUST take exactly one
  `--location`.
- In the single-record form, `judge-jev check` MUST take exactly one
  `--mode`.
- Each record kind MUST use its own question set.

### Rationale

A requirement, a decision and a non-functional requirement are each
violated in a different way.

### Success Criteria

**Acceptance Criteria:**
- [ ] The same location checked with `--req` and with `--adr` sends
  different question sets.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: '`judge-jev check` MUST take one of two argument forms: a single record\nwith a location and a mode, or a `--profile`.'
    - pass: obligations=1@0.45; joined_by=alternatives@0.96; term=none@0.55; check=CLI run@0.89
    - pass: obligations=1@0.47; joined_by=alternatives@0.95; term=none@0.56; check=CLI run@0.86
    - pass: obligations=1@0.44; joined_by=alternatives@0.96; term=none@0.49; check=CLI run@0.87
- s2: 'In the single-record form, `judge-jev check` MUST take one record id,\ngiven with exactly one record-kind flag: `--req` (requirement), `--adr`\n(architecture decision record) or `--nfr` (non-functional requirement).'
    - pass: obligations=3@0.28; joined_by=condition+obligation@0.26; term=none@0.69; check=CLI run@0.87
    - pass: obligations=3@0.29; joined_by=condition+obligation@0.34; term=none@0.68; check=CLI run@0.86
    - pass: obligations=3@0.23; joined_by=condition+obligation@0.18; term=none@0.70; check=CLI run@0.87
- s3: 'In the single-record form, `judge-jev check` MUST take exactly one\n`--location`.'
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.68; term=none@0.80; check=CLI run@0.91
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.70; term=none@0.77; check=CLI run@0.89
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.59; term=none@0.77; check=CLI run@0.86
- s4: 'In the single-record form, `judge-jev check` MUST take exactly one\n`--mode`.'
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.52; term=none@0.70; check=CLI run@0.82
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.52; term=none@0.65; check=CLI run@0.85
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.51; term=none@0.69; check=CLI run@0.87
- s5: 'Each record kind MUST use its own question set.'
    - pass: obligations=1@0.80; joined_by=none@0.92; term=none@0.71; check=CLI run@0.37
    - pass: obligations=1@0.65; joined_by=none@0.96; term=none@0.75; check=CLI run@0.35
    - pass: obligations=1@0.67; joined_by=none@0.98; term=none@0.76; check=CLI run@0.37


======== REQ-JEV-0202 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0202: One record and one location per request

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model. A record is one
requirement (REQ), non-functional requirement (NFR) or architecture decision
record (ADR) REQ, NFR and ADR are its record kinds. A location is the text
judged against a record (REQ-JEV-0207). A stream of single requests is a
sequence of Jev requests, one per pair (REQ-JEV-0002).

**MUST statements:**
- Each Jev request MUST carry exactly one record.
- Each Jev request MUST carry exactly one location.
- A run over many pairs MUST send them as a stream of single requests.

### Rationale

Jev judges one record and location at a time; packing records into one
request hides which one failed. Batching is streaming single requests, which
the batch command already does.

### Success Criteria

**Acceptance Criteria:**
- [ ] A profile mapping one file to three records sends three requests.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0202: One record and one location per request

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- Each Jev request MUST carry exactly one record.
- Each Jev request MUST carry exactly one location.
- A run over many pairs MUST send them as a stream of single requests.

### Rationale

Jev judges one record and location at a time; packing records into one request hides
which one failed. Batching is streaming single requests, which the batch
command already does.

### Success Criteria

**Acceptance Criteria:**
- [ ] A profile mapping one file to three records sends three requests.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'Each Jev request MUST carry exactly one record.'
    - pass: obligations=1@0.95; joined_by=none@0.94; term=none@0.57; check=unit test@0.69
    - pass: obligations=1@0.95; joined_by=none@0.96; term=none@0.60; check=unit test@0.66
    - pass: obligations=1@0.92; joined_by=none@0.91; term=none@0.56; check=unit test@0.65
- s2: 'Each Jev request MUST carry exactly one location.'
    - pass: obligations=1@0.89; joined_by=none@0.95; term=none@0.64; check=unit test@0.75
    - pass: obligations=1@0.85; joined_by=none@0.95; term=none@0.60; check=unit test@0.71
    - pass: obligations=1@0.84; joined_by=none@0.95; term=none@0.73; check=unit test@0.76
- s3: 'A run over many pairs MUST send them as a stream of single requests.'
    - pass: obligations=1@0.88; joined_by=condition+obligation@0.70; term=none@0.44; check=unit test@0.30
    - pass: obligations=1@0.84; joined_by=condition+obligation@0.70; term=none@0.34; check=unit test@0.31
    - pass: obligations=1@0.91; joined_by=condition+obligation@0.73; term=none@0.51; check=unit test@0.35


======== REQ-JEV-0203 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0203: Target modes

**Status:** Draft  

### Requirement Statement

Definitions: A mode (target mode) names what a location holds: `prompt`
`skill`, `task` or `code`. A location is the text judged against a record
(REQ-JEV-0207). sc-compose is the template renderer. sc-agent is the agent
tool that defines the tree-sitter grammars (ADR-JEV-0004).

**MUST statements:**
- judge-jev MUST support the target mode `prompt`.
- judge-jev MUST support the target mode `skill`.
- judge-jev MUST support the target mode `task`.
- judge-jev MUST support the target mode `code`.
- In `task` mode judge-jev MUST judge the raw template.
- In `task` mode judge-jev MUST judge an assignment rendered by sc-compose
  in strict mode from the vars file that `--vars` names, or, in a profile
  run, that the profile names.
- In `code` mode judge-jev MUST resolve the location with the tree-sitter
  grammars sc-agent defines.

**MUST NOT statements:**
- judge-jev MUST NOT define its own tree-sitter grammars.

### Rationale

The raw template shows which variables are substituted; a rendered
assignment shows what an agent actually receives. Strict rendering fails on
a missing variable instead of judging a half-rendered assignment. sc-agent
owns the grammars so every consumer selects code the same way.

### Success Criteria

**Acceptance Criteria:**
- [ ] A task template checked in `task` mode produces one result for the
  raw template and one for its rendered assignment.
- [ ] A vars file missing a template variable fails the render with the
  variable named.
- [ ] The repository contains no tree-sitter grammar definitions.

### Implementation Notes

`code` mode waits for sc-agent's tree-sitter grammars (ADR-JEV-0004).

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0203: Target modes

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- judge-jev MUST support the target mode `prompt`.
- judge-jev MUST support the target mode `skill`.
- judge-jev MUST support the target mode `task`.
- judge-jev MUST support the target mode `code`.
- In `task` mode judge-jev MUST judge the raw template.
- In `task` mode judge-jev MUST judge an assignment rendered by sc-compose
  in strict mode from the vars file that `--vars` names, or, in a profile
  run, that the profile names.
- In `code` mode judge-jev MUST resolve the location with the tree-sitter
  grammars sc-agent defines.

**MUST NOT statements:**
- judge-jev MUST NOT define its own tree-sitter grammars.

### Rationale

The raw template shows which variables are substituted; a rendered
assignment shows what an agent actually receives. Strict rendering fails on
a missing variable instead of judging a half-rendered assignment. sc-agent
owns the grammars so every consumer selects code the same way.

### Success Criteria

**Acceptance Criteria:**
- [ ] A task template checked in `task` mode produces one result for the
  raw template and one for its rendered assignment.
- [ ] A vars file missing a template variable fails the render with the
  variable named.
- [ ] The repository contains no tree-sitter grammar definitions.

### Implementation Notes

`code` mode waits for sc-agent's tree-sitter grammars (ADR-JEV-0004).

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'judge-jev MUST support the target mode `prompt`.'
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.68; check=CLI run@0.47
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.70; check=CLI run@0.59
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.74; check=CLI run@0.52
- s2: 'judge-jev MUST support the target mode `skill`.'
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.82; check=CLI run@0.54
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.81; check=CLI run@0.54
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.82; check=CLI run@0.55
- s3: 'judge-jev MUST support the target mode `task`.'
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.71; check=CLI run@0.59
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.80; check=CLI run@0.57
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.80; check=CLI run@0.55
- s4: 'judge-jev MUST support the target mode `code`.'
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.84; check=CLI run@0.44
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.85; check=CLI run@0.44
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.84; check=CLI run@0.50
- s5: 'In `task` mode judge-jev MUST judge the raw template.'
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.69; term=none@0.61; check=CLI run@0.66
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.68; term=none@0.66; check=CLI run@0.60
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.64; term=none@0.68; check=CLI run@0.66
- s6: 'In `task` mode judge-jev MUST judge an assignment rendered by sc-compose\nin strict mode from the vars file that `--vars` names, or, in a profile\nrun, that the profile names.'
    - pass: obligations=1@0.40; joined_by=condition+obligation@0.44; term=none@0.40; check=CLI run@0.71
    - pass: obligations=1@0.47; joined_by=condition+obligation@0.36; term=none@0.37; check=CLI run@0.75
    - pass: obligations=1@0.40; joined_by=condition+obligation@0.52; term=none@0.37; check=CLI run@0.75
- s7: 'In `code` mode judge-jev MUST resolve the location with the tree-sitter\ngrammars sc-agent defines.'
    - pass: obligations=1@0.93; joined_by=condition+obligation@0.85; term=none@0.68; check=CLI run@0.29
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.80; term=none@0.68; check=inspection or grep@0.19
    - pass: obligations=1@0.92; joined_by=condition+obligation@0.85; term=none@0.71; check=CLI run@0.22
- s8: 'judge-jev MUST NOT define its own tree-sitter grammars.'
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.65; check=inspection or grep@1.00
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.66; check=inspection or grep@1.00
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.60; check=inspection or grep@1.00


======== REQ-JEV-0204 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0204: Profiles map locations to records

**Status:** Draft  

### Requirement Statement

Definitions: TOML is Tom's Obvious Minimal Language. A profile is a TOML
file listing locations, each with its mode and the ids of the records that
govern it. A location is the text judged against a record.

**MUST statements:**
- judge-jev MUST read a TOML profile listing locations, each with its
  mode, the record ids that govern it, and for `task` mode a vars file.
- `judge-jev check --profile <profile>` MUST check every listed pair.
- `judge-jev check --profile <profile>` MUST report each pair's verdict.
- `judge-jev check --profile <profile>` MUST aggregate the verdicts per
  record.
- `judge-jev check --profile <profile>` MUST aggregate the verdicts per
  location.

**MUST NOT statements:**
- A profile run MUST NOT judge a pair the profile does not list.

### Rationale

The profile states which records govern which locations, so a run checks
exactly those pairs. A record id carries its kind, so one profile holds
all kinds.

### Success Criteria

**Acceptance Criteria:**
- [ ] A run over a profile produces one result per (record, location)
  pair and none for unlisted pairs.
- [ ] The report states, per record, whether it is met at every listed
  location, and names the failing locations.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0204: Profiles map locations to records

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- judge-jev MUST read a TOML profile listing locations, each with its
  mode, the record ids that govern it, and for `task` mode a vars file.
- `judge-jev check --profile <profile>` MUST check every listed pair.
- `judge-jev check --profile <profile>` MUST report each pair's verdict.
- `judge-jev check --profile <profile>` MUST aggregate the verdicts per
  record.
- `judge-jev check --profile <profile>` MUST aggregate the verdicts per
  location.

**MUST NOT statements:**
- A profile run MUST NOT judge a pair the profile does not list.

### Rationale

The profile states which records govern which locations, so a run checks
exactly those pairs. A record id carries its kind, so one profile holds
all kinds.

### Success Criteria

**Acceptance Criteria:**
- [ ] A run over a profile produces one result per (record, location)
  pair and none for unlisted pairs.
- [ ] The report states, per record, whether it is met at every listed
  location, and names the failing locations.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'judge-jev MUST read a TOML profile listing locations, each with its\nmode, the record ids that govern it, and for `task` mode a vars file.'
    - pass: obligations=1@0.40; joined_by=and-list@0.37; term=none@0.60; check=CLI run@0.61
    - pass: obligations=1@0.36; joined_by=and-list@0.45; term=none@0.52; check=CLI run@0.69
    - pass: obligations=1@0.37; joined_by=and-list@0.49; term=none@0.47; check=CLI run@0.65
- s2: '`judge-jev check --profile <profile>` MUST check every listed pair.'
    - pass: obligations=1@0.96; joined_by=none@0.91; term=none@0.75; check=CLI run@0.74
    - pass: obligations=1@0.95; joined_by=none@0.85; term=none@0.73; check=CLI run@0.75
    - pass: obligations=1@0.97; joined_by=none@0.89; term=none@0.70; check=CLI run@0.71
- s3: "`judge-jev check --profile <profile>` MUST report each pair's verdict."
    - pass: obligations=1@0.96; joined_by=none@0.80; term=none@0.65; check=CLI run@0.92
    - pass: obligations=1@0.97; joined_by=none@0.85; term=none@0.57; check=CLI run@0.94
    - pass: obligations=1@0.97; joined_by=none@0.84; term=none@0.66; check=CLI run@0.94
- s4: '`judge-jev check --profile <profile>` MUST aggregate the verdicts per\nrecord.'
    - pass: obligations=1@0.97; joined_by=none@0.92; term=none@0.57; check=CLI run@0.80
    - pass: obligations=1@0.97; joined_by=none@0.91; term=none@0.55; check=CLI run@0.81
    - pass: obligations=1@0.97; joined_by=none@0.92; term=none@0.59; check=CLI run@0.81
- s5: '`judge-jev check --profile <profile>` MUST aggregate the verdicts per\nlocation.'
    - pass: obligations=1@0.97; joined_by=none@0.90; term=none@0.61; check=CLI run@0.85
    - pass: obligations=1@0.97; joined_by=none@0.87; term=none@0.65; check=CLI run@0.81
    - pass: obligations=1@0.96; joined_by=none@0.90; term=none@0.61; check=CLI run@0.82
- s6: 'A profile run MUST NOT judge a pair the profile does not list.'
    - pass: obligations=1@1.00; joined_by=none@0.66; term=none@0.82; check=CLI run@0.64
    - pass: obligations=1@0.99; joined_by=none@0.62; term=none@0.81; check=CLI run@0.61
    - pass: obligations=1@1.00; joined_by=none@0.71; term=none@0.79; check=CLI run@0.61


======== REQ-JEV-0205 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0205: Question sets ship with the tool

**Status:** Draft  

### Requirement Statement

Definitions: A record is one requirement (REQ), non-functional requirement
(NFR) or architecture decision record (ADR); REQ, NFR and ADR are its record
kinds. A question set is the data file of questions judge-jev sends to Jev
about a location for one record kind and target class. A target class is
agent text (modes `prompt`, `skill` and `task`) or code (mode `code`). A
quality decision tree is the data file of questions that judges whether a
record is well written; see REQ-JEV-0101. A question-set id is the `id`
field of a question set or tree file. The content digest of a file is the
SHA-256 of its bytes. An override file is a file given with `--questions`
that replaces the shipped question set or quality decision tree for that
run. The released tool is the installed judge-jev release. A log entry is
one event a run writes (REQ-JEV-0008).

**MUST statements:**
- judge-jev MUST ship one question set per combination of record kind and
  target class.
- judge-jev MUST ship one quality decision tree per record kind.
- Every shipped question and prompt text MUST be approved by Rand before
  it ships.
- Question sets MUST be data files shipped with the tool.
- Quality decision trees MUST be data files shipped with the tool.
- The released tool MUST accept, with `--questions <file>`, an override file
  for any question set.
- The released tool MUST accept an override file for any quality decision
  tree.
- Every result MUST carry the question-set id.
- Every result MUST carry the content digest of the file used.
- Every log entry MUST carry the question-set id.
- Every log entry MUST carry the content digest of the file used.

### Rationale

Rand: "I do not trust non-frontier agents to write prompts. I do not even
trust frontier agents to write them." The question sets are the tool's
system prompts. Getting them production-worthy means running thousands of
question variations against the released tool; a variation that needs a
code change cannot be run at that scale.

Because question sets and trees are data files, changing a question, a
tree branch or a wave needs no code change. An override file lets a
variation be tried by writing a file, never by changing or rebuilding code.
The question-set id and file digest on every result and log entry let
results from many variations of the same set be told apart and compared.

### Success Criteria

**Acceptance Criteria:**
- [ ] Each shipped question file names the approval that admitted its text.
- [ ] A result produced with an override names the override file and its
  digest.
- [ ] Two override files differing in one question produce results with
  different digests, run on the same released build.
- [ ] Adding a wave to a quality tree changes only the tree file.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0205: Question sets ship with the tool

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- judge-jev MUST ship one question set per combination of record kind and
  target class (agent text or code).
- judge-jev MUST ship one quality decision tree per record kind.
- Every shipped question and prompt text MUST be approved by Rand before
  it ships.
- Question sets MUST be data files shipped with the tool.
- Quality decision trees MUST be data files shipped with the tool.
- The released tool MUST accept an override file for any question set.
- The released tool MUST accept an override file for any quality decision
  tree.
- Every result MUST carry the question-set id.
- Every result MUST carry the content digest of the file used.
- Every log entry MUST carry the question-set id.
- Every log entry MUST carry the content digest of the file used.

### Rationale

Rand: "I do not trust non-frontier agents to write prompts. I do not even
trust frontier agents to write them." The question sets are the tool's
system prompts. Getting them production-worthy means running thousands of
question variations against the released tool; a variation that needs a
code change cannot be run at that scale.

Because question sets and trees are data files, changing a question, a
tree branch or a wave needs no code change. An override file lets a
variation be tried by writing a file, never by changing or rebuilding code.
The question-set id and file digest on every result and log entry let
results from many variations of the same set be told apart and compared.

### Success Criteria

**Acceptance Criteria:**
- [ ] Each shipped question file names the approval that admitted its text.
- [ ] A result produced with an override names the override file and its
  digest.
- [ ] Two override files differing in one question produce results with
  different digests, run on the same released build.
- [ ] Adding a wave to a quality tree changes only the tree file.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'judge-jev MUST ship one question set per combination of record kind and\ntarget class.'
    - pass: obligations=1@0.85; joined_by=none@0.95; term=none@0.73; check=inspection or grep@0.87
    - pass: obligations=1@0.79; joined_by=none@0.95; term=none@0.68; check=inspection or grep@0.85
    - pass: obligations=1@0.76; joined_by=none@0.98; term=none@0.71; check=inspection or grep@0.81
- s2: 'judge-jev MUST ship one quality decision tree per record kind.'
    - pass: obligations=1@0.95; joined_by=none@0.99; term=none@0.55; check=inspection or grep@0.86
    - pass: obligations=1@0.95; joined_by=none@0.99; term=none@0.64; check=inspection or grep@0.85
    - pass: obligations=1@0.96; joined_by=none@0.99; term=none@0.61; check=inspection or grep@0.89
- s3: 'Every shipped question and prompt text MUST be approved by Rand before\nit ships.'
    - pass: obligations=1@0.76; joined_by=none@0.66; term=none@0.40; check=inspection or grep@0.87
    - pass: obligations=1@0.69; joined_by=none@0.65; term=none@0.47; check=inspection or grep@0.87
    - pass: obligations=1@0.72; joined_by=none@0.59; term=none@0.41; check=inspection or grep@0.89
- s4: 'Question sets MUST be data files shipped with the tool.'
    - pass: obligations=1@0.63; joined_by=none@0.95; term=none@0.84; check=inspection or grep@0.86
    - pass: obligations=1@0.80; joined_by=none@0.94; term=none@0.87; check=inspection or grep@0.82
    - pass: obligations=1@0.64; joined_by=none@0.91; term=none@0.87; check=inspection or grep@0.84
- s5: 'Quality decision trees MUST be data files shipped with the tool.'
    - pass: obligations=1@0.79; joined_by=none@0.96; term=none@0.87; check=inspection or grep@0.85
    - pass: obligations=1@0.85; joined_by=none@0.98; term=none@0.89; check=inspection or grep@0.85
    - pass: obligations=1@0.81; joined_by=none@0.96; term=none@0.86; check=inspection or grep@0.84
- s6: 'The released tool MUST accept, with `--questions <file>`, an override file\nfor any question set.'
    - pass: obligations=1@0.76; joined_by=none@0.64; term=none@0.89; check=CLI run@0.94
    - pass: obligations=1@0.73; joined_by=none@0.68; term=none@0.87; check=CLI run@0.94
    - pass: obligations=1@0.77; joined_by=none@0.65; term=none@0.92; check=CLI run@0.94
- s7: 'The released tool MUST accept an override file for any quality decision\ntree.'
    - pass: obligations=1@0.89; joined_by=none@0.92; term=none@0.94; check=CLI run@0.91
    - pass: obligations=1@0.96; joined_by=none@0.94; term=none@0.90; check=CLI run@0.90
    - pass: obligations=1@0.91; joined_by=none@0.91; term=none@0.90; check=CLI run@0.91
- s8: 'Every result MUST carry the question-set id.'
    - pass: obligations=1@0.99; joined_by=none@0.96; term=none@0.65; check=inspection or grep@0.44
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.62; check=inspection or grep@0.46
    - pass: obligations=1@0.99; joined_by=none@0.96; term=none@0.70; check=inspection or grep@0.44
- s9: 'Every result MUST carry the content digest of the file used.'
    - pass: obligations=1@0.97; joined_by=none@0.96; term=none@0.71; check=inspection or grep@0.36
    - pass: obligations=1@0.96; joined_by=none@0.95; term=none@0.71; check=inspection or grep@0.41
    - pass: obligations=1@0.99; joined_by=none@0.91; term=none@0.68; check=inspection or grep@0.42
- s10: 'Every log entry MUST carry the question-set id.'
    - pass: obligations=1@0.99; joined_by=none@0.98; term=none@0.82; check=inspection or grep@0.59
    - pass: obligations=1@0.99; joined_by=none@0.98; term=none@0.86; check=inspection or grep@0.62
    - pass: obligations=1@0.99; joined_by=none@0.96; term=none@0.77; check=inspection or grep@0.62
- s11: 'Every log entry MUST carry the content digest of the file used.'
    - pass: obligations=1@0.99; joined_by=none@0.96; term=none@0.75; check=inspection or grep@0.56
    - pass: obligations=1@0.99; joined_by=none@0.96; term=none@0.74; check=inspection or grep@0.61
    - pass: obligations=1@0.96; joined_by=none@0.92; term=none@0.66; check=inspection or grep@0.59


======== REQ-JEV-0206 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0206: One judgment per record and location

**Status:** Draft  

### Requirement Statement

Definitions: A judgment is one Jev verdict on one record at one location; a
result is the reported judgment. A location is defined in REQ-JEV-0207; a
pair is one (record, location) pair. A record is one requirement,
non-functional requirement or architecture decision record as Raptor imports
it. A location is the text judged against a record: a whole file (`path`), a
Markdown section (`path#Heading`) or a code symbol (`path::Symbol`)
(REQ-JEV-0207). A pair is one (record, location) pair.

**MUST statements:**
- When a record is satisfied in more than one location, judge-jev MUST
  judge the record separately at each location.
- judge-jev MUST report one result per (record, location) pair.

**MUST NOT statements:**
- judge-jev MUST NOT combine a record's locations into one judgment.

### Rationale

Rand (2026-11-07): "from raptor config standpoint for judge-jev, we must
have single requirements mapped to multiple places in
prompts/skills/agents/code I would expect a separate jev query for each
location it is satisfied. We may be able to fan out a single jev call w/
<location> - <question-1-req-1> | <question-2-req-1> | <question-3-req-2>
| <question-4-req-2> |... depending on how we can fit items in context"
Rand (2026-11-08): "batching is simply streaming of single requests."

### Success Criteria

**Acceptance Criteria:**
- [ ] A record mapped to three locations produces three results, one per
  location.
- [ ] A failure at one location is reported against that location only.

---


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0206: One judgment per record and location

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- When a record is satisfied in more than one location (prompt, skill,
  agent, template or code), judge-jev MUST judge the record separately at
  each location.
- judge-jev MUST report one result per (record, location) pair.

**MUST NOT statements:**
- judge-jev MUST NOT combine a record's locations into one judgment.

### Rationale

Rand (2026-11-07): "from raptor config standpoint for judge-jev, we must
have single requirements mapped to multiple places in
prompts/skills/agents/code I would expect a separate jev query for each
location it is satisfied. We may be able to fan out a single jev call w/
<location> - <question-1-req-1> | <question-2-req-1> | <question-3-req-2>
| <question-4-req-2> | ... depending on how we can fit items in context"
Rand (2026-11-08): "batching is simply streaming of single requests."

### Success Criteria

**Acceptance Criteria:**
- [ ] A record mapped to three locations produces three results, one per
  location.
- [ ] A failure at one location is reported against that location only.

---


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'When a record is satisfied in more than one location, judge-jev MUST\njudge the record separately at each location.'
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.99; term=none@0.68; check=unit test@0.32
    - pass: obligations=1@0.93; joined_by=condition+obligation@0.99; term=none@0.62; check=unit test@0.42
    - pass: obligations=1@0.92; joined_by=condition+obligation@0.99; term=none@0.55; check=unit test@0.39
- s2: 'judge-jev MUST report one result per (record, location) pair.'
    - pass: obligations=1@0.96; joined_by=none@0.95; term=none@0.68; check=unit test@0.35
    - pass: obligations=1@0.96; joined_by=none@0.96; term=none@0.73; check=unit test@0.42
    - pass: obligations=1@0.95; joined_by=none@0.96; term=none@0.71; check=unit test@0.40
- s3: "judge-jev MUST NOT combine a record's locations into one judgment."
    - pass: obligations=1@0.99; joined_by=none@0.98; term=none@0.79; check=unit test@0.31
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.85; check=unit test@0.34
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.81; check=unit test@0.29


======== REQ-JEV-0207 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0207: Location syntax

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool that imports Markdown records.
sc-agent is the agent tool. Tree-sitter grammars are the parsers.

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

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

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

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'A location MUST take one of three forms: `path`, `path#Heading` or\n`path::Symbol`.'
    - pass: obligations=1@0.67; joined_by=alternatives@0.91; term=none@0.60; check=unit test@0.79
    - pass: obligations=1@0.61; joined_by=alternatives@0.94; term=none@0.65; check=unit test@0.79
    - pass: obligations=1@0.57; joined_by=alternatives@0.89; term=none@0.56; check=unit test@0.80
- s2: 'A `path` location MUST select the whole file.'
    - pass: obligations=1@0.99; joined_by=none@0.99; term=none@0.86; check=unit test@0.69
    - pass: obligations=1@0.99; joined_by=none@0.98; term=none@0.84; check=unit test@0.71
    - pass: obligations=1@0.99; joined_by=none@0.99; term=none@0.86; check=unit test@0.76
- s3: 'A `path#Heading` location MUST select a Markdown section, from the\nheading to the next heading of the same or higher level.'
    - pass: obligations=1@0.83; joined_by=none@0.80; term=none@0.64; check=unit test@0.90
    - pass: obligations=1@0.80; joined_by=none@0.85; term=none@0.60; check=unit test@0.89
    - pass: obligations=1@0.85; joined_by=none@0.85; term=none@0.66; check=unit test@0.89
- s4: "A `path::Symbol` location MUST select a code symbol resolved by\nsc-agent's tree-sitter grammars."
    - pass: obligations=1@0.84; joined_by=none@0.91; term=none@0.70; check=unit test@0.75
    - pass: obligations=1@0.88; joined_by=none@0.89; term=none@0.68; check=unit test@0.71
    - pass: obligations=1@0.87; joined_by=none@0.91; term=none@0.64; check=unit test@0.74
- s5: 'Markdown sections MUST be parsed by the same rules Raptor uses.'
    - pass: obligations=1@0.99; joined_by=none@0.99; term=none@0.69; check=unit test@0.77
    - pass: obligations=1@0.97; joined_by=none@0.99; term=none@0.62; check=unit test@0.80
    - pass: obligations=1@0.99; joined_by=none@0.99; term=none@0.65; check=unit test@0.76
- s6: 'A location MUST NOT be a line range.'
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.90; check=unit test@0.69
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.89; check=unit test@0.59
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.89; check=unit test@0.66


======== REQ-JEV-0208 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

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

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

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

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: '`judge-jev quality` MUST accept `--dry-run`.'
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.81; check=CLI run@0.94
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.77; check=CLI run@0.90
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.77; check=CLI run@0.94
- s2: '`judge-jev check` MUST accept `--dry-run`.'
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.85; check=CLI run@0.94
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.85; check=CLI run@0.91
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.80; check=CLI run@0.92
- s3: 'A dry run MUST compose every request without calling Jev.'
    - pass: obligations=2@0.40; joined_by=none@0.50; term=none@0.82; check=CLI run@0.69
    - pass: obligations=2@0.43; joined_by=none@0.41; term=none@0.81; check=CLI run@0.60
    - pass: obligations=2@0.47; joined_by=none@0.51; term=none@0.82; check=CLI run@0.65
- s4: 'Each dry-run entry MUST report the record id.'
    - pass: obligations=1@1.00; joined_by=none@0.96; term=none@0.61; check=CLI run@0.75
    - pass: obligations=1@1.00; joined_by=none@0.96; term=none@0.61; check=CLI run@0.79
    - pass: obligations=1@1.00; joined_by=none@0.96; term=none@0.64; check=CLI run@0.73
- s5: "Each dry-run entry MUST report the record's Raptor source."
    - pass: obligations=1@0.99; joined_by=none@0.95; term=none@0.68; check=CLI run@0.71
    - pass: obligations=1@0.99; joined_by=none@0.94; term=none@0.73; check=CLI run@0.69
    - pass: obligations=1@0.99; joined_by=none@0.96; term=none@0.71; check=CLI run@0.73
- s6: 'Each dry-run entry MUST report the resolved location as its path, section\nor symbol.'
    - pass: obligations=1@0.72; joined_by=alternatives@0.62; term=none@0.59; check=CLI run@0.69
    - pass: obligations=1@0.73; joined_by=alternatives@0.69; term=none@0.57; check=CLI run@0.62
    - pass: obligations=1@0.67; joined_by=alternatives@0.73; term=none@0.60; check=CLI run@0.65
- s7: "Each dry-run entry MUST report the digest of the location's selected\ntext."
    - pass: obligations=1@0.96; joined_by=none@0.94; term=none@0.81; check=CLI run@0.60
    - pass: obligations=1@0.99; joined_by=none@0.95; term=none@0.80; check=CLI run@0.66
    - pass: obligations=1@0.99; joined_by=none@0.95; term=none@0.82; check=CLI run@0.68
- s8: 'Each dry-run entry MUST report the mode.'
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.86; check=CLI run@0.62
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.86; check=CLI run@0.56
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.86; check=CLI run@0.64
- s9: 'Each dry-run entry MUST report the question set as its shipped id or its\noverride path.'
    - pass: obligations=1@0.85; joined_by=alternatives@0.89; term=none@0.85; check=CLI run@0.73
    - pass: obligations=1@0.81; joined_by=alternatives@0.86; term=none@0.82; check=CLI run@0.76
    - pass: obligations=1@0.81; joined_by=alternatives@0.89; term=none@0.86; check=CLI run@0.77
- s10: 'In `task` mode, each dry-run entry MUST report the vars file.'
    - pass: obligations=1@0.96; joined_by=condition+obligation@0.95; term=none@0.81; check=CLI run@0.68
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.90; term=none@0.79; check=CLI run@0.77
    - pass: obligations=1@0.96; joined_by=condition+obligation@0.94; term=none@0.81; check=CLI run@0.76
- s11: 'In `task` mode, each dry-run entry MUST report the rendered text.'
    - pass: obligations=1@0.92; joined_by=condition+obligation@0.94; term=none@0.90; check=CLI run@0.80
    - pass: obligations=1@0.93; joined_by=condition+obligation@0.92; term=none@0.85; check=CLI run@0.81
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.95; term=none@0.82; check=CLI run@0.81
- s12: 'Each dry-run entry MUST report the full composed request.'
    - pass: obligations=1@0.99; joined_by=none@0.96; term=none@0.76; check=CLI run@0.80
    - pass: obligations=1@0.97; joined_by=none@0.96; term=none@0.80; check=CLI run@0.79
    - pass: obligations=1@0.97; joined_by=none@0.98; term=none@0.79; check=CLI run@0.79
- s13: "Each dry-run entry MUST report the composed request's size against the\nrequest limit."
    - pass: obligations=1@0.83; joined_by=none@0.92; term=none@0.82; check=CLI run@0.73
    - pass: obligations=1@0.83; joined_by=none@0.77; term=none@0.77; check=CLI run@0.75
    - pass: obligations=1@0.79; joined_by=none@0.73; term=none@0.85; check=CLI run@0.71
- s14: 'For `quality`, the dry run MUST report the decision tree.'
    - pass: obligations=1@0.99; joined_by=none@0.68; term=none@0.77; check=CLI run@0.73
    - pass: obligations=1@0.99; joined_by=none@0.47; term=none@0.79; check=CLI run@0.74
    - pass: obligations=1@0.99; joined_by=none@0.46; term=none@0.81; check=CLI run@0.79
- s15: 'For `quality`, the dry run MUST report the composed wave-1 request.'
    - pass: obligations=1@0.97; joined_by=none@0.55; term=none@0.84; check=CLI run@0.84
    - pass: obligations=1@0.95; joined_by=none@0.75; term=none@0.84; check=CLI run@0.87
    - pass: obligations=1@0.95; joined_by=none@0.68; term=none@0.82; check=CLI run@0.86
- s16: 'A dry run MUST fail with a typed error on anything that would make the\nlive request wrong: an unresolved record or location, a render failure,\nor an oversize request.'
    - pass: obligations=3@0.36; joined_by=condition+obligation@0.56; term=none@0.34; check=CLI run@0.74
    - pass: obligations=3@0.24; joined_by=condition+obligation@0.52; term=none@0.34; check=CLI run@0.73
    - pass: obligations=3@0.36; joined_by=condition+obligation@0.55; term=none@0.39; check=CLI run@0.79
