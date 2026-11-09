# REQ-JEV-0210

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [8, 7, 7, 7, 9, 7] | 6/6 | 0.639 |
| greedy | [0, 0, 0, 1, 0, 0] | 1/6 | 0.679 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.678 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [1, 0, 1] margin 0.686; final fails [0, 0, 0] margin 0.680.

Selection: fixes-only (paired runs: fixes-only 1 failing runs, margin 0.6774; pruned 0 failing runs, margin 0.6396).
Iteration 4 change adopted: iter1-haiku-C remove s2: eval 0/12 failing runs, margin 0.675 (control 2/12, 0.682); confirmation 0/12, margin 0.677 (control 1/12, 0.678). See iter4/eval.json, iter4/confirm.json.

## Kept tweaks (text present in the final record) and measured effect

- remove s2 (proposed by i1:haiku-C, i4:iter1-haiku-C)
  - old: ``--tree` (quality tree), `--questions` (question set), `--answers` (answers file), `--index` (Raptor import index) or `--requests` (batch request stream).`
  - new: ``--tree`, `--questions`, `--answers`, `--index` or `--requests`.`
  - i1 haiku-C: m1: fails 0, margin 0.666; m2: fails 0, margin 0.688 (reference margin 0.680, reference fails mean 0.00)
  - i4 iter1-haiku-C: 0/12 failing runs, margin 0.675; confirmation 0/12, margin 0.677

## Definitions pruned (greedy -> final)

None.

## Definitions added or reworded (greedy -> final)

None.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -4,12 +4,22 @@
 
 ### Requirement Statement
 
+Definitions: Jev is TypeSafe's hosted judge model: it answers each
+multiple-choice question about a text with one choice and a confidence from
+0 to 1. A Jev request is one call to it. The model for an input kind is the
+Pydantic model (a typed schema class) judge-jev validates that input with
+(ADR-JEV-0005). A field path is the dotted path of keys and list indexes to
+the refused field, such as `nodes.wave-1.questions.context.criteria`. An
+answers file is a JSON file of Jev's answers, keyed by request, that
+`--answers-file` gives judge-jev in place of a live call. Its envelope is
+its outer structure: its keys and the type of each value.
+`JEV.RESPONSE_INVALID` is the typed error code for an answer whose
+questions, choices or probabilities do not match the request.
+
 **MUST statements:**
 - `judge-jev validate` MUST take one input file.
 - `judge-jev validate` MUST take one input-kind flag with that file:
-  `--tree` (quality tree), `--questions` (question set), `--answers`
-  (answers file), `--index` (Raptor import index) or `--requests` (batch
-  request stream).
+  `--tree`, `--questions`, `--answers`, `--index` or `--requests`.
 - `judge-jev validate` MUST check the file with the model `judge-jev`
   applies to that input kind before its first Jev request (ADR-JEV-0005).
 - Every refusal from `judge-jev validate` MUST name the field path.

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -19,9 +19,7 @@
 **MUST statements:**
 - `judge-jev validate` MUST take one input file.
 - `judge-jev validate` MUST take one input-kind flag with that file:
-  `--tree` (quality tree), `--questions` (question set), `--answers`
-  (answers file), `--index` (Raptor import index) or `--requests` (batch
-  request stream).
+  `--tree`, `--questions`, `--answers`, `--index` or `--requests`.
 - `judge-jev validate` MUST check the file with the model `judge-jev`
   applies to that input kind before its first Jev request (ADR-JEV-0005).
 - Every refusal from `judge-jev validate` MUST name the field path.

```

## Original text

````markdown
## REQ-JEV-0210: Validate command

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev validate` MUST take one input file.
- `judge-jev validate` MUST take one input-kind flag with that file:
  `--tree` (quality tree), `--questions` (question set), `--answers`
  (answers file), `--index` (Raptor import index) or `--requests` (batch
  request stream).
- `judge-jev validate` MUST check the file with the model `judge-jev`
  applies to that input kind before its first Jev request (ADR-JEV-0005).
- Every refusal from `judge-jev validate` MUST name the field path.
- Every refusal from `judge-jev validate` MUST name the rule the field
  breaks.
- `judge-jev validate --answers` MUST apply the answers-file envelope that
  `--answers-file` applies before the first request.
- The answers-file envelope MUST require an object of string keys.
- The answers-file envelope MUST require each key's value to be an object
  or a non-empty list of objects.
- The answers-file envelope MUST require an object with `__error__` to hold
  only a string code of at most 64 characters.

**MUST NOT statements:**
- `judge-jev validate` MUST NOT call Jev.

### Rationale

A tree variation checked before a run costs nothing; one refused after a
paid call wastes it.

The answers file stands in for Jev's response, so what an answer holds
(its questions, choices and probabilities) is not part of the envelope; it
is checked after the send as `JEV.RESPONSE_INVALID`.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every input the sweep tests refuse in `quality` is refused by
  `judge-jev validate` with the same field path.
- [ ] The shipped trees and question sets pass `judge-jev validate`.

---
````

## Final text

````markdown
## REQ-JEV-0210: Validate command

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. The model for an input kind is the
Pydantic model (a typed schema class) judge-jev validates that input with
(ADR-JEV-0005). A field path is the dotted path of keys and list indexes to
the refused field, such as `nodes.wave-1.questions.context.criteria`. An
answers file is a JSON file of Jev's answers, keyed by request, that
`--answers-file` gives judge-jev in place of a live call. Its envelope is
its outer structure: its keys and the type of each value.
`JEV.RESPONSE_INVALID` is the typed error code for an answer whose
questions, choices or probabilities do not match the request.

**MUST statements:**
- `judge-jev validate` MUST take one input file.
- `judge-jev validate` MUST take one input-kind flag with that file:
  `--tree`, `--questions`, `--answers`, `--index` or `--requests`.
- `judge-jev validate` MUST check the file with the model `judge-jev`
  applies to that input kind before its first Jev request (ADR-JEV-0005).
- Every refusal from `judge-jev validate` MUST name the field path.
- Every refusal from `judge-jev validate` MUST name the rule the field
  breaks.
- `judge-jev validate --answers` MUST apply the answers-file envelope that
  `--answers-file` applies before the first request.
- The answers-file envelope MUST require an object of string keys.
- The answers-file envelope MUST require each key's value to be an object
  or a non-empty list of objects.
- The answers-file envelope MUST require an object with `__error__` to hold
  only a string code of at most 64 characters.

**MUST NOT statements:**
- `judge-jev validate` MUST NOT call Jev.

### Rationale

A tree variation checked before a run costs nothing; one refused after a
paid call wastes it.

The answers file stands in for Jev's response, so what an answer holds
(its questions, choices and probabilities) is not part of the envelope; it
is checked after the send as `JEV.RESPONSE_INVALID`.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every input the sweep tests refuse in `quality` is refused by
  `judge-jev validate` with the same field path.
- [ ] The shipped trees and question sets pass `judge-jev validate`.

---
````
