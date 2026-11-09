# Packet group A (iteration 2)


======== NFR-JEV-0001 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## NFR-JEV-0001: Deterministic offline tests

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model. Recorded Jev answers are
an answers file (`--answers-file`): JSON answers given to judge-jev.

**MUST statements:**

- judge-jev tests MUST run offline against recorded Jev answers.

**MUST NOT statements:**

- judge-jev tests MUST NOT depend on timing.
- judge-jev tests MUST NOT depend on sleeps.
- judge-jev tests MUST NOT depend on ordering.

### Rationale

Flaky tests are prohibited; live Jev calls are neither free nor
repeatable.

### Success Criteria

**Acceptance Criteria:**

- [ ] The test suite passes 20 consecutive runs with networking disabled.

```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## NFR-JEV-0001: Deterministic offline tests

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev tests MUST run offline against recorded Jev answers.

**MUST NOT statements:**

- judge-jev tests MUST NOT depend on timing.
- judge-jev tests MUST NOT depend on sleeps.
- judge-jev tests MUST NOT depend on ordering.

### Rationale

Flaky tests are prohibited; live Jev calls are neither free nor
repeatable.

### Success Criteria

**Acceptance Criteria:**

- [ ] The test suite passes 20 consecutive runs with networking disabled.

```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'judge-jev tests MUST run offline against recorded Jev answers.'
    - pass: obligations=1@0.72; joined_by=none@0.91; term=none@0.69; check=CLI run@0.57
    - pass: obligations=1@0.61; joined_by=none@0.91; term=none@0.66; check=CLI run@0.45
    - pass: obligations=1@0.71; joined_by=none@0.89; term=none@0.61; check=CLI run@0.47
- s2: 'judge-jev tests MUST NOT depend on timing.'
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.47; check=inspection or grep@0.59
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.36; check=inspection or grep@0.47
    - pass: obligations=1@0.99; joined_by=none@0.95; term=none@0.46; check=inspection or grep@0.31
- s3: 'judge-jev tests MUST NOT depend on sleeps.'
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.64; check=inspection or grep@0.89
    - pass: obligations=1@1.00; joined_by=none@0.96; term=none@0.68; check=inspection or grep@0.90
    - pass: obligations=1@1.00; joined_by=none@0.95; term=none@0.62; check=inspection or grep@0.87
- s4: 'judge-jev tests MUST NOT depend on ordering.'
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.34; check=inspection or grep@0.65
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.26; check=inspection or grep@0.66
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.35; check=inspection or grep@0.57


======== REQ-JEV-0001 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0001: Records come from Raptor

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool that imports Markdown records
into its record store.

**MUST statements:**

- judge-jev MUST obtain records through Raptor's query interface.

**MUST NOT statements:**

- judge-jev MUST NOT parse record Markdown itself.
- judge-jev MUST NOT run SQL (Structured Query Language) against the record
  store itself.

### Rationale

Raptor owns the schema and every conversion; the Raptor team can change
them and notify judge-jev without breaking it.

### Success Criteria

**Acceptance Criteria:**

- [ ] judge-jev contains no Markdown record parser and no SQL statement.


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0001: Records come from Raptor

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST obtain records through Raptor's query interface.

**MUST NOT statements:**

- judge-jev MUST NOT parse record Markdown itself.
- judge-jev MUST NOT run SQL (Structured Query Language) against the record
  store itself.

### Rationale

Raptor owns the schema and every conversion; the Raptor team can change
them and notify judge-jev without breaking it.

### Success Criteria

**Acceptance Criteria:**

- [ ] judge-jev contains no Markdown record parser and no SQL statement.


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: "judge-jev MUST obtain records through Raptor's query interface."
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.70; check=inspection or grep@0.44
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.62; check=inspection or grep@0.61
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.57; check=inspection or grep@0.51
- s2: 'judge-jev MUST NOT parse record Markdown itself.'
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.85; check=inspection or grep@0.99
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.81; check=inspection or grep@0.99
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.81; check=inspection or grep@0.99
- s3: 'judge-jev MUST NOT run SQL (Structured Query Language) against the record\nstore itself.'
    - pass: obligations=1@1.00; joined_by=none@0.96; term=none@0.74; check=inspection or grep@0.99
    - pass: obligations=1@1.00; joined_by=none@0.96; term=none@0.70; check=inspection or grep@0.99
    - pass: obligations=1@1.00; joined_by=none@0.98; term=none@0.74; check=inspection or grep@0.99


