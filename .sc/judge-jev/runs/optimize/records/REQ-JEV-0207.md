# REQ-JEV-0207

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [2, 2, 2, 2, 2, 2] | 6/6 | 0.767 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.780 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.776 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.777; final fails [0, 0, 0] margin 0.772.

Selection: pruned (paired runs: fixes-only 0 failing runs, margin 0.7828; pruned 0 failing runs, margin 0.7736).

## Kept tweaks (text present in the final record) and measured effect

- remove defs (proposed by i1:haiku-B)
  - old: `whose Rust Jev tool will replace judge-jev's Python Jev core (ADR-JEV-0007)`
  - new: `(removed)`
  - i1 haiku-B: m1: fails 0, margin 0.795; m2: fails 0, margin 0.792 (reference margin 0.782, reference fails mean 0.00)
- remove defs (proposed by i1:opus-B)
  - old: `; its rules decide which text belongs to which heading`
  - new: `(removed)`
  - i1 opus-B: m1: fails 0, margin 0.789; m2: fails 0, margin 0.787 (reference margin 0.782, reference fails mean 0.00)
- remove s5 (proposed by i1:opus-B)
  - old: `for the same file`
  - new: `(removed)`
  - i1 opus-B: m1: fails 0, margin 0.780; m2: fails 0, margin 0.778 (reference margin 0.782, reference fails mean 0.00)
- remove defs (proposed by i1:sonnet-B)
  - old: `that find a named symbol in source code`
  - new: `(removed)`
  - i1 sonnet-B: m1: fails 0, margin 0.765; m2: fails 0, margin 0.780 (reference margin 0.782, reference fails mean 0.00)
- reword defs (proposed by i2:haiku-B)
  - old: `the requirements tool that imports Markdown records.`
  - new: `the requirements tool.`
  - i2 haiku-B: m1: fails 0, margin 0.775; m2: fails 0, margin 0.763 (reference margin 0.790, reference fails mean 0.00)

## Definitions pruned (greedy -> final)

- Raptor is the requirements tool that imports Markdown records; its rules decide which text belongs to which heading.
- sc-agent is the agent tool whose Rust Jev tool will replace judge-jev's Python Jev core (ADR-JEV-0007).
- Tree-sitter grammars are the parsers that find a named symbol in source code.

## Definitions added or reworded (greedy -> final)

- Raptor is the requirements tool.
- sc-agent is the agent tool.
- Tree-sitter grammars are the parsers.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -3,6 +3,9 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: Raptor is the requirements tool. sc-agent is the agent tool.
+Tree-sitter grammars are the parsers.
 
 **MUST statements:**
 - A location MUST take one of three forms: `path`, `path#Heading` or
@@ -12,8 +15,7 @@
   heading to the next heading of the same or higher level.
 - A `path::Symbol` location MUST select a code symbol resolved by
   sc-agent's tree-sitter grammars.
-- Markdown sections MUST be parsed by the same rules Raptor uses for the
-  same file.
+- Markdown sections MUST be parsed by the same rules Raptor uses.
 
 **MUST NOT statements:**
 - A location MUST NOT be a line range.

```

## Diff: greedy (previous commit) -> final

```diff
--- greedy
+++ final
@@ -4,11 +4,8 @@
 
 ### Requirement Statement
 
-Definitions: Raptor is the requirements tool that imports Markdown records;
-its rules decide which text belongs to which heading. sc-agent is the agent
-tool whose Rust Jev tool will replace judge-jev's Python Jev core
-(ADR-JEV-0007). Tree-sitter grammars are the parsers that find a named
-symbol in source code.
+Definitions: Raptor is the requirements tool. sc-agent is the agent tool.
+Tree-sitter grammars are the parsers.
 
 **MUST statements:**
 - A location MUST take one of three forms: `path`, `path#Heading` or
@@ -18,8 +15,7 @@
   heading to the next heading of the same or higher level.
 - A `path::Symbol` location MUST select a code symbol resolved by
   sc-agent's tree-sitter grammars.
-- Markdown sections MUST be parsed by the same rules Raptor uses for the
-  same file.
+- Markdown sections MUST be parsed by the same rules Raptor uses.
 
 **MUST NOT statements:**
 - A location MUST NOT be a line range.

```

## Original text

````markdown
## REQ-JEV-0207: Location syntax

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- A location MUST take one of three forms: `path`, `path#Heading` or
  `path::Symbol`.
- A `path` location MUST select the whole file.
- A `path#Heading` location MUST select a Markdown section, from the
  heading to the next heading of the same or higher level.
- A `path::Symbol` location MUST select a code symbol resolved by
  sc-agent's tree-sitter grammars.
- Markdown sections MUST be parsed by the same rules Raptor uses for the
  same file.

**MUST NOT statements:**
- A location MUST NOT be a line range.

### Rationale

Line ranges drift on every edit; headings and symbols survive. One
Markdown parsing rule keeps judge-jev and Raptor agreeing on what a
section is.

### Success Criteria

**Acceptance Criteria:**
- [ ] `path#Heading` selects the same text Raptor attributes to that
  heading.
- [ ] A heading or symbol that does not resolve is a typed error naming the
  location.

### Implementation Notes

Open: which Raptor parser and heading rules judge-jev matches, and whether
paths in a profile are relative to the profile or to the repository root.

---
````

## Final text

````markdown
## REQ-JEV-0207: Location syntax

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool. sc-agent is the agent tool.
Tree-sitter grammars are the parsers.

**MUST statements:**
- A location MUST take one of three forms: `path`, `path#Heading` or
  `path::Symbol`.
- A `path` location MUST select the whole file.
- A `path#Heading` location MUST select a Markdown section, from the
  heading to the next heading of the same or higher level.
- A `path::Symbol` location MUST select a code symbol resolved by
  sc-agent's tree-sitter grammars.
- Markdown sections MUST be parsed by the same rules Raptor uses.

**MUST NOT statements:**
- A location MUST NOT be a line range.

### Rationale

Line ranges drift on every edit; headings and symbols survive. One
Markdown parsing rule keeps judge-jev and Raptor agreeing on what a
section is.

### Success Criteria

**Acceptance Criteria:**
- [ ] `path#Heading` selects the same text Raptor attributes to that
  heading.
- [ ] A heading or symbol that does not resolve is a typed error naming the
  location.

### Implementation Notes

Open: which Raptor parser and heading rules judge-jev matches, and whether
paths in a profile are relative to the profile or to the repository root.

---
````
