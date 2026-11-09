# REQ-JEV-0008

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [1, 1, 1, 1, 1, 1] | 6/6 | 0.710 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.730 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.730 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.731; final fails [0, 0, 0] margin 0.740.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.7336; pruned 0 failing runs, margin 0.6948).

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
+Definitions: The sc-observability logger is the JSON-lines logger of the
+sc-observability package (version 1.5.0), which writes
+`.sc/judge-jev/logs/judge-jev.log.jsonl`. sc-agent is the agent tool whose
+Rust Jev tool will replace judge-jev's Python Jev core (ADR-JEV-0007). A
+quality-tree branch is the next wave a quality decision tree's rules select
+from Jev's answers.
 
 **MUST statements:**
 

```

## Diff: greedy (previous commit) -> final

```diff
(no change)
```

## Original text

````markdown
## REQ-JEV-0008: Logging through the sc-observability logger

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST write its run logs (requests, answers, quality-tree
  branches, verdicts) through the sc-observability logger, the logger
  sc-agent uses.

**MUST NOT statements:**

- judge-jev MUST NOT keep its own log format alongside it.

### Rationale

Rand (2026-11-08): "we will need to use sc-observability logger for both
(this is what sc-agent uses). we should implement in judge-jev first then
we can upgrade plan-anchor which is currently working solidly."

### Success Criteria

**Acceptance Criteria:**

- [ ] A live `check` run's requests, answers and verdicts appear in the
  sc-observability log.
- [ ] No judge-jev command writes `anchor-runs/tournament-*.jsonl`.

### Implementation Notes

Today the copied core writes its own `anchor-runs/tournament-<run>.jsonl`
(`jev_judge.py` `pump_batch`). plan-anchor moves to the same logger after
judge-jev.
````

## Final text

````markdown
## REQ-JEV-0008: Logging through the sc-observability logger

**Status:** Draft  

### Requirement Statement

Definitions: The sc-observability logger is the JSON-lines logger of the
sc-observability package (version 1.5.0), which writes
`.sc/judge-jev/logs/judge-jev.log.jsonl`. sc-agent is the agent tool whose
Rust Jev tool will replace judge-jev's Python Jev core (ADR-JEV-0007). A
quality-tree branch is the next wave a quality decision tree's rules select
from Jev's answers.

**MUST statements:**

- judge-jev MUST write its run logs (requests, answers, quality-tree
  branches, verdicts) through the sc-observability logger, the logger
  sc-agent uses.

**MUST NOT statements:**

- judge-jev MUST NOT keep its own log format alongside it.

### Rationale

Rand (2026-11-08): "we will need to use sc-observability logger for both
(this is what sc-agent uses). we should implement in judge-jev first then
we can upgrade plan-anchor which is currently working solidly."

### Success Criteria

**Acceptance Criteria:**

- [ ] A live `check` run's requests, answers and verdicts appear in the
  sc-observability log.
- [ ] No judge-jev command writes `anchor-runs/tournament-*.jsonl`.

### Implementation Notes

Today the copied core writes its own `anchor-runs/tournament-<run>.jsonl`
(`jev_judge.py` `pump_batch`). plan-anchor moves to the same logger after
judge-jev.
````