======== REQ-JEV-0002 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0002: One batch command calls Jev

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: The batch command is
`jev_judge.py batch`: it reads request lines, sends each to Jev and writes a
result line. A result envelope is the JSON result line for one request,
holding its answers or its error. A typed error code is a stable dotted code
naming a failure. The fixed retry policy is one retry of a call that failed
with a recoverable or transient error (`JEV.RATE_LIMITED`, `JEV.OVERLOADED`,
`JEV.NETWORK`, `JEV.RESPONSE_INVALID`). The request size limit is the
`--max-request-bytes` value, at most 64000 bytes. The sc-observability
logger is the JSON-lines logger of the sc-observability package, which
writes `.sc/judge-jev/logs/judge-jev.log.jsonl`.

**MUST statements:**

- judge-jev MUST send every Jev request through one batch command.
- The batch command MUST read request lines.
- The batch command MUST write one result envelope per request.
- The batch command MUST use typed error codes.
- The batch command MUST apply a fixed retry policy.
- The batch command MUST enforce request size limits.
- The batch command MUST log every request through the sc-observability
  logger (REQ-JEV-0008).
- The batch command MUST log every answer through the sc-observability
  logger (REQ-JEV-0008).

### Rationale

One call path keeps the Jev core stable while a Rust implementation
replaces it (ADR-JEV-0001).

### Success Criteria

**Acceptance Criteria:**

- [ ] A request file of three lines produces three result envelopes and
  three log entries.


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0002: One batch command calls Jev

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST send every Jev request through one batch command.
- The batch command MUST read request lines.
- The batch command MUST write one result envelope per request.
- The batch command MUST use typed error codes.
- The batch command MUST apply a fixed retry policy.
- The batch command MUST enforce request size limits.
- The batch command MUST log every request through the sc-observability
  logger (REQ-JEV-0008).
- The batch command MUST log every answer through the sc-observability
  logger (REQ-JEV-0008).

### Rationale

One call path keeps the Jev core stable while a Rust implementation
replaces it (ADR-JEV-0001).

### Success Criteria

**Acceptance Criteria:**

- [ ] A request file of three lines produces three result envelopes and
  three log entries.


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'judge-jev MUST send every Jev request through one batch command.'
    - pass: obligations=1@0.97; joined_by=none@0.99; term=none@0.52; check=inspection or grep@0.51
    - pass: obligations=1@0.97; joined_by=none@0.98; term=none@0.56; check=inspection or grep@0.42
    - pass: obligations=1@0.95; joined_by=none@0.98; term=none@0.59; check=inspection or grep@0.51
- s2: 'The batch command MUST read request lines.'
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.84; check=unit test@0.31
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.86; check=CLI run@0.35
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.84; check=unit test@0.31
- s3: 'The batch command MUST write one result envelope per request.'
    - pass: obligations=1@0.93; joined_by=none@0.98; term=none@0.86; check=CLI run@0.60
    - pass: obligations=1@0.93; joined_by=none@0.99; term=none@0.75; check=CLI run@0.54
    - pass: obligations=1@0.95; joined_by=none@0.99; term=none@0.80; check=CLI run@0.52
- s4: 'The batch command MUST use typed error codes.'
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.94; check=inspection or grep@0.34
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.86; check=inspection or grep@0.35
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.91; check=inspection or grep@0.32
- s5: 'The batch command MUST apply a fixed retry policy.'
    - pass: obligations=1@0.99; joined_by=none@0.86; term=none@0.84; check=unit test@0.55
    - pass: obligations=1@0.99; joined_by=none@0.84; term=none@0.81; check=unit test@0.46
    - pass: obligations=1@0.97; joined_by=none@0.87; term=none@0.86; check=unit test@0.49
- s6: 'The batch command MUST enforce request size limits.'
    - pass: obligations=1@1.00; joined_by=none@0.99; term=none@0.90; check=CLI run@0.32
    - pass: obligations=1@1.00; joined_by=none@1.00; term=none@0.89; check=CLI run@0.34
    - pass: obligations=1@0.99; joined_by=none@0.99; term=none@0.90; check=CLI run@0.26
