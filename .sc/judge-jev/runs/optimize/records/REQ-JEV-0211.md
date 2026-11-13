# REQ-JEV-0211

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [4, 4, 4, 4, 4, 4] | 6/6 | 0.539 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.610 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.706 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.583; final fails [0, 0, 0] margin 0.717.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.712; pruned 0 failing runs, margin 0.6815).

## Kept tweaks (text present in the final record) and measured effect

- split s3 (proposed by i1:opus-C)
  - old: `- `judge-jev` MUST refuse an invalid tree, question set, index, request stream or run directory before its first Jev request.`
  - new: `- `judge-jev` MUST refuse an invalid tree before its first Jev request. - `judge-jev` MUST refuse an invalid question set before its first Jev request. - `judge-jev` MUST refuse an invalid index before its first Jev request. - `judge-jev` MUST refuse an invalid request stream before its first Jev request. - `judge-jev` MUST refuse an invalid run directory before its first Jev request.`
  - i1 opus-C: m1: fails 0, margin 0.707; m2: fails 0, margin 0.697; m3: fails 0, margin 0.711; m4: fails 0, margin 0.683; m5: fails 0, margin 0.711; m6: fails 0, margin 0.700 (reference margin 0.614, reference fails mean 0.33)
- define defs (proposed by i1:sonnet-C)
  - old: `A log event is one event`
  - new: `An input is a tree, question set, index, request stream or run directory. A log event is one event`
  - i1 sonnet-C: m1: fails 0, margin 0.619; m2: fails 0, margin 0.607; m3: fails 0, margin 0.593; m4: fails 0, margin 0.603; m5: fails 0, margin 0.669; m6: fails 0, margin 0.671 (reference margin 0.614, reference fails mean 0.33)

## Definitions pruned (greedy -> final)

None.

## Definitions added or reworded (greedy -> final)

- An input is a tree, question set, index, request stream or run directory.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -4,13 +4,32 @@
 
 ### Requirement Statement
 
+Definitions: Jev is TypeSafe's hosted judge model: it answers each
+multiple-choice question about a text with one choice and a confidence from
+0 to 1. A Jev request is one call to it. A `judge-jev` command's result is
+the JSON object it prints on success. A typed error is a JSON error object
+with a stable `code` (such as `INPUT.MALFORMED`), a `message` and a
+`suggested_action`. A tree is a quality decision tree file, a question set a
+file of questions, an index a Raptor import index, a request stream the
+request lines of the batch command, and a run directory the folder that
+holds a run's log. An input is a tree, question set, index, request stream
+or run directory. A log event is one event written through the
+sc-observability logger; the logger's event size limit is 65536 bytes
+(sc-observability 1.5.0).
+
 **MUST statements:**
 - For every input, every `judge-jev` command MUST print exactly one JSON
   object.
 - The JSON object a `judge-jev` command prints MUST be its result or a
   typed error.
