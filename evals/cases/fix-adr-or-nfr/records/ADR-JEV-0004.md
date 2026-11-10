## ADR-JEV-0004: Code references are outside the first version

**Status:** Draft  

### Context

Records will eventually govern code as well as prompts.

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

---

