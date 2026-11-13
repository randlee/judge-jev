# REQ-JEV-0201

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [2, 2, 2, 2, 2, 2] | 6/6 | 0.652 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.697 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.686 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.687; final fails [0, 0, 0] margin 0.687.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.6958; pruned 0 failing runs, margin 0.6847).

## Kept tweaks (text present in the final record) and measured effect

- remove defs (proposed by i1:mechanical)
  - old: `A mode (target mode) names what a location holds: `prompt` (prompt text), `skill` (a skill file), `task` (a task template) or `code` (source code).`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.686; m2: fails 0, margin 0.700 (reference margin 0.686, reference fails mean 0.00)
- reword defs (proposed by i2:haiku-B)
  - old: `against a record: a whole file (`path`), a Markdown section (`path#Heading`) or a code symbol (`path::Symbol`) (REQ-JEV-0207).`
  - new: `against a record.`
  - i2 haiku-B: m1: fails 0, margin 0.693; m2: fails 0, margin 0.704 (reference margin 0.673, reference fails mean 0.00)
- reword defs (proposed by i2:haiku-B)
  - old: `check (REQ-JEV-0204).`
  - new: `check.`
  - i2 haiku-B: m1: fails 0, margin 0.679; m2: fails 0, margin 0.683 (reference margin 0.673, reference fails mean 0.00)
- reword defs (proposed by i2:opus-B)
  - old: `one requirement (REQ), non-functional requirement (NFR) or architecture decision record (ADR) REQ, NFR and ADR are its record kinds.`
  - new: `one requirement, non-functional requirement or architecture decision record; these are its record kinds.`
  - i2 opus-B: m1: fails 0, margin 0.688; m2: fails 0, margin 0.673 (reference margin 0.673, reference fails mean 0.00)
- reword defs (proposed by i2:sonnet-B)
  - old: `a TOML file listing locations to check`
  - new: `a file listing locations to check`
  - i2 sonnet-B: m1: fails 0, margin 0.665; m2: fails 0, margin 0.687 (reference margin 0.673, reference fails mean 0.00)
- remove defs (proposed by i2:sonnet-B)
  - old: `for one record kind and target class`
  - new: `(removed)`
  - i2 sonnet-B: m1: fails 0, margin 0.664; m2: fails 0, margin 0.678 (reference margin 0.673, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- A record is one requirement (REQ), non-functional requirement (NFR) or architecture decision record (ADR) as Raptor imports it; REQ, NFR and ADR are its record kinds.
- A location is the text judged against a record: a whole file (`path`), a Markdown section (`path#Heading`) or a code symbol (`path::Symbol`) (REQ-JEV-0207).
- A mode (target mode) names what a location holds: `prompt` (prompt text), `skill` (a skill file), `task` (a task template) or `code` (source code).
- A question set is the data file of questions judge-jev sends to Jev about a location for one record kind and target class.
- `--profile` names a profile: a TOML file listing locations, each with its mode and the ids of the records that govern it (REQ-JEV-0204).

## Definitions added or reworded (greedy -> final)

- A record is one requirement, non-functional requirement or architecture decision record; these are its record kinds.
- A location is the text judged against a record.
- A question set is the data file of questions judge-jev sends to Jev about a location.
- `--profile` names a profile: a file listing locations to check.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -3,6 +3,12 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: A record is one requirement, non-functional requirement or
+architecture decision record; these are its record kinds. A location is the
+text judged against a record. A question set is the data file of questions
+judge-jev sends to Jev about a location. `--profile` names a profile: a file
+listing locations to check.
 
 **MUST statements:**
 - `judge-jev check` MUST take one of two argument forms: a single record

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,16 +4,11 @@
 
 ### Requirement Statement
 
-Definitions: A record is one requirement (REQ), non-functional requirement
-(NFR) or architecture decision record (ADR) as Raptor imports it; REQ, NFR
-and ADR are its record kinds. A location is the text judged against a
-record: a whole file (`path`), a Markdown section (`path#Heading`) or a code
-symbol (`path::Symbol`) (REQ-JEV-0207). A mode (target mode) names what a
-location holds: `prompt` (prompt text), `skill` (a skill file), `task` (a
-task template) or `code` (source code). A question set is the data file of
-questions judge-jev sends to Jev about a location for one record kind and
-target class. `--profile` names a profile: a TOML file listing locations,
-each with its mode and the ids of the records that govern it (REQ-JEV-0204).
+Definitions: A record is one requirement, non-functional requirement or
+architecture decision record; these are its record kinds. A location is the
+text judged against a record. A question set is the data file of questions
+judge-jev sends to Jev about a location. `--profile` names a profile: a file
+listing locations to check.
 
 **MUST statements:**
 - `judge-jev check` MUST take one of two argument forms: a single record

```

## Original text

````markdown
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
````

## Final text

````markdown
## REQ-JEV-0201: One record per check

**Status:** Draft  

### Requirement Statement

Definitions: A record is one requirement, non-functional requirement or
architecture decision record; these are its record kinds. A location is the
text judged against a record. A question set is the data file of questions
judge-jev sends to Jev about a location. `--profile` names a profile: a file
listing locations to check.

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
````
