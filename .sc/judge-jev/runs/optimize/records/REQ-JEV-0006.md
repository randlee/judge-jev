# REQ-JEV-0006

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [2, 2, 2, 2, 2, 2] | 6/6 | 0.642 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.692 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.680 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.674; final fails [0, 0, 0] margin 0.683.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.6827; pruned 0 failing runs, margin 0.6366).

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
@@ -3,6 +3,14 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: Raptor is the requirements tool that imports Markdown records
+into its record store and serves them to other tools (ADR-JEV-0002).
+Raptor-parseable Markdown is Markdown in the record format Raptor's import
+reads. SQLite is a single-file SQL (Structured Query Language) database.
+Dolt is a SQL database with Git-style branches; a SQLite snapshot of a Dolt
+branch is a SQLite copy of that branch's records. The Raptor interface is
+the way Raptor hands records to another tool.
 
 **MUST statements:**
 

```

## Diff: greedy (previous commit) -> final

```diff
(no change)
```

## Original text

````markdown
## REQ-JEV-0006: Local record database built through Raptor

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST obtain its record database by asking Raptor to build a
  local SQLite database from the repository's Raptor-parseable Markdown on
  each run.
- When Raptor supplies a SQLite snapshot of a Dolt branch, judge-jev MUST
  query it through the same Raptor interface.

### Rationale

Querying SQLite is the same work whether it was built from Markdown or
pulled from Dolt, so the source can change without changing judge-jev.

### Success Criteria

**Acceptance Criteria:**

- [ ] A run in a repository with a `.raptor/` configuration judges records
  from a database built in that run.
````

## Final text

````markdown
## REQ-JEV-0006: Local record database built through Raptor

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool that imports Markdown records
into its record store and serves them to other tools (ADR-JEV-0002).
Raptor-parseable Markdown is Markdown in the record format Raptor's import
reads. SQLite is a single-file SQL (Structured Query Language) database.
Dolt is a SQL database with Git-style branches; a SQLite snapshot of a Dolt
branch is a SQLite copy of that branch's records. The Raptor interface is
the way Raptor hands records to another tool.

**MUST statements:**

- judge-jev MUST obtain its record database by asking Raptor to build a
  local SQLite database from the repository's Raptor-parseable Markdown on
  each run.
- When Raptor supplies a SQLite snapshot of a Dolt branch, judge-jev MUST
  query it through the same Raptor interface.

### Rationale

Querying SQLite is the same work whether it was built from Markdown or
pulled from Dolt, so the source can change without changing judge-jev.

### Success Criteria

**Acceptance Criteria:**

- [ ] A run in a repository with a `.raptor/` configuration judges records
  from a database built in that run.
````
