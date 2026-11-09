# REQ-JEV-0209

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [2, 2, 2, 2, 2, 2] | 6/6 | 0.701 |
| greedy | [1, 1, 1, 0, 0, 0] | 3/6 | 0.713 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.737 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 1, 1] margin 0.712; final fails [0, 0, 0] margin 0.743.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.7556; pruned 0 failing runs, margin 0.7381).

## Kept tweaks (text present in the final record) and measured effect

- cite s3 (proposed by i1:opus-C)
  - old: `Every record-kind flag of `judge-jev quality` MUST be repeatable.`
  - new: `Every record-kind flag of `judge-jev quality` (the flags the statement above lists) MUST be repeatable.`
  - i1 opus-C: m1: fails 0, margin 0.707; m2: fails 0, margin 0.687; m3: fails 0, margin 0.702; m4: fails 0, margin 0.691; m5: fails 0, margin 0.699; m6: fails 0, margin 0.701 (reference margin 0.714, reference fails mean 0.67)
- remove defs (proposed by i2:haiku-C)
  - old: `(`--run-name`)`
  - new: `(removed)`
  - i2 haiku-C: m1: fails 0, margin 0.755; m2: fails 0, margin 0.768 (reference margin 0.753, reference fails mean 0.00)
- remove defs (proposed by i2:haiku-C)
  - old: `one of `--req`, `--adr` and `--nfr`; it is`
  - new: `(removed)`
  - i2 haiku-C: m1: fails 0, margin 0.757; m2: fails 0, margin 0.744 (reference margin 0.753, reference fails mean 0.00)
- reword defs (proposed by i2:opus-C)
  - old: `A run name is the name every log event of one invocation carries`
  - new: `A run name is the name an invocation's log events carry`
  - i2 opus-C: m1: fails 0, margin 0.763; m2: fails 0, margin 0.760 (reference margin 0.753, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- A run name is the name every log event of one invocation carries (`--run-name`).

## Definitions added or reworded (greedy -> final)

- A run name is the name an invocation's log events carry.
- A record-kind flag is repeatable when one invocation may give it more than once.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -4,12 +4,17 @@
 
 ### Requirement Statement
 
+Definitions: A run name is the name an invocation's log events carry. A
+record-kind flag is repeatable when one invocation may give it more than
+once.
+
 **MUST statements:**
 - `judge-jev quality` MUST take one or more record ids.
 - `judge-jev quality` MUST take each record id with one record-kind flag:
   `--req` (requirement), `--adr` (architecture decision record) or `--nfr`
   (non-functional requirement).
-- Every record-kind flag of `judge-jev quality` MUST be repeatable.
+- Every record-kind flag of `judge-jev quality` (the flags the statement
+  above lists) MUST be repeatable.
 - `judge-jev quality` MUST judge each record with its kind's quality
   decision tree (REQ-JEV-0101).
 - All records of one `judge-jev quality` invocation MUST be logged under

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,15 +4,17 @@
 
 ### Requirement Statement
 
-Definitions: A run name is the name every log event of one invocation
-carries (`--run-name`).
+Definitions: A run name is the name an invocation's log events carry. A
+record-kind flag is repeatable when one invocation may give it more than
+once.
 
 **MUST statements:**
 - `judge-jev quality` MUST take one or more record ids.
 - `judge-jev quality` MUST take each record id with one record-kind flag:
   `--req` (requirement), `--adr` (architecture decision record) or `--nfr`
   (non-functional requirement).
-- Every record-kind flag of `judge-jev quality` MUST be repeatable.
+- Every record-kind flag of `judge-jev quality` (the flags the statement
+  above lists) MUST be repeatable.
 - `judge-jev quality` MUST judge each record with its kind's quality
   decision tree (REQ-JEV-0101).
 - All records of one `judge-jev quality` invocation MUST be logged under

```

## Original text

````markdown
## REQ-JEV-0209: Record quality command

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev quality` MUST take one or more record ids.
- `judge-jev quality` MUST take each record id with one record-kind flag:
  `--req` (requirement), `--adr` (architecture decision record) or `--nfr`
  (non-functional requirement).
- Every record-kind flag of `judge-jev quality` MUST be repeatable.
- `judge-jev quality` MUST judge each record with its kind's quality
  decision tree (REQ-JEV-0101).
- All records of one `judge-jev quality` invocation MUST be logged under
  one run name.

### Rationale

Quality and compliance are separate questions about separate inputs. One
run name per invocation groups a measurement over many records in the
log.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every request `judge-jev quality --req <id>` sends carries only the
  record and questions from the REQ quality tree.

---
````

## Final text

````markdown
## REQ-JEV-0209: Record quality command

**Status:** Draft  

### Requirement Statement

Definitions: A run name is the name an invocation's log events carry. A
record-kind flag is repeatable when one invocation may give it more than
once.

**MUST statements:**
- `judge-jev quality` MUST take one or more record ids.
- `judge-jev quality` MUST take each record id with one record-kind flag:
  `--req` (requirement), `--adr` (architecture decision record) or `--nfr`
  (non-functional requirement).
- Every record-kind flag of `judge-jev quality` (the flags the statement
  above lists) MUST be repeatable.
- `judge-jev quality` MUST judge each record with its kind's quality
  decision tree (REQ-JEV-0101).
- All records of one `judge-jev quality` invocation MUST be logged under
  one run name.

### Rationale

Quality and compliance are separate questions about separate inputs. One
run name per invocation groups a measurement over many records in the
log.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every request `judge-jev quality --req <id>` sends carries only the
  record and questions from the REQ quality tree.

---
````
