# REQ-JEV-0205

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [5, 6, 4, 6, 5, 6] | 6/6 | 0.741 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.795 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.811 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 1] margin 0.796; final fails [0, 0, 0] margin 0.814.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.8255; pruned 0 failing runs, margin 0.8161).

## Kept tweaks (text present in the final record) and measured effect

- remove s1 (proposed by i1:haiku-B)
  - old: `(agent text or code)`
  - new: `(removed)`
  - i1 haiku-B: m1: fails 0, margin 0.798; m2: fails 0, margin 0.805 (reference margin 0.798, reference fails mean 0.33)
- remove defs (proposed by i1:haiku-B)
  - old: `through the sc-observability logger`
  - new: `(removed)`
  - i1 haiku-B: m1: fails 0, margin 0.802; m2: fails 0, margin 0.793 (reference margin 0.798, reference fails mean 0.33)
- reword s6 (proposed by i1:opus-B)
  - old: `The released tool MUST accept an override file for any question set.`
  - new: `The released tool MUST accept, with `--questions <file>`, an override file for any question set.`
  - i1 opus-B: m1: fails 0, margin 0.809; m2: fails 0, margin 0.805; m3: fails 0, margin 0.812; m4: fails 0, margin 0.800; m5: fails 0, margin 0.814; m6: fails 0, margin 0.806 (reference margin 0.798, reference fails mean 0.33)
- remove defs (proposed by i1:opus-B)
  - old: `as Raptor imports it`
  - new: `(removed)`
  - i1 opus-B: m1: fails 0, margin 0.792; m2: fails 0, margin 0.785 (reference margin 0.798, reference fails mean 0.33)
- remove defs (proposed by i2:mechanical)
  - old: `A record is one requirement (REQ), non-functional requirement (NFR) or architecture decision record (ADR); REQ, NFR and ADR are its record kinds.`
  - new: `(removed)`
  - i2 mechanical: m1: fails 0, margin 0.819; m2: fails 0, margin 0.826 (reference margin 0.815, reference fails mean 0.00)
- remove defs (proposed by i2:mechanical)
  - old: `A target class is agent text (modes `prompt`, `skill` and `task`) or code (mode `code`).`
  - new: `(removed)`
  - i2 mechanical: m1: fails 0, margin 0.821; m2: fails 0, margin 0.813 (reference margin 0.815, reference fails mean 0.00)
- remove defs (proposed by i2:mechanical)
  - old: `A question-set id is the `id` field of a question set or tree file.`
  - new: `(removed)`
  - i2 mechanical: m1: fails 0, margin 0.811; m2: fails 0, margin 0.805 (reference margin 0.815, reference fails mean 0.00)
- remove defs (proposed by i2:mechanical)
  - old: `The released tool is the installed judge-jev release.`
  - new: `(removed)`
  - i2 mechanical: m1: fails 0, margin 0.817; m2: fails 0, margin 0.811 (reference margin 0.815, reference fails mean 0.00)
- remove defs (proposed by i2:haiku-B)
  - old: `; see REQ-JEV-0101`
  - new: `(removed)`
  - i2 haiku-B: m1: fails 0, margin 0.820; m2: fails 0, margin 0.827 (reference margin 0.815, reference fails mean 0.00)
- reword defs (proposed by i2:haiku-B)
  - old: `writes (REQ-JEV-0008).`
  - new: `writes.`
  - i2 haiku-B: m1: fails 0, margin 0.822; m2: fails 0, margin 0.822 (reference margin 0.815, reference fails mean 0.00)
- reword defs (proposed by i2:haiku-B)
  - old: `sends to Jev about a location for one record kind`
  - new: `sends to Jev for one record kind`
  - i2 haiku-B: m1: fails 0, margin 0.819; m2: fails 0, margin 0.812 (reference margin 0.815, reference fails mean 0.00)
- remove defs (proposed by i2:opus-B)
  - old: `given with `--questions``
  - new: `(removed)`
  - i2 opus-B: m1: fails 0, margin 0.818; m2: fails 0, margin 0.819 (reference margin 0.815, reference fails mean 0.00)
