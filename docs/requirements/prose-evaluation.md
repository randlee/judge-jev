# judge-jev Requirements - Prose Evaluation

**ID Range:** REQ-JEV-0201 through REQ-JEV-0206  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-08  
**Owner:** Rand Lee  
**Version:** 0.1.0  

---

## Overview

judge-jev evaluates prose (skills, agent prompts, task templates) against
Raptor-supplied REQ, NFR and ADR records.

---

## REQ-JEV-0201: One record kind per run

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

## REQ-JEV-0202: One record and one target per request

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- Each Jev request MUST carry exactly one record and one target.

### Rationale

Jev judges one item at a time; batching records hides which one failed.

### Success Criteria

**Acceptance Criteria:**

- [ ] A profile mapping one file to three records sends three requests.

## REQ-JEV-0203: Target modes

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

## REQ-JEV-0204: Profiles map documents to records

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

## REQ-JEV-0205: Approved question wording

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

### Success Criteria

**Acceptance Criteria:**

- [ ] A record mapped to three locations produces three results, one per
  location.
- [ ] A failure at one location is reported against that location only.

### Implementation Notes

Open: the ruling's batching option (one call per location carrying the
questions of several records, packed to fit context) conflicts with
REQ-JEV-0202 (exactly one record per request). It needs a ruling before
either record changes.