- s7: 'The batch command MUST log every request through the sc-observability\nlogger (REQ-JEV-0008).'
    - pass: obligations=1@0.93; joined_by=none@0.87; term=none@0.52; check=inspection or grep@0.35
    - pass: obligations=1@0.95; joined_by=none@0.86; term=none@0.59; check=inspection or grep@0.36
    - pass: obligations=1@0.92; joined_by=none@0.94; term=none@0.52; check=inspection or grep@0.36
- s8: 'The batch command MUST log every answer through the sc-observability\nlogger (REQ-JEV-0008).'
    - pass: obligations=1@0.92; joined_by=none@0.91; term=none@0.68; check=inspection or grep@0.31
    - pass: obligations=1@0.92; joined_by=none@0.89; term=none@0.65; check=inspection or grep@0.47
    - pass: obligations=1@0.93; joined_by=none@0.92; term=none@0.62; check=inspection or grep@0.37


======== REQ-JEV-0003 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0003: TypeSafe key lookup

**Status:** Draft  

### Requirement Statement

Definitions: TypeSafe is the company whose API serves Jev. The platform
credential store is the macOS Keychain, the Windows Credential Manager or,
on Linux, the Secret Service.

**MUST statements:**

- judge-jev MUST read the TypeSafe API key from `TYPESAFE_API_KEY` first,
  then from the platform credential store, service `plan-anchor`, account
  `typesafe-api-key`.

### Rationale

Tools that call Jev share one stored key, saved once.

### Success Criteria

**Acceptance Criteria:**

- [ ] A key stored under that service and account is found with no other
  setup.


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0003: TypeSafe key lookup

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST read the TypeSafe API key from `TYPESAFE_API_KEY` first,
  then from the platform credential store, service `plan-anchor`, account
  `typesafe-api-key`.

### Rationale

Tools that call Jev share one stored key, saved once.

### Success Criteria

**Acceptance Criteria:**

- [ ] A key stored under that service and account is found with no other
  setup.


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'judge-jev MUST read the TypeSafe API key from `TYPESAFE_API_KEY` first,\nthen from the platform credential store, service `plan-anchor`, account\n`typesafe-api-key`.'
    - pass: obligations=1@0.51; joined_by=and-list@0.20; term=none@0.64; check=unit test@0.81
    - pass: obligations=1@0.52; joined_by=alternatives@0.19; term=none@0.61; check=unit test@0.75
    - pass: obligations=1@0.52; joined_by=and-list@0.27; term=none@0.61; check=unit test@0.77


======== REQ-JEV-0004 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0004: Remote-judge consent

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: A live Jev call is a
request sent to Jev.


**MUST statements:**

- judge-jev MUST refuse every live Jev call with
  `POLICY.REMOTE_JUDGE_DISABLED` unless the committed
  `.sc/judge-jev/settings.yaml` sets `allow_remote_judge: true`.

**MUST NOT statements:**

- judge-jev MUST NOT write that setting without the user's answer.

### Rationale

Text sent to Jev leaves the machine; the user decides once per repository.

### Success Criteria

**Acceptance Criteria:**

- [ ] With the setting absent or false, a live call exits with
  `POLICY.REMOTE_JUDGE_DISABLED` and sends nothing.


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0004: Remote-judge consent

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST refuse every live Jev call with
  `POLICY.REMOTE_JUDGE_DISABLED` unless the committed
  `.sc/judge-jev/settings.yaml` sets `allow_remote_judge: true`.

**MUST NOT statements:**

- judge-jev MUST NOT write that setting without the user's answer.

### Rationale

Text sent to Jev leaves the machine; the user decides once per repository.

### Success Criteria

**Acceptance Criteria:**

- [ ] With the setting absent or false, a live call exits with
  `POLICY.REMOTE_JUDGE_DISABLED` and sends nothing.


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'judge-jev MUST refuse every live Jev call with\n`POLICY.REMOTE_JUDGE_DISABLED` unless the committed\n`.sc/judge-jev/settings.yaml` sets `allow_remote_judge: true`.'
    - pass: obligations=1@0.81; joined_by=condition+obligation@0.99; term=none@0.49; check=unit test@0.46
    - pass: obligations=1@0.79; joined_by=condition+obligation@1.00; term=none@0.55; check=unit test@0.45
    - pass: obligations=1@0.81; joined_by=condition+obligation@0.99; term=none@0.41; check=unit test@0.55
