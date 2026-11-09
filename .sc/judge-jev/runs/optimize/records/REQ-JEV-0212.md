# REQ-JEV-0212

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [5, 5, 5, 5, 5, 5] | 6/6 | 0.655 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.697 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.689 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.699; final fails [0, 0, 0] margin 0.691.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.6958; pruned 0 failing runs, margin 0.6889).

## Kept tweaks (text present in the final record) and measured effect

- remove defs (proposed by i1:mechanical)
  - old: `A definition is a term with its meaning, from a `.sc/judge-jev/*.definitions.ttl` file (ADR-JEV-0008).`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.709; m2: fails 0, margin 0.720 (reference margin 0.690, reference fails mean 0.00)
- remove s2 (proposed by i1:opus-C)
  - old: `in its state next to the record, only`
  - new: `in its state, only`
  - i1 opus-C: m1: fails 0, margin 0.706; m2: fails 0, margin 0.703 (reference margin 0.690, reference fails mean 0.00)
- remove defs (proposed by i1:sonnet-C)
  - old: `(the file, Markdown section or code symbol being judged)`
  - new: `(removed)`
  - i1 sonnet-C: m1: fails 0, margin 0.691; m2: fails 0, margin 0.695 (reference margin 0.690, reference fails mean 0.00)
- remove defs (proposed by i1:sonnet-C)
  - old: `, which holds the record`
  - new: `(removed)`
  - i1 sonnet-C: m1: fails 0, margin 0.698; m2: fails 0, margin 0.705 (reference margin 0.690, reference fails mean 0.00)
- reword defs (proposed by i2:opus-C)
  - old: `A request's state is the data it sends to Jev next to the questions.`
  - new: `A request's state is the data it sends.`
  - i2 opus-C: m1: fails 0, margin 0.703; m2: fails 0, margin 0.698 (reference margin 0.707, reference fails mean 0.00)
- reword defs (proposed by i2:opus-C)
  - old: `The size limit of a request is 24000 bytes.`
  - new: `The size limit is 24000 bytes.`
  - i2 opus-C: m1: fails 0, margin 0.718; m2: fails 0, margin 0.703 (reference margin 0.707, reference fails mean 0.00)
- remove defs (proposed by i2:sonnet-C)
  - old: `of its term, text and source`
  - new: `(removed)`
  - i2 sonnet-C: m1: fails 0, margin 0.710; m2: fails 0, margin 0.697 (reference margin 0.707, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- A definition is a term with its meaning, from a `.sc/judge-jev/*.definitions.ttl` file (ADR-JEV-0008).
- It is attached to a record, or to a record and a location (the file, Markdown section or code symbol being judged).
- A request's state is the data it sends to Jev next to the questions, which holds the record.
- The size limit of a request is 24000 bytes.
- A definition's digest is the SHA-256 of its term, text and source.

## Definitions added or reworded (greedy -> final)

- It is attached to a record, or to a record and a location.
- A request's state is the data it sends.
- The size limit is 24000 bytes.
- A definition's digest is the SHA-256.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -4,10 +4,14 @@
 
 ### Requirement Statement
 
+Definitions: It is attached to a record, or to a record and a location. A
+request's state is the data it sends. The size limit is 24000 bytes. A
+definition's digest is the SHA-256.
+
 **MUST statements:**
 - A definition MUST be attachable to a record alone, or to a record and
   one location under evaluation.
-- A request about a record MUST carry, in its state next to the record, only
+- A request about a record MUST carry, in its state, only
   the definitions attached to that record alone, plus those attached to
   that record and the request's location.
 - A request with no matching definition MUST be identical to the request

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,17 +4,14 @@
 
 ### Requirement Statement
 
-Definitions: A definition is a term with its meaning, from a
-`.sc/judge-jev/*.definitions.ttl` file (ADR-JEV-0008). It is attached to a
-record, or to a record and a location (the file, Markdown section or code
-symbol being judged). A request's state is the data it sends to Jev next to
-the questions, which holds the record. The size limit of a request is 24000
-bytes. A definition's digest is the SHA-256 of its term, text and source.
+Definitions: It is attached to a record, or to a record and a location. A
+request's state is the data it sends. The size limit is 24000 bytes. A
+definition's digest is the SHA-256.
 
 **MUST statements:**
 - A definition MUST be attachable to a record alone, or to a record and
   one location under evaluation.
-- A request about a record MUST carry, in its state next to the record, only
+- A request about a record MUST carry, in its state, only
   the definitions attached to that record alone, plus those attached to
   that record and the request's location.
 - A request with no matching definition MUST be identical to the request

```

## Original text

````markdown
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
````

## Final text

````markdown
## REQ-JEV-0212: Targeted definitions

**Status:** Draft  

### Requirement Statement

Definitions: It is attached to a record, or to a record and a location. A
request's state is the data it sends. The size limit is 24000 bytes. A
definition's digest is the SHA-256.

**MUST statements:**
- A definition MUST be attachable to a record alone, or to a record and
  one location under evaluation.
- A request about a record MUST carry, in its state, only
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
````
