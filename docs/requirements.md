# judge-jev Requirements

**ID Range:** REQ-JEV-0001 through REQ-JEV-0011  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-07  
**Owner:** Rand Lee  
**Version:** 0.1.0  

---

## Overview

judge-jev asks TypeSafe Jev whether a prompt, skill or task template
complies with one requirement, architecture decision or non-functional
requirement, and whether such a record is well written. Records come from
Raptor. The Jev calling layer is plan-anchor's, so a later Rust CLI can
replace the Python one without changing callers.

---

## REQ-JEV-0001: Same Jev calling layer as plan-anchor

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

## REQ-JEV-0002: Same license lookup as plan-anchor

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

## REQ-JEV-0003: Remote-judge consent

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

## REQ-JEV-0004: Marketplace and installer

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

## REQ-JEV-0005: One record kind per run

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- The `judge-jev` CLI MUST take exactly one of `--req`, `--adr` or `--nfr`.
- Each of the three MUST use its own question set.

### Rationale

A requirement, a decision and a non-functional requirement are each
violated in a different way.

### Success Criteria

**Acceptance Criteria:**

- [ ] The same target judged with `--req` and with `--adr` sends different
  question sets.

## REQ-JEV-0006: One record and one target per request

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- Each Jev request MUST carry exactly one record and one target.

### Rationale

Jev judges one item at a time; batching records hides which one failed.

### Success Criteria

**Acceptance Criteria:**

- [ ] A profile mapping one file to three records sends three requests.

## REQ-JEV-0007: Target modes

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST support the target modes `prompt`, `skill` and `task`.
- In `task` mode judge-jev MUST judge both the raw template and a rendered
  assignment.

### Rationale

The raw template shows which variables are substituted; a rendered
assignment shows what an agent actually receives. Both are tested.

### Success Criteria

**Acceptance Criteria:**

- [ ] A task template judged in `task` mode produces one result for the raw
  template and one for its rendered assignment.

## REQ-JEV-0008: Profiles map documents to records

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST read `.sc/judge-jev/req-profile`, `adr-profile` and
  `nfr-profile`, each listing documents (skills, agents, task templates)
  with the array of record ids that govern each document.
- `judge-jev --req <req-profile>` MUST judge every listed document against
  every listed record.

### Rationale

The profile states which records govern which documents, so a run checks
exactly those pairs.

### Success Criteria

**Acceptance Criteria:**

- [ ] A run over a profile produces one result per (document, record) pair
  and none for unlisted pairs.

## REQ-JEV-0009: Records come from Raptor

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

## REQ-JEV-0010: Record quality mode

**Status:** Proposed  

### Requirement Statement

**MUST statements:**

- judge-jev MUST provide a mode that asks whether one REQ, NFR or ADR is
  well written.
- A failing answer MUST report the decision-tree path that failed.

### Rationale

Records Raptor rejects or that judge badly are explained instead of being
accepted by a looser schema.

### Success Criteria

**Acceptance Criteria:**

- [ ] A record with no acceptance criterion reports `no` with the path that
  names the criteria node.

## REQ-JEV-0011: Approved question wording

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- Every question and prompt text judge-jev sends MUST be approved by Rand
  before it ships.

**MUST NOT statements:**

- Agents MUST NOT author that wording during development.

### Rationale

Rand: "I do not trust non-frontier agents to write prompts. I do not even
trust frontier agents to write them."

### Success Criteria

**Acceptance Criteria:**

- [ ] Each shipped question file names the approval that admitted its text.

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