- s2: "judge-jev MUST NOT write that setting without the user's answer."
    - pass: obligations=1@0.96; joined_by=condition+obligation@0.75; term=none@0.50; check=inspection or grep@0.45
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.69; term=none@0.52; check=inspection or grep@0.42
    - pass: obligations=1@0.97; joined_by=condition+obligation@0.73; term=none@0.51; check=inspection or grep@0.31


======== REQ-JEV-0005 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0005: Marketplace and installer

**Status:** Draft  

### Requirement Statement

Definitions: A harness is an agent tool judge-jev installs into: Claude,
Codex or Cursor. A harness is locked when the install lock records it,
installed when its `.<harness>/skills/judge-jev/` directory exists, and
present when its `.<harness>/` directory exists.

**MUST statements:**

- judge-jev MUST ship as a marketplace plugin for Claude.
- judge-jev MUST ship as a marketplace plugin for Codex.
- judge-jev MUST ship as a marketplace plugin for Cursor.
- An upgrade MUST update every harness that is locked, installed or present.

### Rationale

No harness is left on an old version.

### Success Criteria

**Acceptance Criteria:**

- [ ] Upgrading in a repository with Claude, Codex and Cursor installs
  updates all three.


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0005: Marketplace and installer

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST ship as a marketplace plugin for Claude.
- judge-jev MUST ship as a marketplace plugin for Codex.
- judge-jev MUST ship as a marketplace plugin for Cursor.
- An upgrade MUST update every harness that is locked, installed or present.

### Rationale

No harness is left on an old version.

### Success Criteria

**Acceptance Criteria:**

- [ ] Upgrading in a repository with Claude, Codex and Cursor installs
  updates all three.


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'judge-jev MUST ship as a marketplace plugin for Claude.'
    - pass: obligations=1@0.97; joined_by=none@0.92; term=none@0.56; check=inspection or grep@0.74
    - pass: obligations=1@0.96; joined_by=none@0.92; term=none@0.56; check=inspection or grep@0.70
    - pass: obligations=1@0.97; joined_by=none@0.95; term=none@0.61; check=inspection or grep@0.68
- s2: 'judge-jev MUST ship as a marketplace plugin for Codex.'
    - pass: obligations=1@0.97; joined_by=none@0.94; term=none@0.61; check=inspection or grep@0.70
    - pass: obligations=1@0.97; joined_by=none@0.94; term=none@0.61; check=inspection or grep@0.70
    - pass: obligations=1@0.97; joined_by=none@0.96; term=none@0.55; check=inspection or grep@0.75
- s3: 'judge-jev MUST ship as a marketplace plugin for Cursor.'
    - pass: obligations=1@0.96; joined_by=none@0.96; term=none@0.65; check=inspection or grep@0.70
    - pass: obligations=1@0.97; joined_by=none@0.96; term=none@0.65; check=inspection or grep@0.61
    - pass: obligations=1@0.97; joined_by=none@0.96; term=none@0.55; check=inspection or grep@0.73
- s4: 'An upgrade MUST update every harness that is locked, installed or present.'
    - pass: obligations=1@0.41; joined_by=condition+obligation@0.31; term=none@0.79; check=CLI run@0.26
    - pass: obligations=1@0.43; joined_by=condition+obligation@0.41; term=none@0.70; check=CLI run@0.26
    - pass: obligations=1@0.49; joined_by=alternatives@0.18; term=none@0.73; check=CLI run@0.25


======== REQ-JEV-0006 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0006: Local record database built through Raptor

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool that imports Markdown records.
SQLite is a single-file SQL database. Dolt is a SQL database with Git-style
branches; a SQLite snapshot of a Dolt branch is a SQLite copy of that
branch.

**MUST statements:**

- judge-jev MUST obtain its record database by asking Raptor to build a
  local SQLite database from the repository's Raptor-parseable Markdown on
  each run.
- When Raptor supplies a SQLite snapshot of a Dolt branch, judge-jev MUST
  query it through the same Raptor interface.

