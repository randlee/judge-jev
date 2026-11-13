# REQ-JEV-0213

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [4, 4, 4, 4, 5, 4] | 6/6 | 0.589 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.719 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.713 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.716; final fails [0, 0, 0] margin 0.721.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.7174; pruned 0 failing runs, margin 0.6421).

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
@@ -3,6 +3,13 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: A definition is a term with its meaning, attached to a record
+(ADR-JEV-0008); a candidate definition is one being tested. The comparison
+is `judge-jev compare-definition`. The requests a candidate would reach are
+the requests about the records it is attached to. An answer is Jev's choice
+for one question, with its confidence from 0 to 1. The decision threshold is
+0.6 unless `--threshold` sets it; a confidence at or above it decides.
 
 **MUST statements:**
 - `judge-jev` MUST provide a comparison of one or more candidate

```

## Diff: greedy (previous commit) -> final

```diff
(no change)
```

## Original text

````markdown
## REQ-JEV-0213: A definition is kept only when it changes an answer

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev` MUST provide a comparison of one or more candidate
  definitions.
- The comparison MUST run the requests the candidate definitions would
  reach with the candidates.
- The comparison MUST run the same requests without the candidates.
- The comparison MUST report each answer's choice with and without the
  candidates.
- The comparison MUST report each answer's confidence with and without the
  candidates.
- The comparison MUST report the candidates as material when an answer's
  choice flips or its confidence crosses the decision threshold, and as not
  material when every change stays on the same side of the threshold.
- The comparison MUST record the threshold it applied.

### Rationale

Rand Lee, 2026-11-08: "if adding the definition does not impact the scores
used in the rubric, they aren't necessary to add"; "Moving from 90->95
confidence doesn't matter. A change from 20%->50% would be material if
other changes get it over the threshold."

### Success Criteria

**Acceptance Criteria:**
- [ ] With fixture answers where the definition flips one answer, the
  comparison reports it as material.
- [ ] With fixture answers that are the same with and without the
  definition, the comparison reports it as not material.
- [ ] A confidence move from 0.90 to 0.95 on the same side of the threshold
  is not material. Two candidates that each move an answer part of the way,
  and together across the threshold, are material when compared together.

---
````

## Final text

````markdown
## REQ-JEV-0213: A definition is kept only when it changes an answer

**Status:** Draft  

### Requirement Statement

Definitions: A definition is a term with its meaning, attached to a record
(ADR-JEV-0008); a candidate definition is one being tested. The comparison
is `judge-jev compare-definition`. The requests a candidate would reach are
the requests about the records it is attached to. An answer is Jev's choice
for one question, with its confidence from 0 to 1. The decision threshold is
0.6 unless `--threshold` sets it; a confidence at or above it decides.

**MUST statements:**
- `judge-jev` MUST provide a comparison of one or more candidate
  definitions.
- The comparison MUST run the requests the candidate definitions would
  reach with the candidates.
- The comparison MUST run the same requests without the candidates.
- The comparison MUST report each answer's choice with and without the
  candidates.
- The comparison MUST report each answer's confidence with and without the
  candidates.
- The comparison MUST report the candidates as material when an answer's
  choice flips or its confidence crosses the decision threshold, and as not
  material when every change stays on the same side of the threshold.
- The comparison MUST record the threshold it applied.

### Rationale

Rand Lee, 2026-11-08: "if adding the definition does not impact the scores
used in the rubric, they aren't necessary to add"; "Moving from 90->95
confidence doesn't matter. A change from 20%->50% would be material if
other changes get it over the threshold."

### Success Criteria

**Acceptance Criteria:**
- [ ] With fixture answers where the definition flips one answer, the
  comparison reports it as material.
- [ ] With fixture answers that are the same with and without the
  definition, the comparison reports it as not material.
- [ ] A confidence move from 0.90 to 0.95 on the same side of the threshold
  is not material. Two candidates that each move an answer part of the way,
  and together across the threshold, are material when compared together.

---
````
