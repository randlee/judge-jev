# REQ-JEV-0001

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [0, 1, 1, 1, 0, 1] | 4/6 | 0.850 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.868 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.887 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.866; final fails [0, 0, 0] margin 0.891.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.869; pruned 0 failing runs, margin 0.8917).

## Kept tweaks (text present in the final record) and measured effect

- remove defs (proposed by i1:mechanical)
  - old: `Its query interface is the way Raptor hands records to another tool.`
  - new: `(removed)`
  - i1 mechanical: m1: fails 0, margin 0.865; m2: fails 0, margin 0.878 (reference margin 0.869, reference fails mean 0.00)
- remove defs (proposed by i1:sonnet-A)
  - old: `and serves them to other tools (ADR-JEV-0002)`
  - new: `(removed)`
  - i1 sonnet-A: m1: fails 0, margin 0.883; m2: fails 0, margin 0.887 (reference margin 0.869, reference fails mean 0.00)
- reword defs (proposed by i2:haiku-A)
  - old: `requirements tool`
  - new: `tool`
  - i2 haiku-A: m1: fails 0, margin 0.877; m2: fails 0, margin 0.888 (reference margin 0.884, reference fails mean 0.00)
- remove defs (proposed by i2:sonnet-A)
  - old: `into its record store`
  - new: `(removed)`
  - i2 sonnet-A: m1: fails 0, margin 0.885; m2: fails 0, margin 0.883 (reference margin 0.884, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- Raptor is the requirements tool that imports Markdown records into its record store and serves them to other tools (ADR-JEV-0002).
- Its query interface is the way Raptor hands records to another tool.

## Definitions added or reworded (greedy -> final)

- Raptor is the tool that imports records.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -3,6 +3,8 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: Raptor is the tool that imports records.
 
 **MUST statements:**
 

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,9 +4,7 @@
 
 ### Requirement Statement
 
-Definitions: Raptor is the requirements tool that imports Markdown records
-into its record store and serves them to other tools (ADR-JEV-0002). Its
-query interface is the way Raptor hands records to another tool.
+Definitions: Raptor is the tool that imports records.
 
 **MUST statements:**
 

```

## Original text

````markdown
## REQ-JEV-0001: Records come from Raptor

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST obtain records through Raptor's query interface.

**MUST NOT statements:**

- judge-jev MUST NOT parse record Markdown itself.
- judge-jev MUST NOT run SQL (Structured Query Language) against the record
  store itself.

### Rationale

Raptor owns the schema and every conversion; the Raptor team can change
them and notify judge-jev without breaking it.

### Success Criteria

**Acceptance Criteria:**

- [ ] judge-jev contains no Markdown record parser and no SQL statement.
````

## Final text

````markdown
## REQ-JEV-0001: Records come from Raptor

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the tool that imports records.

**MUST statements:**

- judge-jev MUST obtain records through Raptor's query interface.

**MUST NOT statements:**

- judge-jev MUST NOT parse record Markdown itself.
- judge-jev MUST NOT run SQL (Structured Query Language) against the record
  store itself.

### Rationale

Raptor owns the schema and every conversion; the Raptor team can change
them and notify judge-jev without breaking it.

### Success Criteria

**Acceptance Criteria:**

- [ ] judge-jev contains no Markdown record parser and no SQL statement.
````
