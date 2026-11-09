# REQ-JEV-0202

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [3, 3, 3, 3, 3, 3] | 6/6 | 0.711 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.748 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.747 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.738; final fails [0, 0, 0] margin 0.744.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.7416; pruned 0 failing runs, margin 0.7507).

## Kept tweaks (text present in the final record) and measured effect

- remove defs (proposed by i1:mechanical)
  - old: `A Jev request is one call to it.`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.737; m2: fails 0, margin 0.724 (reference margin 0.744, reference fails mean 0.00)
- remove defs (proposed by i1:mechanical)
  - old: `A pair is one (record, location) pair.`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.764; m2: fails 0, margin 0.747 (reference margin 0.744, reference fails mean 0.00)
- remove defs (proposed by i1:haiku-B)
  - old: `: it answers each multiple-choice question about a text with one choice and a confidence from 0 to 1`
  - new: `(removed)`
  - i1 haiku-B: m1: fails 0, margin 0.763; m2: fails 0, margin 0.746 (reference margin 0.744, reference fails mean 0.00)
- reword defs (proposed by i2:haiku-B)
  - old: `one per pair (REQ-JEV-0002).`
  - new: `one per pair.`
  - i2 haiku-B: m1: fails 0, margin 0.734; m2: fails 0, margin 0.747 (reference margin 0.720, reference fails mean 0.00)
- reword defs (proposed by i2:haiku-B)
  - old: `judged against a record (REQ-JEV-0207).`
  - new: `judged against a record.`
  - i2 haiku-B: m1: fails 0, margin 0.760; m2: fails 0, margin 0.733 (reference margin 0.720, reference fails mean 0.00)
- reword defs (proposed by i2:opus-B)
  - old: `requirement (REQ), non-functional requirement (NFR) or architecture decision record (ADR) REQ, NFR and ADR are its record kinds.`
  - new: `requirement, non-functional requirement or architecture decision record.`
  - i2 opus-B: m1: fails 0, margin 0.739; m2: fails 0, margin 0.731 (reference margin 0.720, reference fails mean 0.00)
- reword defs (proposed by i2:opus-B)
  - old: `Jev is TypeSafe's hosted judge model.`
  - new: `Jev is the judge model.`
  - i2 opus-B: m1: fails 0, margin 0.727; m2: fails 0, margin 0.739 (reference margin 0.720, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- Jev is TypeSafe's hosted judge model: it answers each multiple-choice question about a text with one choice and a confidence from 0 to 1.
- A Jev request is one call to it.
- A record is one requirement (REQ), non-functional requirement (NFR) or architecture decision record (ADR) as Raptor imports it; REQ, NFR and ADR are its record kinds.
- A location is the text judged against a record: a whole file (`path`), a Markdown section (`path#Heading`) or a code symbol (`path::Symbol`) (REQ-JEV-0207).
- A pair is one (record, location) pair.
- A stream of single requests is a sequence of Jev requests, one per pair, sent one at a time through the batch command (REQ-JEV-0002).

## Definitions added or reworded (greedy -> final)

- Jev is the judge model.
- A record is one requirement, non-functional requirement or architecture decision record.
- A location is the text judged against a record.
- A stream of single requests is a sequence of Jev requests, one per pair.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -3,6 +3,11 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: Jev is the judge model. A record is one requirement,
+non-functional requirement or architecture decision record. A location is
+the text judged against a record. A stream of single requests is a sequence
+of Jev requests, one per pair.
 
 **MUST statements:**
 - Each Jev request MUST carry exactly one record.
@@ -11,9 +16,9 @@
 
 ### Rationale
 
-Jev judges one record and location at a time; packing records into one request hides
-which one failed. Batching is streaming single requests, which the batch
-command already does.
+Jev judges one record and location at a time; packing records into one
+request hides which one failed. Batching is streaming single requests, which
+the batch command already does.
 
 ### Success Criteria
 

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,16 +4,10 @@
 
 ### Requirement Statement
 
-Definitions: Jev is TypeSafe's hosted judge model: it answers each
-multiple-choice question about a text with one choice and a confidence from
-0 to 1. A Jev request is one call to it. A record is one requirement (REQ),
-non-functional requirement (NFR) or architecture decision record (ADR) as
-Raptor imports it; REQ, NFR and ADR are its record kinds. A location is the
-text judged against a record: a whole file (`path`), a Markdown section
-(`path#Heading`) or a code symbol (`path::Symbol`) (REQ-JEV-0207). A pair is
-one (record, location) pair. A stream of single requests is a sequence of
-Jev requests, one per pair, sent one at a time through the batch command
-(REQ-JEV-0002).
+Definitions: Jev is the judge model. A record is one requirement,
+non-functional requirement or architecture decision record. A location is
+the text judged against a record. A stream of single requests is a sequence
+of Jev requests, one per pair.
 
 **MUST statements:**
 - Each Jev request MUST carry exactly one record.
@@ -22,9 +16,9 @@
 
 ### Rationale
 
-Jev judges one record and location at a time; packing records into one request hides
-which one failed. Batching is streaming single requests, which the batch
-command already does.
+Jev judges one record and location at a time; packing records into one
+request hides which one failed. Batching is streaming single requests, which
+the batch command already does.
 
 ### Success Criteria
 

```

## Original text

````markdown
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
````

## Final text

````markdown
## REQ-JEV-0202: One record and one location per request

**Status:** Draft  

### Requirement Statement

Definitions: Jev is the judge model. A record is one requirement,
non-functional requirement or architecture decision record. A location is
the text judged against a record. A stream of single requests is a sequence
of Jev requests, one per pair.

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
````
