# judge-jev Requirements - Raptor Integration

**ID Range:** REQ-JEV-0001 through REQ-JEV-0008  
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

**MUST statements:**

- judge-jev MUST obtain records through Raptor's query interface.

**MUST NOT statements:**

- judge-jev MUST NOT parse record Markdown or run SQL against the record
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

**MUST statements:**

- judge-jev MUST send every Jev request through one batch command that
  reads request lines and writes one result envelope per request, with
  typed error codes, a fixed retry policy, request size limits and a run
  file logging every request and answer.

### Rationale

One call path keeps the Jev core stable while a Rust implementation
replaces it (ADR-JEV-0001).

### Success Criteria

**Acceptance Criteria:**

- [ ] A request file of three lines produces three result envelopes and
  one run file holding all three.

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

## REQ-JEV-0005: Marketplace and installer

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST ship as a marketplace plugin for Claude, Codex and Cursor.
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

**MUST statements:**

- judge-jev tests MUST run offline against recorded Jev answers.

**MUST NOT statements:**

- judge-jev tests MUST NOT depend on timing, sleeps or ordering.

### Rationale

Flaky tests are prohibited; live Jev calls are neither free nor
repeatable.

### Success Criteria

**Acceptance Criteria:**

- [ ] The test suite passes 20 consecutive runs with networking disabled.
