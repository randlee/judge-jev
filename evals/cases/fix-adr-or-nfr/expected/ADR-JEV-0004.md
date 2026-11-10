## ADR-JEV-0004: Code references are outside the first version

**Status:** Draft  

### Context

Records will eventually govern code as well as prompts, but selecting code
needs tree-sitter grammars, which sc-agent defines and which may not be
complete yet. The problem is what the first version judges while those
grammars are unfinished.

### Decision

The first version judges prompts, skills and task templates only. Code
references come later through tree-sitter grammars that sc-agent defines;
judge-jev never defines its own grammars. sc-agent's grammars may not be
complete yet.

### Rationale

Prompt and task wording is the immediate risk; code selection needs the
tree-sitter work first.

### Consequences

**Positive:**

- The first version ships without a code-reference model.

**Negative:**

- Code is not judged until the tree-sitter extension exists.

### Alternatives Considered

#### Alternative 1: judge-jev defines its own tree-sitter grammars

**Description:** Ship grammars inside judge-jev so code is judged now.

**Why Rejected:** sc-agent owns the grammars so every consumer selects code
the same way (REQ-JEV-0203).

#### Alternative 2: Line-range locations for code

**Description:** Reference code by file line ranges instead of symbols.

**Why Rejected:** Line ranges drift on every edit; symbols survive
(REQ-JEV-0207).

---

