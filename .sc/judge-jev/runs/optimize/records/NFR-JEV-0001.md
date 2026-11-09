# NFR-JEV-0001

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [1, 1, 1, 1, 1, 1] | 6/6 | 0.689 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.769 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.750 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.771; final fails [0, 0, 0] margin 0.759.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.7583; pruned 0 failing runs, margin 0.7423).

## Kept tweaks (text present in the final record) and measured effect

- remove defs (proposed by i1:haiku-A)
  - old: `: it answers each multiple-choice question about a text with one choice and a confidence from 0 to 1. A Jev request is one call to it.`
  - new: `.`
  - i1 haiku-A: m1: fails 0, margin 0.776; m2: fails 0, margin 0.757 (reference margin 0.760, reference fails mean 0.00)
- remove defs (proposed by i1:haiku-A)
  - old: `in place of a live Jev call`
  - new: `(removed)`
  - i1 haiku-A: m1: fails 0, margin 0.764; m2: fails 0, margin 0.741 (reference margin 0.760, reference fails mean 0.00)
- remove defs (proposed by i2:haiku-A)
  - old: `(`--answers-file`)`
  - new: `(removed)`
  - i2 haiku-A: m1: fails 0, margin 0.736; m2: fails 0, margin 0.744 (reference margin 0.746, reference fails mean 0.00)
- remove defs (proposed by i2:haiku-A)
  - old: `: JSON answers given to judge-jev`
  - new: `(removed)`
  - i2 haiku-A: m1: fails 0, margin 0.759; m2: fails 0, margin 0.768 (reference margin 0.746, reference fails mean 0.00)
- reword defs (proposed by i2:opus-A)
  - old: `Jev is TypeSafe's hosted judge model.`
  - new: `Jev is a judge model.`
  - i2 opus-A: m1: fails 0, margin 0.748; m2: fails 0, margin 0.748 (reference margin 0.746, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- Jev is TypeSafe's hosted judge model: it answers each multiple-choice question about a text with one choice and a confidence from 0 to 1.
- A Jev request is one call to it.
- Recorded Jev answers are an answers file (`--answers-file`): JSON answers given to judge-jev in place of a live Jev call.

## Definitions added or reworded (greedy -> final)

- Jev is a judge model.
- Recorded Jev answers are an answers file.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -3,6 +3,8 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: Jev is a judge model. Recorded Jev answers are an answers file.
 
 **MUST statements:**
 

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,11 +4,7 @@
 
 ### Requirement Statement
 
-Definitions: Jev is TypeSafe's hosted judge model: it answers each
-multiple-choice question about a text with one choice and a confidence from
-0 to 1. A Jev request is one call to it. Recorded Jev answers are an answers
-file (`--answers-file`): JSON answers given to judge-jev in place of a live
-Jev call.
+Definitions: Jev is a judge model. Recorded Jev answers are an answers file.
 
 **MUST statements:**
 

```

## Original text

````markdown
## NFR-JEV-0001: Deterministic offline tests

**Status:** Draft  

### Requirement Statement

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
````

## Final text

````markdown
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
````
