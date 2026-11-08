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
implementation, and a Rust implementation, exposed through PyO3 bindings or
a command-line interface (CLI), will replace that Python core. The problem
is whether the Python core may change before then: any change to its
architecture or contracts is a change the Rust replacement must reproduce,
or its callers break when the replacement lands.

### Decision

The Jev core keeps its architecture and contracts unchanged. It changes
only to fix a defect, or to replace its run log with the sc-observability
logger (REQ-JEV-0008).

### Rationale

An unchanged core lets the Rust implementation replace it with no change
to its callers.

### Consequences

**Positive:**

- The Rust replacement is a drop-in.

**Negative:**

- Improvements to the core wait for the Rust implementation.

### Alternatives Considered

#### Alternative 1: Improve the Python core before the Rust replacement

**Description:** Change the copied core's architecture or contracts now.

**Why Rejected:** The Rust implementation could then not replace the core
without a change to its callers.

## ADR-JEV-0002: Query records through Raptor over local SQLite

**Status:** Draft  

### Context

judge-jev needs requirement records to judge, and their source is
changing: requirements move from Markdown files to a Dolt server as the
single source of truth, with the Raptor command-line interface (CLI) as
the access path. Raptor owns the record schema and every conversion
(REQ-JEV-0001). The problem is how judge-jev reads records so that neither
the move to Dolt nor a Raptor schema change breaks it.

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

### Alternatives Considered

#### Alternative 1: Parse record Markdown directly

**Description:** judge-jev reads the record Markdown files itself.

**Why Rejected:** Raptor owns the schema and every conversion; a parser in
judge-jev breaks when Raptor changes them (REQ-JEV-0001).

#### Alternative 2: Query the record store with SQL directly

**Description:** judge-jev runs its own SQL against the record store.

**Why Rejected:** Raptor owns the schema; judge-jev's own queries break when
Raptor changes it (REQ-JEV-0001).

## ADR-JEV-0003: Judge record quality instead of loosening the schema

**Status:** Proposed  

### Context

Raptor rejects records missing required sections, such as statements
written as plain prose, so corpora with prose-only records do not import.
judge-jev can judge only records with typed statements and criteria. The
problem is how such records get into a judgeable form: by loosening
Raptor's schema to accept them, or by keeping it strict and explaining
what to fix.

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

### Alternatives Considered

#### Alternative 1: Loosen Raptor's schema

**Description:** Accept records missing required sections, such as
prose-only statements.

**Why Rejected:** A looser schema stores records that cannot be judged.

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