### Rationale

Querying SQLite is the same work whether it was built from Markdown or
pulled from Dolt, so the source can change without changing judge-jev.

### Success Criteria

**Acceptance Criteria:**

- [ ] A run in a repository with a `.raptor/` configuration judges records
  from a database built in that run.


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0006: Local record database built through Raptor

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST obtain its record database by asking Raptor to build a
  local SQLite database from the repository's Raptor-parseable Markdown on
  each run.
- When Raptor supplies a SQLite snapshot of a Dolt branch, judge-jev MUST
  query it through the same Raptor interface.

### Rationale

Querying SQLite is the same work whether it was built from Markdown or
pulled from Dolt, so the source can change without changing judge-jev.

### Success Criteria

**Acceptance Criteria:**

- [ ] A run in a repository with a `.raptor/` configuration judges records
  from a database built in that run.


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: "judge-jev MUST obtain its record database by asking Raptor to build a\nlocal SQLite database from the repository's Raptor-parseable Markdown on\neach run."
    - pass: obligations=1@0.47; joined_by=none@0.86; term=none@0.57; check=CLI run@0.60
    - pass: obligations=1@0.39; joined_by=none@0.89; term=none@0.45; check=CLI run@0.52
    - pass: obligations=1@0.53; joined_by=none@0.84; term=none@0.54; check=CLI run@0.56
- s2: 'When Raptor supplies a SQLite snapshot of a Dolt branch, judge-jev MUST\nquery it through the same Raptor interface.'
    - pass: obligations=1@0.96; joined_by=condition+obligation@0.99; term=none@0.64; check=unit test@0.34
    - pass: obligations=1@0.96; joined_by=condition+obligation@0.99; term=none@0.54; check=unit test@0.40
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.99; term=none@0.46; check=unit test@0.32


======== REQ-JEV-0007 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0007: judge-jev's own records are Raptor-parseable

**Status:** Draft  

### Requirement Statement

Definitions: An issue is a diagnostic Raptor's import reports for a record.

**MUST statements:**

- judge-jev's requirements, non-functional requirements and decisions MUST
  import through Raptor with no issues.

### Rationale

judge-jev depends on Raptor's format, so its own records prove the format
first.

### Success Criteria

**Acceptance Criteria:**

- [ ] Raptor's import of this repository reports zero issues.


```

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

```markdown
## REQ-JEV-0007: judge-jev's own records are Raptor-parseable

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev's requirements, non-functional requirements and decisions MUST
  import through Raptor with no issues.

### Rationale

judge-jev depends on Raptor's format, so its own records prove the format
first.

### Success Criteria

**Acceptance Criteria:**

- [ ] Raptor's import of this repository reports zero issues.


```

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: "judge-jev's requirements, non-functional requirements and decisions MUST\nimport through Raptor with no issues."
    - pass: obligations=3@0.32; joined_by=none@0.65; term=none@0.42; check=CLI run@0.96
    - pass: obligations=1@0.40; joined_by=none@0.68; term=none@0.44; check=CLI run@0.98
    - pass: obligations=3@0.31; joined_by=none@0.69; term=none@0.40; check=CLI run@0.98


======== REQ-JEV-0008 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0008: Logging through the sc-observability logger

**Status:** Draft  

### Requirement Statement

Definitions: The sc-observability logger is the JSON-lines logger of the
sc-observability package (version 1.5.0). A quality-tree branch is the next
wave a quality decision tree's rules select from Jev's answers.

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

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

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

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: 'judge-jev MUST write its run logs (requests, answers, quality-tree\nbranches, verdicts) through the sc-observability logger, the logger\nsc-agent uses.'
    - pass: obligations=1@0.77; joined_by=none@0.68; term=none@0.36; check=CLI run@0.31
    - pass: obligations=1@0.79; joined_by=none@0.68; term=none@0.40; check=inspection or grep@0.30
    - pass: obligations=1@0.71; joined_by=none@0.62; term=none@0.37; check=inspection or grep@0.30
- s2: 'judge-jev MUST NOT keep its own log format alongside it.'
    - pass: obligations=1@0.99; joined_by=none@0.90; term=none@0.61; check=inspection or grep@0.87
    - pass: obligations=1@0.99; joined_by=none@0.94; term=none@0.64; check=inspection or grep@0.82
    - pass: obligations=1@0.99; joined_by=none@0.96; term=none@0.61; check=inspection or grep@0.86


======== REQ-JEV-0101 ========

## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)

```markdown
## REQ-JEV-0101: Record quality mode

