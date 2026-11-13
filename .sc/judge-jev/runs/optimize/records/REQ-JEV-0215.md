# REQ-JEV-0215

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [9, 9, 9, 9, 9, 9] | 6/6 | 0.708 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.822 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.826 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [1, 0, 0] margin 0.829; final fails [0, 0, 0] margin 0.829.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.8281; pruned 0 failing runs, margin 0.8043).

## Kept tweaks (text present in the final record) and measured effect

- reword s4 (proposed by i1:opus-C)
  - old: `MUST validate every tree, question set and definitions file in the scope against the ontology's shapes, including edges and cycles.`
  - new: `MUST validate every file in the scope against the ontology's shapes, including edges and cycles.`
  - i1 opus-C: m1: fails 0, margin 0.829; m2: fails 0, margin 0.825; m3: fails 0, margin 0.819; m4: fails 0, margin 0.820; m5: fails 0, margin 0.828; m6: fails 0, margin 0.828 (reference margin 0.827, reference fails mean 0.67)

## Definitions pruned (greedy -> final)

None.

## Definitions added or reworded (greedy -> final)

None.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -3,6 +3,21 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: Jev is TypeSafe's hosted judge model: it answers each
+multiple-choice question about a text with one choice and a confidence from
+0 to 1. A Jev request is one call to it. The scope is the trees and question
+sets shipped with judge-jev, the tree and definitions files at the top level
+of `.sc/judge-jev/`, and each path given to `judge-jev doctor`. A tree is a
+quality decision tree file; a question set is a file of questions; a
+definitions file is a `.definitions.ttl` file of definitions, each a term
+with its meaning and the `source` file it comes from. A file's schema is the
+model that checks its fields. The ontology's shapes are the SHACL (Shapes
+Constraint Language) files in `assets/shapes/`; an edge is a link from one
+node of a tree to another, and a cycle is a chain of edges that leads back
+to its start. An attachment links a definition to a record, or to a record
+and a location (a file, Markdown section or code symbol). The Raptor index
+is the record file Raptor's import writes.
 
 **MUST statements:**
 - `judge-jev doctor` MUST validate every tree in the scope against its
@@ -11,9 +26,8 @@
   its schema.
 - `judge-jev doctor` MUST validate every definitions file in the scope
   against its schema.
-- `judge-jev doctor` MUST validate every tree, question set and definitions
-  file in the scope against the ontology's shapes, including edges and
-  cycles.
+- `judge-jev doctor` MUST validate every file in the scope against the
+  ontology's shapes, including edges and cycles.
 - `judge-jev doctor` MUST report each validation failure as an error.
 - `judge-jev doctor` MUST report a definition with no attachment as a
   warning.

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -26,9 +26,8 @@
   its schema.
 - `judge-jev doctor` MUST validate every definitions file in the scope
   against its schema.
-- `judge-jev doctor` MUST validate every tree, question set and definitions
-  file in the scope against the ontology's shapes, including edges and
-  cycles.
+- `judge-jev doctor` MUST validate every file in the scope against the
+  ontology's shapes, including edges and cycles.
 - `judge-jev doctor` MUST report each validation failure as an error.
 - `judge-jev doctor` MUST report a definition with no attachment as a
   warning.

```

## Original text

````markdown
## REQ-JEV-0215: Doctor command

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev doctor` MUST validate every tree in the scope against its
  schema.
- `judge-jev doctor` MUST validate every question set in the scope against
  its schema.
- `judge-jev doctor` MUST validate every definitions file in the scope
  against its schema.
- `judge-jev doctor` MUST validate every tree, question set and definitions
  file in the scope against the ontology's shapes, including edges and
  cycles.
- `judge-jev doctor` MUST report each validation failure as an error.
- `judge-jev doctor` MUST report a definition with no attachment as a
  warning.
- `judge-jev doctor` MUST report an attachment to a record the Raptor index
  does not hold as a warning.
- `judge-jev doctor` MUST report an attachment to a location that does not
  exist as a warning.
- `judge-jev doctor` MUST report a definition whose source does not exist
  as a warning.

**MUST NOT statements:**
- `judge-jev doctor` MUST NOT call Jev.
- A `judge-jev doctor` warning MUST NOT fail the command.

### Rationale

Rand Lee, 2026-11-08: "I would expect judge-jev doctor to report orphans/dead
links as warnings, it would also run schema validation and verify ontology
followed and no cycles."

### Success Criteria

**Acceptance Criteria:**
- [ ] A scope with one orphan definition exits 0 with one warning naming it.
- [ ] A scope with a tree that has a cycle exits non-zero with an error
  naming the cycle.
````

## Final text

````markdown
## REQ-JEV-0215: Doctor command

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. The scope is the trees and question
sets shipped with judge-jev, the tree and definitions files at the top level
of `.sc/judge-jev/`, and each path given to `judge-jev doctor`. A tree is a
quality decision tree file; a question set is a file of questions; a
definitions file is a `.definitions.ttl` file of definitions, each a term
with its meaning and the `source` file it comes from. A file's schema is the
model that checks its fields. The ontology's shapes are the SHACL (Shapes
Constraint Language) files in `assets/shapes/`; an edge is a link from one
node of a tree to another, and a cycle is a chain of edges that leads back
to its start. An attachment links a definition to a record, or to a record
and a location (a file, Markdown section or code symbol). The Raptor index
is the record file Raptor's import writes.

**MUST statements:**
- `judge-jev doctor` MUST validate every tree in the scope against its
  schema.
- `judge-jev doctor` MUST validate every question set in the scope against
  its schema.
- `judge-jev doctor` MUST validate every definitions file in the scope
  against its schema.
- `judge-jev doctor` MUST validate every file in the scope against the
  ontology's shapes, including edges and cycles.
- `judge-jev doctor` MUST report each validation failure as an error.
- `judge-jev doctor` MUST report a definition with no attachment as a
  warning.
- `judge-jev doctor` MUST report an attachment to a record the Raptor index
  does not hold as a warning.
- `judge-jev doctor` MUST report an attachment to a location that does not
  exist as a warning.
- `judge-jev doctor` MUST report a definition whose source does not exist
  as a warning.

**MUST NOT statements:**
- `judge-jev doctor` MUST NOT call Jev.
- A `judge-jev doctor` warning MUST NOT fail the command.

### Rationale

Rand Lee, 2026-11-08: "I would expect judge-jev doctor to report orphans/dead
links as warnings, it would also run schema validation and verify ontology
followed and no cycles."

### Success Criteria

**Acceptance Criteria:**
- [ ] A scope with one orphan definition exits 0 with one warning naming it.
- [ ] A scope with a tree that has a cycle exits non-zero with an error
  naming the cycle.
````
