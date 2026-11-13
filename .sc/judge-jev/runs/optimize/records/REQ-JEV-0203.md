# REQ-JEV-0203

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [3, 2, 3, 3, 3, 3] | 6/6 | 0.702 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.799 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.799 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.797; final fails [0, 0, 0] margin 0.796.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.7982; pruned 0 failing runs, margin 0.7702).

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
@@ -3,6 +3,17 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: A mode (target mode) names what a location holds: `prompt`
+(prompt text), `skill` (a skill file), `task` (a task template) or `code`
+(source code). A location is the text judged against a record: a whole file
+(`path`), a Markdown section (`path#Heading`) or a code symbol
+(`path::Symbol`) (REQ-JEV-0207). sc-compose is the template renderer; in
+strict mode it fails on any template variable the vars file does not set. A
+vars file holds the values of a template's variables. An assignment is the
+text a task template renders to. sc-agent is the agent tool whose Rust Jev
+tool will replace judge-jev's Python Jev core (ADR-JEV-0007). Tree-sitter
+grammars are the parsers that find a named symbol in source code.
 
 **MUST statements:**
 - judge-jev MUST support the target mode `prompt`.

```

## Diff: greedy (previous commit) -> final

```diff
(no change)
```

## Original text

````markdown
## REQ-JEV-0203: Target modes

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- judge-jev MUST support the target mode `prompt`.
- judge-jev MUST support the target mode `skill`.
- judge-jev MUST support the target mode `task`.
- judge-jev MUST support the target mode `code`.
- In `task` mode judge-jev MUST judge the raw template.
- In `task` mode judge-jev MUST judge an assignment rendered by sc-compose
  in strict mode from the vars file that `--vars` names, or, in a profile
  run, that the profile names.
- In `code` mode judge-jev MUST resolve the location with the tree-sitter
  grammars sc-agent defines.

**MUST NOT statements:**
- judge-jev MUST NOT define its own tree-sitter grammars.

### Rationale

The raw template shows which variables are substituted; a rendered
assignment shows what an agent actually receives. Strict rendering fails on
a missing variable instead of judging a half-rendered assignment. sc-agent
owns the grammars so every consumer selects code the same way.

### Success Criteria

**Acceptance Criteria:**
- [ ] A task template checked in `task` mode produces one result for the
  raw template and one for its rendered assignment.
- [ ] A vars file missing a template variable fails the render with the
  variable named.
- [ ] The repository contains no tree-sitter grammar definitions.

### Implementation Notes

`code` mode waits for sc-agent's tree-sitter grammars (ADR-JEV-0004).

---
````

## Final text

````markdown
## REQ-JEV-0203: Target modes

**Status:** Draft  

### Requirement Statement

Definitions: A mode (target mode) names what a location holds: `prompt`
(prompt text), `skill` (a skill file), `task` (a task template) or `code`
(source code). A location is the text judged against a record: a whole file
(`path`), a Markdown section (`path#Heading`) or a code symbol
(`path::Symbol`) (REQ-JEV-0207). sc-compose is the template renderer; in
strict mode it fails on any template variable the vars file does not set. A
vars file holds the values of a template's variables. An assignment is the
text a task template renders to. sc-agent is the agent tool whose Rust Jev
tool will replace judge-jev's Python Jev core (ADR-JEV-0007). Tree-sitter
grammars are the parsers that find a named symbol in source code.

**MUST statements:**
- judge-jev MUST support the target mode `prompt`.
- judge-jev MUST support the target mode `skill`.
- judge-jev MUST support the target mode `task`.
- judge-jev MUST support the target mode `code`.
- In `task` mode judge-jev MUST judge the raw template.
- In `task` mode judge-jev MUST judge an assignment rendered by sc-compose
  in strict mode from the vars file that `--vars` names, or, in a profile
  run, that the profile names.
- In `code` mode judge-jev MUST resolve the location with the tree-sitter
  grammars sc-agent defines.

**MUST NOT statements:**
- judge-jev MUST NOT define its own tree-sitter grammars.

### Rationale

The raw template shows which variables are substituted; a rendered
assignment shows what an agent actually receives. Strict rendering fails on
a missing variable instead of judging a half-rendered assignment. sc-agent
owns the grammars so every consumer selects code the same way.

### Success Criteria

**Acceptance Criteria:**
- [ ] A task template checked in `task` mode produces one result for the
  raw template and one for its rendered assignment.
- [ ] A vars file missing a template variable fails the render with the
  variable named.
- [ ] The repository contains no tree-sitter grammar definitions.

### Implementation Notes

`code` mode waits for sc-agent's tree-sitter grammars (ADR-JEV-0004).

---
````