**Status:** Proposed  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A quality decision tree is a data file of prompts (questions to Jev)
in waves; a wave is one set of questions, and its reason is the report of
its questions and Jev's answers. A per-statement wave asks its questions
once for each MUST and MUST NOT statement. A verdict rule is a rule in the
tree file that turns a wave's answers into a verdict (`yes` or `no`). The
walk is the sequence of waves from the first to the one that gives the
verdict; its decision-tree path is the list of those waves' ids.

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

## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only

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

## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.

- s1: "judge-jev MUST provide a mode that reports, for one requirement (REQ),\nnon-functional requirement (NFR) or architecture decision record (ADR),\nthe verdict of that record kind's quality decision tree."
    - pass: obligations=1@0.80; joined_by=none@0.60; term=none@0.42; check=CLI run@0.75
    - pass: obligations=1@0.84; joined_by=none@0.69; term=none@0.42; check=CLI run@0.79
    - pass: obligations=1@0.80; joined_by=none@0.61; term=none@0.42; check=CLI run@0.80
- s2: 'The mode MUST judge only records that Raptor imported without\ndiagnostics.'
    - pass: obligations=1@0.92; joined_by=none@0.69; term=none@0.29; check=unit test@0.49
    - pass: obligations=1@0.91; joined_by=none@0.46; term=none@0.31; check=unit test@0.52
    - pass: obligations=1@0.95; joined_by=none@0.61; term=none@0.32; check=unit test@0.55
- s3: "The mode MUST run as a decision tree of prompts: each wave sends several\nquestions, and the answers to one wave select the next wave's questions."
    - pass: obligations=3@0.17; joined_by=none@0.60; term=none@0.61; check=unit test@0.32
    - pass: obligations=3@0.13; joined_by=none@0.59; term=none@0.57; check=unit test@0.26
    - pass: obligations=3@0.15; joined_by=none@0.57; term=none@0.66; check=unit test@0.36
- s4: "Every wave MUST report, as its reason, each of its questions with the\nquestion's id and text, Jev's choice and Jev's confidence."
    - pass: obligations=1@0.52; joined_by=none@0.45; term=none@0.74; check=CLI run@0.21
    - pass: obligations=1@0.55; joined_by=none@0.41; term=none@0.71; check=CLI run@0.20
    - pass: obligations=1@0.52; joined_by=none@0.49; term=none@0.69; check=unit test@0.16
- s5: 'A wave the tree marks per statement MUST send one request for each MUST\nand MUST NOT statement of the record.'
    - pass: obligations=1@0.92; joined_by=and-list@0.24; term=none@0.76; check=unit test@0.35
    - pass: obligations=1@0.89; joined_by=none@0.44; term=none@0.79; check=unit test@0.45
    - pass: obligations=1@0.88; joined_by=none@0.40; term=none@0.73; check=unit test@0.37
- s6: 'Each per-statement request MUST carry its statement with the whole record\nas context.'
    - pass: obligations=1@0.63; joined_by=none@0.79; term=none@0.71; check=unit test@0.25
    - pass: obligations=1@0.64; joined_by=none@0.80; term=none@0.75; check=CLI run@0.24
    - pass: obligations=1@0.65; joined_by=none@0.82; term=none@0.77; check=unit test@0.26
- s7: "A per-statement wave's reason MUST list each statement's index and text\nwith each question's id, choice and confidence."
    - pass: obligations=1@0.55; joined_by=none@0.47; term=none@0.76; check=unit test@0.20
    - pass: obligations=1@0.59; joined_by=none@0.44; term=none@0.74; check=inspection or grep@0.20
    - pass: obligations=1@0.60; joined_by=none@0.35; term=none@0.79; check=CLI run@0.27
- s8: "A per-statement wave's verdict rule MUST be able to fire when any one\nstatement's answers match it."
    - pass: obligations=1@0.95; joined_by=condition+obligation@0.65; term=none@0.46; check=unit test@0.42
    - pass: obligations=1@0.92; joined_by=condition+obligation@0.37; term=none@0.52; check=unit test@0.51
    - pass: obligations=1@0.92; joined_by=condition+obligation@0.39; term=none@0.54; check=unit test@0.51
