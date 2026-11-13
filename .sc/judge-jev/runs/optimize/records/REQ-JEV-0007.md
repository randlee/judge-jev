# REQ-JEV-0007

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [1, 1, 1, 1, 1, 1] | 6/6 | 0.731 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.652 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.649 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.615; final fails [0, 0, 0] margin 0.627.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.6422; pruned 0 failing runs, margin 0.6306).

## Kept tweaks (text present in the final record) and measured effect

- remove defs (proposed by i1:mechanical)
  - old: `Raptor is the requirements tool that imports Markdown records.`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.693; m2: fails 0, margin 0.593 (reference margin 0.638, reference fails mean 0.00)
- remove defs (proposed by i1:haiku-A)
  - old: `, such as `UNKNOWN_SECTION``
  - new: `(removed)`
  - i1 haiku-A: m1: fails 0, margin 0.680; m2: fails 0, margin 0.615 (reference margin 0.638, reference fails mean 0.00)
- remove defs (proposed by i2:haiku-A)
  - old: `for a record`
  - new: `(removed)`
  - i2 haiku-A: m1: fails 0, margin 0.615; m2: fails 0, margin 0.640 (reference margin 0.653, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- Raptor is the requirements tool that imports Markdown records.
- An issue is a diagnostic Raptor's import reports for a record, such as `UNKNOWN_SECTION`.

## Definitions added or reworded (greedy -> final)

- An issue is a diagnostic Raptor's import reports.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -3,6 +3,8 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: An issue is a diagnostic Raptor's import reports.
 
 **MUST statements:**
 

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,9 +4,7 @@
 
 ### Requirement Statement
 
-Definitions: Raptor is the requirements tool that imports Markdown records.
-An issue is a diagnostic Raptor's import reports for a record, such as
-`UNKNOWN_SECTION`.
+Definitions: An issue is a diagnostic Raptor's import reports.
 
 **MUST statements:**
 

```

## Original text

````markdown
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
````

## Final text

````markdown
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
````