- remove defs (proposed by i2:opus-B)
  - old: `for that run`
  - new: `(removed)`
  - i2 opus-B: m1: fails 0, margin 0.808; m2: fails 0, margin 0.815 (reference margin 0.815, reference fails mean 0.00)
- reword defs (proposed by i2:sonnet-B)
  - old: `is the SHA-256 of its bytes`
  - new: `is its SHA-256`
  - i2 sonnet-B: m1: fails 0, margin 0.813; m2: fails 0, margin 0.817 (reference margin 0.815, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- A record is one requirement (REQ), non-functional requirement (NFR) or architecture decision record (ADR) as Raptor imports it; REQ, NFR and ADR are its record kinds.
- A question set is the data file of questions judge-jev sends to Jev about a location for one record kind and target class.
- A target class is agent text (modes `prompt`, `skill` and `task`) or code (mode `code`).
- A quality decision tree is the data file of questions that judges whether a record is well written: waves of questions, with rules that turn Jev's answers into the next wave or a verdict (REQ-JEV-0101).
- A question-set id is the `id` field of a question set or tree file.
- The content digest of a file is the SHA-256 of its bytes.
- A log entry is one event a run writes through the sc-observability logger (REQ-JEV-0008).

## Definitions added or reworded (greedy -> final)

- A question set is the data file of questions judge-jev sends to Jev for one record kind and target class.
- A quality decision tree is the data file of questions that judges whether a record is well written.
- The content digest of a file is its SHA-256.
- An override file is a file that replaces the shipped question set or quality decision tree.
- A log entry is one event a run writes.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -4,15 +4,23 @@
 
 ### Requirement Statement
 
+Definitions: A question set is the data file of questions judge-jev sends to
+Jev for one record kind and target class. A quality decision tree is the
+data file of questions that judges whether a record is well written. The
+content digest of a file is its SHA-256. An override file is a file that
+replaces the shipped question set or quality decision tree. A log entry is
+one event a run writes.
+
 **MUST statements:**
 - judge-jev MUST ship one question set per combination of record kind and
-  target class (agent text or code).
+  target class.
 - judge-jev MUST ship one quality decision tree per record kind.
 - Every shipped question and prompt text MUST be approved by Rand before
   it ships.
 - Question sets MUST be data files shipped with the tool.
 - Quality decision trees MUST be data files shipped with the tool.
-- The released tool MUST accept an override file for any question set.
+- The released tool MUST accept, with `--questions <file>`, an override file
+  for any question set.
 - The released tool MUST accept an override file for any quality decision
   tree.
 - Every result MUST carry the question-set id.

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,27 +4,23 @@
 
 ### Requirement Statement
 
-Definitions: A record is one requirement (REQ), non-functional requirement
-(NFR) or architecture decision record (ADR) as Raptor imports it; REQ, NFR
-and ADR are its record kinds. A question set is the data file of questions
-judge-jev sends to Jev about a location for one record kind and target
-class. A target class is agent text (modes `prompt`, `skill` and `task`) or
-code (mode `code`). A quality decision tree is the data file of questions
-that judges whether a record is well written: waves of questions, with rules
-that turn Jev's answers into the next wave or a verdict (REQ-JEV-0101). A
-question-set id is the `id` field of a question set or tree file. The
-content digest of a file is the SHA-256 of its bytes. A log entry is one
-event a run writes through the sc-observability logger (REQ-JEV-0008).
+Definitions: A question set is the data file of questions judge-jev sends to
+Jev for one record kind and target class. A quality decision tree is the
+data file of questions that judges whether a record is well written. The
+content digest of a file is its SHA-256. An override file is a file that
+replaces the shipped question set or quality decision tree. A log entry is
+one event a run writes.
 
 **MUST statements:**
 - judge-jev MUST ship one question set per combination of record kind and
-  target class (agent text or code).
+  target class.
 - judge-jev MUST ship one quality decision tree per record kind.
 - Every shipped question and prompt text MUST be approved by Rand before
   it ships.
 - Question sets MUST be data files shipped with the tool.
 - Quality decision trees MUST be data files shipped with the tool.
-- The released tool MUST accept an override file for any question set.
+- The released tool MUST accept, with `--questions <file>`, an override file
+  for any question set.
 - The released tool MUST accept an override file for any quality decision
   tree.
 - Every result MUST carry the question-set id.

```

## Original text

````markdown
## REQ-JEV-0205: Question sets ship with the tool

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- judge-jev MUST ship one question set per combination of record kind and
  target class (agent text or code).
- judge-jev MUST ship one quality decision tree per record kind.
- Every shipped question and prompt text MUST be approved by Rand before
  it ships.
- Question sets MUST be data files shipped with the tool.
- Quality decision trees MUST be data files shipped with the tool.
- The released tool MUST accept an override file for any question set.
- The released tool MUST accept an override file for any quality decision
  tree.
- Every result MUST carry the question-set id.
- Every result MUST carry the content digest of the file used.
- Every log entry MUST carry the question-set id.
- Every log entry MUST carry the content digest of the file used.

### Rationale

Rand: "I do not trust non-frontier agents to write prompts. I do not even
trust frontier agents to write them." The question sets are the tool's
system prompts. Getting them production-worthy means running thousands of
question variations against the released tool; a variation that needs a
code change cannot be run at that scale.

Because question sets and trees are data files, changing a question, a
tree branch or a wave needs no code change. An override file lets a
variation be tried by writing a file, never by changing or rebuilding code.
The question-set id and file digest on every result and log entry let
results from many variations of the same set be told apart and compared.

### Success Criteria

**Acceptance Criteria:**
- [ ] Each shipped question file names the approval that admitted its text.
- [ ] A result produced with an override names the override file and its
  digest.
- [ ] Two override files differing in one question produce results with
  different digests, run on the same released build.
- [ ] Adding a wave to a quality tree changes only the tree file.

---
````

## Final text

````markdown
## REQ-JEV-0205: Question sets ship with the tool

**Status:** Draft  

### Requirement Statement

Definitions: A question set is the data file of questions judge-jev sends to
Jev for one record kind and target class. A quality decision tree is the
data file of questions that judges whether a record is well written. The
content digest of a file is its SHA-256. An override file is a file that
replaces the shipped question set or quality decision tree. A log entry is
one event a run writes.

**MUST statements:**
- judge-jev MUST ship one question set per combination of record kind and
  target class.
- judge-jev MUST ship one quality decision tree per record kind.
- Every shipped question and prompt text MUST be approved by Rand before
  it ships.
- Question sets MUST be data files shipped with the tool.
- Quality decision trees MUST be data files shipped with the tool.
- The released tool MUST accept, with `--questions <file>`, an override file
  for any question set.
- The released tool MUST accept an override file for any quality decision
  tree.
- Every result MUST carry the question-set id.
- Every result MUST carry the content digest of the file used.
- Every log entry MUST carry the question-set id.
- Every log entry MUST carry the content digest of the file used.

### Rationale

Rand: "I do not trust non-frontier agents to write prompts. I do not even
trust frontier agents to write them." The question sets are the tool's
system prompts. Getting them production-worthy means running thousands of
question variations against the released tool; a variation that needs a
code change cannot be run at that scale.

Because question sets and trees are data files, changing a question, a
tree branch or a wave needs no code change. An override file lets a
variation be tried by writing a file, never by changing or rebuilding code.
The question-set id and file digest on every result and log entry let
results from many variations of the same set be told apart and compared.

### Success Criteria

**Acceptance Criteria:**
- [ ] Each shipped question file names the approval that admitted its text.
- [ ] A result produced with an override names the override file and its
  digest.
- [ ] Two override files differing in one question produce results with
  different digests, run on the same released build.
- [ ] Adding a wave to a quality tree changes only the tree file.

---
````
