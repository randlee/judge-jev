# adr-jev-product - judge-jev Product Decisions

**ID Range:** ADR-JEV-0001 through ADR-JEV-0004  
**Version:** 0.1.0  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-07  
**Decision Date:** 2026-11-07  
**Owner:** Rand Lee  

## Context

judge-jev checks prompts, skills and task templates against requirement
records. These decisions fix where it gets records, how it calls Jev and
what the first version leaves out.

---

## ADR-JEV-0001: Keep the Jev core unchanged until its Rust replacement

**Status:** Draft  

### Context

judge-jev's Jev core (the batch command, request and result contracts,
key lookup and remote-judge consent) is copied from an existing
implementation. A Rust implementation, exposed through PyO3 bindings or a
CLI, will replace that Python core.

### Decision

The Jev core keeps its architecture and contracts unchanged. It changes
only to fix a defect.

### Rationale

An unchanged core lets the Rust implementation replace it with no change
to its callers.

### Consequences

**Positive:**

- The Rust replacement is a drop-in.

**Negative:**

- Improvements to the core wait for the Rust implementation.

## ADR-JEV-0002: Query records through Raptor over local SQLite

**Status:** Draft  

### Context

Requirements move to a Dolt server as the single source of truth, with
the Raptor CLI as the access path.

### Decision

judge-jev reads records only through Raptor, which queries a local SQLite
database: built on the fly from Markdown now, pulled from a Dolt branch
later.

### Rationale

Querying SQLite is the same work either way, so the source can change
without touching judge-jev.

### Consequences

**Positive:**

- The move to Dolt does not change judge-jev.

**Negative:**

- judge-jev depends on Raptor's query contract; Raptor notifies judge-jev
  maintenance before changing it.

## ADR-JEV-0003: Judge record quality instead of loosening the schema

**Status:** Proposed  

### Context

Raptor rejects records missing required sections, such as statements
written as plain prose.

### Decision

Raptor's schema stays strict. Raptor's import diagnostics explain why a
record does not fit the schema; judge-jev's quality mode then explains why
an imported record is not well written.

### Rationale

An explained rejection gets the document fixed; a looser schema stores
records that cannot be judged.

### Consequences

**Positive:**

- Every record judge-jev uses has typed statements and criteria.

**Negative:**

- Corpora with prose-only records need editing before import, guided by
  the import diagnostics.

## ADR-JEV-0004: Code references are outside the first version

**Status:** Draft  

### Context

Records will eventually govern code as well as prompts.

### Decision

The first version judges prompts, skills and task templates only. Code
references come later through a tree-sitter grammar extension in
sc-agent.

### Rationale

Prompt and task wording is the immediate risk; code selection needs the
tree-sitter work first.

### Consequences

**Positive:**

- The first version ships without a code-reference model.

**Negative:**

- Code is not judged until the tree-sitter extension exists.