-- `judge-jev` MUST refuse an invalid tree, question set, index, request
-  stream or run directory before its first Jev request.
+- `judge-jev` MUST refuse an invalid tree before its first Jev request.
+- `judge-jev` MUST refuse an invalid question set before its first Jev
+  request.
+- `judge-jev` MUST refuse an invalid index before its first Jev request.
+- `judge-jev` MUST refuse an invalid request stream before its first Jev
+  request.
+- `judge-jev` MUST refuse an invalid run directory before its first Jev
+  request.
 - `judge-jev` MUST check that every log event of a request (the request,
   Jev's largest possible answer and the result) fits the logger's event
   size limit before sending the request.

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -12,7 +12,8 @@
 `suggested_action`. A tree is a quality decision tree file, a question set a
 file of questions, an index a Raptor import index, a request stream the
 request lines of the batch command, and a run directory the folder that
-holds a run's log. A log event is one event written through the
+holds a run's log. An input is a tree, question set, index, request stream
+or run directory. A log event is one event written through the
 sc-observability logger; the logger's event size limit is 65536 bytes
 (sc-observability 1.5.0).
 
@@ -21,8 +22,14 @@
   object.
 - The JSON object a `judge-jev` command prints MUST be its result or a
   typed error.
-- `judge-jev` MUST refuse an invalid tree, question set, index, request
-  stream or run directory before its first Jev request.
+- `judge-jev` MUST refuse an invalid tree before its first Jev request.
+- `judge-jev` MUST refuse an invalid question set before its first Jev
+  request.
+- `judge-jev` MUST refuse an invalid index before its first Jev request.
+- `judge-jev` MUST refuse an invalid request stream before its first Jev
+  request.
+- `judge-jev` MUST refuse an invalid run directory before its first Jev
+  request.
 - `judge-jev` MUST check that every log event of a request (the request,
   Jev's largest possible answer and the result) fits the logger's event
   size limit before sending the request.

```

## Original text

````markdown
## REQ-JEV-0211: A typed result for every input

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- For every input, every `judge-jev` command MUST print exactly one JSON
  object.
- The JSON object a `judge-jev` command prints MUST be its result or a
  typed error.
- `judge-jev` MUST refuse an invalid tree, question set, index, request
  stream or run directory before its first Jev request.
- `judge-jev` MUST check that every log event of a request (the request,
  Jev's largest possible answer and the result) fits the logger's event
  size limit before sending the request.

### Rationale

Rand Lee, 2026-11-08: "Crash is not acceptable for any input." A refusal
after a paid call wastes the call; a crash loses its answer.

### Success Criteria

**Acceptance Criteria:**
- [ ] The sweep tests (every field of a tree, index and answers file
  replaced by each of a fixed list of wrong values, deleted or given an
  extra key, and raw JSON no value expresses) produce no `SCRIPT.INTERNAL`
  and no refusal after a request is sent.
- [ ] Invalid UTF-8 on stdin is refused with `INPUT.MALFORMED`.

---
````

## Final text

````markdown
## REQ-JEV-0211: A typed result for every input

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. A `judge-jev` command's result is
the JSON object it prints on success. A typed error is a JSON error object
with a stable `code` (such as `INPUT.MALFORMED`), a `message` and a
`suggested_action`. A tree is a quality decision tree file, a question set a
file of questions, an index a Raptor import index, a request stream the
request lines of the batch command, and a run directory the folder that
holds a run's log. An input is a tree, question set, index, request stream
or run directory. A log event is one event written through the
sc-observability logger; the logger's event size limit is 65536 bytes
(sc-observability 1.5.0).

**MUST statements:**
- For every input, every `judge-jev` command MUST print exactly one JSON
  object.
- The JSON object a `judge-jev` command prints MUST be its result or a
  typed error.
- `judge-jev` MUST refuse an invalid tree before its first Jev request.
- `judge-jev` MUST refuse an invalid question set before its first Jev
  request.
- `judge-jev` MUST refuse an invalid index before its first Jev request.
- `judge-jev` MUST refuse an invalid request stream before its first Jev
  request.
- `judge-jev` MUST refuse an invalid run directory before its first Jev
  request.
- `judge-jev` MUST check that every log event of a request (the request,
  Jev's largest possible answer and the result) fits the logger's event
  size limit before sending the request.

### Rationale

Rand Lee, 2026-11-08: "Crash is not acceptable for any input." A refusal
after a paid call wastes the call; a crash loses its answer.

### Success Criteria

**Acceptance Criteria:**
- [ ] The sweep tests (every field of a tree, index and answers file
  replaced by each of a fixed list of wrong values, deleted or given an
  extra key, and raw JSON no value expresses) produce no `SCRIPT.INTERNAL`
  and no refusal after a request is sent.
- [ ] Invalid UTF-8 on stdin is refused with `INPUT.MALFORMED`.

---
````