- s9: "A per-statement wave's verdict MUST name the statements whose answers\nfired its rule."
    - pass: obligations=1@0.95; joined_by=none@0.74; term=none@0.74; check=unit test@0.20
    - pass: obligations=1@0.92; joined_by=none@0.80; term=none@0.70; check=unit test@0.24
    - pass: obligations=1@0.96; joined_by=none@0.80; term=none@0.73; check=unit test@0.19
- s10: 'A per-statement request that gets no answer MUST fail with an error that\nnames its statement.'
    - pass: obligations=2@0.29; joined_by=none@0.40; term=none@0.57; check=CLI run@0.57
    - pass: obligations=2@0.28; joined_by=condition+obligation@0.36; term=none@0.60; check=CLI run@0.56
    - pass: obligations=2@0.24; joined_by=none@0.45; term=none@0.52; check=CLI run@0.59
- s11: 'A wave after the first MUST refine the answers of the wave before it.'
    - pass: obligations=1@0.85; joined_by=none@0.82; term=none@0.34; check=CLI run@0.21
    - pass: obligations=1@0.85; joined_by=none@0.66; term=none@0.30; check=CLI run@0.21
    - pass: obligations=1@0.83; joined_by=none@0.71; term=none@0.32; check=unit test@0.21
- s12: 'A wave after the first MUST be designed from the observed live results\nof the wave before it.'
    - pass: obligations=1@0.81; joined_by=none@0.73; term=none@0.49; check=inspection or grep@0.18
    - pass: obligations=1@0.89; joined_by=none@0.71; term=none@0.46; check=inspection or grep@0.18
    - pass: obligations=1@0.92; joined_by=none@0.73; term=none@0.49; check=inspection or grep@0.18
- s13: "A wave with no next wave MUST end the walk, with its verdict given by a\nrule in the tree file over that wave's answers."
    - pass: obligations=2@0.32; joined_by=none@0.29; term=none@0.73; check=CLI run@0.26
    - pass: obligations=2@0.49; joined_by=condition+obligation@0.39; term=none@0.73; check=unit test@0.26
    - pass: obligations=2@0.45; joined_by=none@0.29; term=none@0.74; check=CLI run@0.26
- s14: 'The tree MUST ship with the tool as a data file a consumer can override\n(REQ-JEV-0205); answers select the branch and the verdict, never a model\nchoosing the next questions.'
    - pass: obligations=3@0.29; joined_by=none@0.37; term=none@0.25; check=inspection or grep@0.47
    - pass: obligations=3@0.35; joined_by=none@0.31; term=none@0.32; check=inspection or grep@0.45
    - pass: obligations=3@0.29; joined_by=none@0.29; term=none@0.26; check=inspection or grep@0.51
- s15: 'A failing answer MUST report the decision-tree path that failed.'
    - pass: obligations=1@0.89; joined_by=none@0.82; term=none@0.40; check=CLI run@0.26
    - pass: obligations=1@0.93; joined_by=none@0.81; term=none@0.41; check=CLI run@0.35
    - pass: obligations=1@0.87; joined_by=none@0.84; term=none@0.46; check=CLI run@0.26
- s16: "A live run MUST log every wave as output: its composed request, Jev's\nanswers, its reason and the branch or verdict they selected."
    - pass: obligations=1@0.47; joined_by=none@0.66; term=none@0.59; check=inspection or grep@0.44
    - pass: obligations=1@0.51; joined_by=none@0.59; term=none@0.47; check=inspection or grep@0.47
    - pass: obligations=1@0.51; joined_by=none@0.68; term=none@0.50; check=inspection or grep@0.46
- s17: "The mode MUST NOT check structure that Raptor's import checks."
    - pass: obligations=1@0.97; joined_by=none@0.86; term=none@0.25; check=unit test@0.40
    - pass: obligations=1@0.96; joined_by=none@0.85; term=none@0.24; check=unit test@0.42
    - pass: obligations=1@0.96; joined_by=none@0.86; term=none@0.26; check=unit test@0.40
