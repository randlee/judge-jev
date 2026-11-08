# judge-jev Requirements - Raptor Integration

**ID Range:** REQ-JEV-0001 through REQ-JEV-0007  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-07  
**Owner:** Rand Lee  
**Version:** 0.1.0  

---

## Overview

judge-jev works with Raptor-parseable Markdown and Raptor's SQL store. It
reads records only through Raptor and calls Jev through plan-anchor's layer.

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

## REQ-JEV-0002: Same Jev calling layer as plan-anchor

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST call Jev through plan-anchor's `jev_judge.py batch`
  contract: the same request lines, result envelopes, typed error codes,
  exit codes, retry policy, request size limits and run-file logging.
- Code copied from plan-anchor MUST differ from its source only by
  identifier renames.

### Rationale

Rand will replace the Python Jev layer with a Rust CLI using plan-anchor's
API as the model; identical contracts make the replacement a drop-in.

### Success Criteria

**Acceptance Criteria:**

- [ ] A request file accepted by plan-anchor's `batch` produces the same
  result envelope from judge-jev's `batch`.

## REQ-JEV-0003: Same license lookup as plan-anchor

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST read the TypeSafe API key from `TYPESAFE_API_KEY` first,
  then from the same platform credential-store entry plan-anchor reads.

### Rationale

One key saved once serves both tools.

### Success Criteria

**Acceptance Criteria:**

- [ ] A key stored for plan-anchor is found by judge-jev with no other setup.

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

- judge-jev MUST ship as a marketplace plugin for Claude, Codex and Cursor
  with plan-anchor's installer behaviour.
- An upgrade MUST update every harness that is locked, installed or present.

### Rationale

Users install it the same way as plan-anchor, and no harness is left on an
old version.

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
