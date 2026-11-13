# REQ-JEV-0214

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [2, 2, 2, 2, 2, 2] | 6/6 | 0.529 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.534 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.538 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.548; final fails [0, 0, 0] margin 0.539.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.5381; pruned 1 failing runs, margin 0.6436).

## Kept tweaks (text present in the final record) and measured effect

None: the final text equals the greedy text.

## Definitions pruned (greedy -> final)

None.

## Definitions added or reworded (greedy -> final)

None.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -3,6 +3,12 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: A question IRI (Internationalized Resource Identifier) is the
+URN that names a question, such as `urn:judge-jev:question:req.term`. A tree
+file is a Turtle file of quality decision trees. A consumer extension is a
+tree file that a repository using judge-jev adds. `jj:id` is a question's
+short id within its tree.
 
 **MUST statements:**
 - Every question IRI in one scope (by default the repository) MUST be

```

## Diff: greedy (previous commit) -> final

```diff
(no change)
```

## Original text

````markdown
## REQ-JEV-0214: Question ids are unique within a scope

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- Every question IRI in one scope (by default the repository) MUST be
  declared in one tree file only, across judge-jev's trees and every
  consumer extension's.
- Every `jj:id` in judge-jev's trees and in every consumer extension's
  MUST be unique within its tree.

### Rationale

A question's identity is its IRI.

Rand Lee, 2026-11-08: "We would need to make sure all questions in
judge-jev AND in consumer extensions follow a naming policy for uniqueness
w/in that scope (repo is typical scope)."

### Success Criteria

**Acceptance Criteria:**
- [ ] A question IRI declared in two tree files of one scope is reported
  as an error naming both files; two questions of one tree with the same
  `jj:id` are an error.

---
````

## Final text

````markdown
## REQ-JEV-0214: Question ids are unique within a scope

**Status:** Draft  

### Requirement Statement

Definitions: A question IRI (Internationalized Resource Identifier) is the
URN that names a question, such as `urn:judge-jev:question:req.term`. A tree
file is a Turtle file of quality decision trees. A consumer extension is a
tree file that a repository using judge-jev adds. `jj:id` is a question's
short id within its tree.

**MUST statements:**
- Every question IRI in one scope (by default the repository) MUST be
  declared in one tree file only, across judge-jev's trees and every
  consumer extension's.
- Every `jj:id` in judge-jev's trees and in every consumer extension's
  MUST be unique within its tree.

### Rationale

A question's identity is its IRI.

Rand Lee, 2026-11-08: "We would need to make sure all questions in
judge-jev AND in consumer extensions follow a naming policy for uniqueness
w/in that scope (repo is typical scope)."

### Success Criteria

**Acceptance Criteria:**
- [ ] A question IRI declared in two tree files of one scope is reported
  as an error naming both files; two questions of one tree with the same
  `jj:id` are an error.

---
````
