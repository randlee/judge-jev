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

Definitions: Raptor is the tool that imports records.

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
batch`: it reads request lines (one JSON request per line), sends them through
the released `sc-decidr` Python wheel and writes one result line per request.
A result envelope is the JSON result line for one request, holding its answers
or its error (`assets/schemas/jev-batch-result.schema.json`). A typed error
code is a stable dotted code naming a failure, such as `JEV.NETWORK` or
`JEV.RATE_LIMITED`. Retry and holdoff behavior belongs to sc-agent's
`REQ-SAG-0601`; judge-jev MUST NOT add a provider retry loop. The request size limit is the `--max-request-bytes` value, at most
64000 bytes; by default 24000 bytes with `--gate plan` and 64000 bytes with
`--gate dev`. The sc-observability logger is the JSON-lines logger of the
sc-observability package (version 1.5.0), which writes
`~/.judge-jev/<repository name>/<UTC date>/logs/judge-jev.log.jsonl`.

**MUST statements:**

- judge-jev MUST send every Jev request through one batch command.
- The batch command MUST read request lines.
- The batch command MUST write one result envelope per request.
- The batch command MUST use typed error codes.
- The batch command MUST use sc-agent's retry policy through the released
  `sc-decidr` wheel and MUST NOT retry provider failures itself.
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

- judge-jev MUST use sc-agent's credential lookup: repository-root `.env`,
  then the process environment, then the platform keyring.
- judge-jev MUST use the default TypeSafe keyring entry: service
  `TYPESAFE_API_KEY`, current OS account; it MUST pass no keyring selection
  options.

### Rationale

Tools that call Jev share one stored key, saved once.

### Success Criteria

**Acceptance Criteria:**

- [ ] The repository `.env` value precedes a process environment value, and
  the default TypeSafe keyring entry is found without keyring overrides.

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

Definitions: An issue is a diagnostic Raptor's import reports.

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
`~/.judge-jev/<repository name>/<UTC date>/logs/judge-jev.log.jsonl`. sc-agent is the agent tool whose
Rust Jev tool will replace judge-jev's Python Jev core (ADR-JEV-0007). A
quality-tree branch is the next wave a quality decision tree's rules select
from Jev's answers. The consumer run log is judge-jev's owned Logger.
sc-agent's general log contains decision diagnostics; its session log contains
per-decision records. The two native logger parameters are independent.

**MUST statements:**

- judge-jev MUST write its run logs (requests, answers, quality-tree
  branches, verdicts) through the sc-observability logger, the logger
  sc-agent uses.
- By default, judge-jev MUST omit both native logger parameters so sc-agent
  uses its corresponding default general and session file loggers.
- With `--sc-agent-log`, judge-jev MUST pass the same consumer-owned
  `sc_observability.Logger` directly as `general_log`, without an adapter.
- General-log injection MUST leave `session_log` omitted and its default
  session file logger in control.
- judge-jev MUST retain ownership of flush and shutdown for the injected
  Logger: flush each result's run events and close it after decision work
  ends, including cancellation.
- The consumer's request, answer, result, quality-tree branch and verdict
  events MUST remain queryable through sc-observability in either mode.

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
- [ ] An installed batch or quality run with no injection leaves both
  wheel logger arguments omitted, writes the native default general and
  session files, and preserves queryable consumer run events.
- [ ] With general-log injection, the wheel uses that exact Logger, leaves
  the native session logger at its default, and does not flush or shut down
  the caller's Logger. The consumer can still log after the wheel returns,
  then flush and shut it down; its run events remain queryable.
- [ ] Cancellation closes the consumer-owned run Logger after decision
  work stops, preserving already recorded events.

### Implementation Notes

The consumer always writes its run events through sc-observability.
Optional general-log injection adds wheel diagnostics to that same owned
Logger; it does not alter the batch JSON port or graph-run projection.

## NFR-JEV-0001: Deterministic offline tests

**Status:** Draft  

### Requirement Statement

Definitions: Jev is a judge model. Recorded Jev answers are an answers file.

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
