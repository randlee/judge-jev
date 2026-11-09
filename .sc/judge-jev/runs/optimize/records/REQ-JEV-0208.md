# REQ-JEV-0208

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [12, 11, 12, 12, 12, 12] | 6/6 | 0.680 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.802 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.792 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.801; final fails [0, 0, 0] margin 0.796.

Selection: pruned (paired runs: fixes-only 2 failing runs, margin 0.8031; pruned 1 failing runs, margin 0.7905).
Iteration 4 change adopted: sonnet-G reword s3: eval: not run (author-rejected, then readmitted); confirmation 0/12, margin 0.792 (control 1/12, 0.790). See iter4/eval.json, iter4/confirm.json.

## Kept tweaks (text present in the final record) and measured effect

- remove defs (proposed by i1:mechanical)
  - old: `A Jev request is one call to it.`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.810; m2: fails 0, margin 0.803 (reference margin 0.801, reference fails mean 0.00)
- remove defs (proposed by i1:mechanical)
  - old: `A dry-run entry is its report of one request a live run would send.`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.803; m2: fails 0, margin 0.805 (reference margin 0.801, reference fails mean 0.00)
- remove defs (proposed by i1:mechanical)
  - old: `A composed request is the full JSON body judge-jev would send to Jev.`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.800; m2: fails 0, margin 0.806 (reference margin 0.801, reference fails mean 0.00)
- remove defs (proposed by i1:mechanical)
  - old: `The record's Raptor source is the Raptor index the record was read from.`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.802; m2: fails 0, margin 0.802 (reference margin 0.801, reference fails mean 0.00)
- remove defs (proposed by i1:mechanical)
  - old: `A location (resolved: its path, section or symbol) is the text judged against a record: a whole file (`path`), a Markdown section (`path#Heading`) or a code symbol (`path::Symbol`) (REQ-JEV-0207).`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.798; m2: fails 0, margin 0.795 (reference margin 0.801, reference fails mean 0.00)
- remove defs (proposed by i1:mechanical)
  - old: `A typed error is a JSON error object with a stable `code` (such as `INPUT.MALFORMED`), a `message` and a `suggested_action`.`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.798; m2: fails 0, margin 0.794 (reference margin 0.801, reference fails mean 0.00)
- remove defs (proposed by i1:opus-B)
  - old: `into its record store and serves them to other tools`
  - new: `(removed)`
  - i1 opus-B: m1: fails 0, margin 0.801; m2: fails 0, margin 0.802 (reference margin 0.801, reference fails mean 0.00)
