# judge-jev Requirements - Raptor Integration

**ID Range:** REQ-JEV-0001 through REQ-JEV-0008, NFR-JEV-0001  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-07  
**Owner:** Rand Lee  
**Version:** 0.1.0  

---

## Overview

judge-jev works with Raptor-parseable Markdown and Raptor's SQL store. It
reads records only through Raptor and sends every Jev request through one
batch command.

---

## REQ-JEV-0001: Records come from Raptor

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool that imports Markdown records
into its record store and serves them to other tools (ADR-JEV-0002). Its
query interface is the way Raptor hands records to another tool.

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

## REQ-JEV-0002: One batch command calls Jev

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. The batch command is `jev_judge.py
batch`: it reads request lines (one JSON request per line), sends each to
Jev and writes a result line. A result envelope is the JSON result line for
one request, holding its answers or its error
(`assets/schemas/jev-batch-result.schema.json`). A typed error code is a
stable dotted code naming a failure, such as `JEV.NETWORK` or
`JEV.RATE_LIMITED`. The fixed retry policy is one retry of a call that
failed with a recoverable or transient error (`JEV.RATE_LIMITED`,
`JEV.OVERLOADED`, `JEV.NETWORK`, `JEV.RESPONSE_INVALID`), after the
response's Retry-After delay capped at 30 seconds, or after 1 second without
one. The request size limit is the `--max-request-bytes` value, at most
64000 bytes; by default 24000 bytes with `--gate plan` and 64000 bytes with
`--gate dev`. The sc-observability logger is the JSON-lines logger of the
sc-observability package (version 1.5.0), which writes
`.sc/judge-jev/logs/judge-jev.log.jsonl`.

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

## REQ-JEV-0003: TypeSafe key lookup

**Status:** Draft  

### Requirement Statement

Definitions: TypeSafe is the company whose API (application programming
interface) serves Jev, the judge model; the TypeSafe API key authenticates
calls to it. The platform credential store is the macOS Keychain, the
Windows Credential Manager or, on Linux, the Secret Service (`secret-tool`).

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

## REQ-JEV-0004: Remote-judge consent

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. A live Jev call is a request sent
to Jev, as opposed to a dry run or an answers file.
`POLICY.REMOTE_JUDGE_DISABLED` is the typed error code for a refused live
call.

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

## REQ-JEV-0005: Marketplace and installer

**Status:** Draft  

### Requirement Statement

Definitions: A harness is an agent tool judge-jev installs into: Claude
(Claude Code), Codex or Cursor. A marketplace plugin is a plugin a harness
installs from a plugin marketplace. A harness is locked when the install
lock records it, installed when its `.<harness>/skills/judge-jev/` directory
exists, and present when its `.<harness>/` directory exists in the
repository. An upgrade is an install of a newer judge-jev version.

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

## REQ-JEV-0006: Local record database built through Raptor

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool that imports Markdown records
into its record store and serves them to other tools (ADR-JEV-0002).
Raptor-parseable Markdown is Markdown in the record format Raptor's import
reads. SQLite is a single-file SQL (Structured Query Language) database.
Dolt is a SQL database with Git-style branches; a SQLite snapshot of a Dolt
branch is a SQLite copy of that branch's records. The Raptor interface is
the way Raptor hands records to another tool.

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

## REQ-JEV-0007: judge-jev's own records are Raptor-parseable

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool that imports Markdown records.
An issue is a diagnostic Raptor's import reports for a record, such as
`UNKNOWN_SECTION`.

**MUST statements:**

- judge-jev's requirements, non-functional requirements and decisions MUST
  import through Raptor with no issues.

### Rationale

judge-jev depends on Raptor's format, so its own records prove the format
first.

### Success Criteria

**Acceptance Criteria:**

- [ ] Raptor's import of this repository reports zero issues.

## REQ-JEV-0008: Logging through the sc-observability logger

**Status:** Draft  

### Requirement Statement

Definitions: The sc-observability logger is the JSON-lines logger of the
sc-observability package (version 1.5.0), which writes
`.sc/judge-jev/logs/judge-jev.log.jsonl`. sc-agent is the agent tool whose
Rust Jev tool will replace judge-jev's Python Jev core (ADR-JEV-0007). A
quality-tree branch is the next wave a quality decision tree's rules select
from Jev's answers.

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

## NFR-JEV-0001: Deterministic offline tests

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. Recorded Jev answers are an answers
file (`--answers-file`): JSON answers given to judge-jev in place of a live
Jev call.

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
