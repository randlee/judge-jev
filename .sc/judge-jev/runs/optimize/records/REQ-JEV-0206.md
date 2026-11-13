# REQ-JEV-0206

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [2, 1, 1, 2, 2, 1] | 6/6 | 0.768 |
| greedy | [2, 2, 1, 2, 1, 1] | 6/6 | 0.769 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.788 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [1, 2, 1] margin 0.759; final fails [0, 0, 0] margin 0.784.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.7627; pruned 0 failing runs, margin 0.7811).

## Kept tweaks (text present in the final record) and measured effect

- remove s1 (proposed by i1:opus-B)
  - old: `(prompt, skill, agent, template or code)`
  - new: `(removed)`
  - i1 opus-B: m1: fails 1, margin 0.765; m2: fails 1, margin 0.781 (reference margin 0.776, reference fails mean 1.67)
- remove defs (proposed by i2:mechanical)
  - old: `A record is one requirement, non-functional requirement or architecture decision record as Raptor imports it.`
  - new: `(removed)`
  - i2 mechanical: m1: fails 0, margin 0.777; m2: fails 0, margin 0.777 (reference margin 0.753, reference fails mean 0.00)
  - i2 mechanical: m1: fails 0, margin 0.777; m2: fails 0, margin 0.777 (reference margin 0.753, reference fails mean 0.00)
- remove defs (proposed by i2:mechanical)
  - old: `A pair is one (record, location) pair.`
  - new: `(removed)`
  - i2 mechanical: m1: fails 0, margin 0.723; m2: fails 0, margin 0.748 (reference margin 0.753, reference fails mean 0.00)
  - i2 mechanical: m1: fails 0, margin 0.723; m2: fails 0, margin 0.748 (reference margin 0.753, reference fails mean 0.00)
- remove defs (proposed by i2:opus-B)
  - old: `: a whole file (`path`), a Markdown section (`path#Heading`) or a code symbol (`path::Symbol`)`
  - new: `(removed)`
  - i2 opus-B: m1: fails 0, margin 0.787; m2: fails 0, margin 0.787 (reference margin 0.753, reference fails mean 0.00)
  - i2 opus-B: m1: fails 0, margin 0.787; m2: fails 0, margin 0.787 (reference margin 0.753, reference fails mean 0.00)
- remove defs (proposed by i2:sonnet-B)
  - old: `A location is defined in REQ-JEV-0207;`
  - new: `(removed)`
  - i2 sonnet-B: m1: fails 0, margin 0.757; m2: fails 0, margin 0.767 (reference margin 0.753, reference fails mean 0.00)
  - i2 sonnet-B: m1: fails 0, margin 0.757; m2: fails 0, margin 0.767 (reference margin 0.753, reference fails mean 0.00)
- remove defs (proposed by i2:sonnet-B)
  - old: `; a result is the reported judgment`
  - new: `(removed)`
  - i2 sonnet-B: m1: fails 0, margin 0.733; m2: fails 0, margin 0.737 (reference margin 0.753, reference fails mean 0.00)
  - i2 sonnet-B: m1: fails 0, margin 0.733; m2: fails 0, margin 0.737 (reference margin 0.753, reference fails mean 0.00)
- remove defs (proposed by i3:mechanical)
  - old: `a pair is one (record, location) pair.`
  - new: `(removed)`
  - i3 mechanical: m1: fails 0, margin 0.790; m2: fails 0, margin 0.805 (reference margin 0.802, reference fails mean 0.00)
- remove defs (proposed by i3:mechanical)
  - old: `A location is the text judged against a record (REQ-JEV-0207).`
  - new: `(removed)`
  - i3 mechanical: m1: fails 0, margin 0.797; m2: fails 0, margin 0.782 (reference margin 0.802, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

None.

## Definitions added or reworded (greedy -> final)

- A judgment is one Jev verdict on one record at one location.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -4,10 +4,11 @@
 
 ### Requirement Statement
 
+Definitions: A judgment is one Jev verdict on one record at one location.
+
 **MUST statements:**
-- When a record is satisfied in more than one location (prompt, skill,
-  agent, template or code), judge-jev MUST judge the record separately at
-  each location.
+- When a record is satisfied in more than one location, judge-jev MUST
+  judge the record separately at each location.
 - judge-jev MUST report one result per (record, location) pair.
 
 **MUST NOT statements:**

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,10 +4,11 @@
 
 ### Requirement Statement
 
+Definitions: A judgment is one Jev verdict on one record at one location.
+
 **MUST statements:**
-- When a record is satisfied in more than one location (prompt, skill,
-  agent, template or code), judge-jev MUST judge the record separately at
-  each location.
+- When a record is satisfied in more than one location, judge-jev MUST
+  judge the record separately at each location.
 - judge-jev MUST report one result per (record, location) pair.
 
 **MUST NOT statements:**

```

## Original text

````markdown
## REQ-JEV-0206: One judgment per record and location

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- When a record is satisfied in more than one location (prompt, skill,
  agent, template or code), judge-jev MUST judge the record separately at
  each location.
- judge-jev MUST report one result per (record, location) pair.

**MUST NOT statements:**
- judge-jev MUST NOT combine a record's locations into one judgment.

### Rationale

Rand (2026-11-07): "from raptor config standpoint for judge-jev, we must
have single requirements mapped to multiple places in
prompts/skills/agents/code I would expect a separate jev query for each
location it is satisfied. We may be able to fan out a single jev call w/
<location> - <question-1-req-1> | <question-2-req-1> | <question-3-req-2>
| <question-4-req-2> | ... depending on how we can fit items in context"
Rand (2026-11-08): "batching is simply streaming of single requests."

### Success Criteria

**Acceptance Criteria:**
- [ ] A record mapped to three locations produces three results, one per
  location.
- [ ] A failure at one location is reported against that location only.

---
````

## Final text

````markdown
## REQ-JEV-0206: One judgment per record and location

**Status:** Draft  

### Requirement Statement

Definitions: A judgment is one Jev verdict on one record at one location.

**MUST statements:**
- When a record is satisfied in more than one location, judge-jev MUST
  judge the record separately at each location.
- judge-jev MUST report one result per (record, location) pair.

**MUST NOT statements:**
- judge-jev MUST NOT combine a record's locations into one judgment.

### Rationale

Rand (2026-11-07): "from raptor config standpoint for judge-jev, we must
have single requirements mapped to multiple places in
prompts/skills/agents/code I would expect a separate jev query for each
location it is satisfied. We may be able to fan out a single jev call w/
<location> - <question-1-req-1> | <question-2-req-1> | <question-3-req-2>
| <question-4-req-2> | ... depending on how we can fit items in context"
Rand (2026-11-08): "batching is simply streaming of single requests."

### Success Criteria

**Acceptance Criteria:**
- [ ] A record mapped to three locations produces three results, one per
  location.
- [ ] A failure at one location is reported against that location only.

---
````