- remove defs (proposed by i1:sonnet-B)
  - old: `, with rules that turn Jev's answers into the next wave or a verdict (REQ-JEV-0101)`
  - new: `(REQ-JEV-0101)`
  - i1 sonnet-B: m1: fails 0, margin 0.807; m2: fails 0, margin 0.806 (reference margin 0.801, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- A Jev request is one call to it.
- Raptor is the requirements tool that imports Markdown records into its record store and serves them to other tools (ADR-JEV-0002).
- A dry-run entry is its report of one request a live run would send.
- A composed request is the full JSON body judge-jev would send to Jev.
- The record's Raptor source is the Raptor index the record was read from.
- A location (resolved: its path, section or symbol) is the text judged against a record: a whole file (`path`), a Markdown section (`path#Heading`) or a code symbol (`path::Symbol`) (REQ-JEV-0207).
- A quality decision tree is the data file of questions that judges whether a record is well written: waves of questions, with rules that turn Jev's answers into the next wave or a verdict (REQ-JEV-0101).
- A typed error is a JSON error object with a stable `code` (such as `INPUT.MALFORMED`), a `message` and a `suggested_action`.

## Definitions added or reworded (greedy -> final)

- Raptor is the requirements tool that imports Markdown records (ADR-JEV-0002).
- A quality decision tree is the data file of questions that judges whether a record is well written: waves of questions (REQ-JEV-0101).

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -4,10 +4,24 @@
 
 ### Requirement Statement
 
+Definitions: Jev is TypeSafe's hosted judge model: it answers each
+multiple-choice question about a text with one choice and a confidence from
+0 to 1. Raptor is the requirements tool that imports Markdown records
+(ADR-JEV-0002). A dry run is a run with `--dry-run`: it composes every
+request and sends none. The digest of a text is its SHA-256. A mode (target
+mode) names what a location holds: `prompt` (prompt text), `skill` (a skill
+file), `task` (a task template) or `code` (source code). A question set is
+the data file of questions sent to Jev; its shipped id is the `id` of a set
+shipped with the tool, its override path the file given with `--questions`.
+A vars file holds the values of a task template's variables. The request
+limit is 24000 bytes by default. A quality decision tree is the data file of
+questions that judges whether a record is well written: waves of questions
+(REQ-JEV-0101). The wave-1 request is the request for its first wave.
+
 **MUST statements:**
 - `judge-jev quality` MUST accept `--dry-run`.
 - `judge-jev check` MUST accept `--dry-run`.
-- A dry run MUST compose every request without calling Jev.
+- A dry run MUST compose every request with no Jev call.
 - Each dry-run entry MUST report the record id.
 - Each dry-run entry MUST report the record's Raptor source.
 - Each dry-run entry MUST report the resolved location as its path, section

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -6,32 +6,22 @@
 
 Definitions: Jev is TypeSafe's hosted judge model: it answers each
 multiple-choice question about a text with one choice and a confidence from
-0 to 1. A Jev request is one call to it. Raptor is the requirements tool
-that imports Markdown records into its record store and serves them to other
-tools (ADR-JEV-0002). A dry run is a run with `--dry-run`: it composes every
-request and sends none. A dry-run entry is its report of one request a live
-run would send. A composed request is the full JSON body judge-jev would
-send to Jev. The record's Raptor source is the Raptor index the record was
-read from. A location (resolved: its path, section or symbol) is the text
-judged against a record: a whole file (`path`), a Markdown section
-(`path#Heading`) or a code symbol (`path::Symbol`) (REQ-JEV-0207). The
-digest of a text is its SHA-256. A mode (target mode) names what a location
-holds: `prompt` (prompt text), `skill` (a skill file), `task` (a task
-template) or `code` (source code). A question set is the data file of
-questions sent to Jev; its shipped id is the `id` of a set shipped with the
-tool, its override path the file given with `--questions`. A vars file holds
-the values of a task template's variables. The request limit is 24000 bytes
-by default. A quality decision tree is the data file of questions that
-judges whether a record is well written: waves of questions, with rules that
-turn Jev's answers into the next wave or a verdict (REQ-JEV-0101). The
-wave-1 request is the request for its first wave. A typed error is a JSON
-error object with a stable `code` (such as `INPUT.MALFORMED`), a `message`
-and a `suggested_action`.
+0 to 1. Raptor is the requirements tool that imports Markdown records
+(ADR-JEV-0002). A dry run is a run with `--dry-run`: it composes every
+request and sends none. The digest of a text is its SHA-256. A mode (target
+mode) names what a location holds: `prompt` (prompt text), `skill` (a skill
+file), `task` (a task template) or `code` (source code). A question set is
+the data file of questions sent to Jev; its shipped id is the `id` of a set
+shipped with the tool, its override path the file given with `--questions`.
+A vars file holds the values of a task template's variables. The request
+limit is 24000 bytes by default. A quality decision tree is the data file of
+questions that judges whether a record is well written: waves of questions
+(REQ-JEV-0101). The wave-1 request is the request for its first wave.
 
 **MUST statements:**
 - `judge-jev quality` MUST accept `--dry-run`.
 - `judge-jev check` MUST accept `--dry-run`.
-- A dry run MUST compose every request without calling Jev.
+- A dry run MUST compose every request with no Jev call.
 - Each dry-run entry MUST report the record id.
 - Each dry-run entry MUST report the record's Raptor source.
 - Each dry-run entry MUST report the resolved location as its path, section

```

## Original text

````markdown
## REQ-JEV-0208: Dry run audits the composed request

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev quality` MUST accept `--dry-run`.
- `judge-jev check` MUST accept `--dry-run`.
- A dry run MUST compose every request without calling Jev.
- Each dry-run entry MUST report the record id.
- Each dry-run entry MUST report the record's Raptor source.
- Each dry-run entry MUST report the resolved location as its path, section
  or symbol.
- Each dry-run entry MUST report the digest of the location's selected
  text.
- Each dry-run entry MUST report the mode.
- Each dry-run entry MUST report the question set as its shipped id or its
  override path.
- In `task` mode, each dry-run entry MUST report the vars file.
- In `task` mode, each dry-run entry MUST report the rendered text.
- Each dry-run entry MUST report the full composed request.
- Each dry-run entry MUST report the composed request's size against the
  request limit.
- For `quality`, the dry run MUST report the decision tree.
- For `quality`, the dry run MUST report the composed wave-1 request.
- A dry run MUST fail with a typed error on anything that would make the
  live request wrong: an unresolved record or location, a render failure,
  or an oversize request.

### Rationale

The caller must know the prompt will be built correctly before any text
leaves the machine. A `quality` dry run stops at wave 1 because later
waves depend on live answers.

### Success Criteria

**Acceptance Criteria:**
- [ ] A dry run makes no network call and reports one entry per request a
  live run would send.
- [ ] A dry run over a task location with a missing variable fails naming
  the variable.

---
````

## Final text

````markdown
## REQ-JEV-0208: Dry run audits the composed request

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. Raptor is the requirements tool that imports Markdown records
(ADR-JEV-0002). A dry run is a run with `--dry-run`: it composes every
request and sends none. The digest of a text is its SHA-256. A mode (target
mode) names what a location holds: `prompt` (prompt text), `skill` (a skill
file), `task` (a task template) or `code` (source code). A question set is
the data file of questions sent to Jev; its shipped id is the `id` of a set
shipped with the tool, its override path the file given with `--questions`.
A vars file holds the values of a task template's variables. The request
limit is 24000 bytes by default. A quality decision tree is the data file of
questions that judges whether a record is well written: waves of questions
(REQ-JEV-0101). The wave-1 request is the request for its first wave.

**MUST statements:**
- `judge-jev quality` MUST accept `--dry-run`.
- `judge-jev check` MUST accept `--dry-run`.
- A dry run MUST compose every request with no Jev call.
- Each dry-run entry MUST report the record id.
- Each dry-run entry MUST report the record's Raptor source.
- Each dry-run entry MUST report the resolved location as its path, section
  or symbol.
- Each dry-run entry MUST report the digest of the location's selected
  text.
- Each dry-run entry MUST report the mode.
- Each dry-run entry MUST report the question set as its shipped id or its
  override path.
- In `task` mode, each dry-run entry MUST report the vars file.
- In `task` mode, each dry-run entry MUST report the rendered text.
- Each dry-run entry MUST report the full composed request.
- Each dry-run entry MUST report the composed request's size against the
  request limit.
- For `quality`, the dry run MUST report the decision tree.
- For `quality`, the dry run MUST report the composed wave-1 request.
- A dry run MUST fail with a typed error on anything that would make the
  live request wrong: an unresolved record or location, a render failure,
  or an oversize request.

### Rationale

The caller must know the prompt will be built correctly before any text
leaves the machine. A `quality` dry run stops at wave 1 because later
waves depend on live answers.

### Success Criteria

**Acceptance Criteria:**
- [ ] A dry run makes no network call and reports one entry per request a
  live run would send.
- [ ] A dry run over a task location with a missing variable fails naming
  the variable.

---
````
