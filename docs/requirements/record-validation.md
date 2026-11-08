# judge-jev Requirements - Record Validation

**ID Range:** REQ-JEV-0101 through REQ-JEV-0101  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-07  
**Owner:** Rand Lee  
**Version:** 0.1.0  

---

## Overview

judge-jev verifies that a REQ, NFR or ADR is well written.

---

## REQ-JEV-0101: Record quality mode

**Status:** Proposed  

### Requirement Statement

**MUST statements:**

- judge-jev MUST provide a mode that asks whether one REQ, NFR or ADR is
  well written.
- The mode MUST judge only records that Raptor imported without
  diagnostics.
- A failing answer MUST report the decision-tree path that failed.

**MUST NOT statements:**

- The mode MUST NOT check structure that Raptor's import checks.

### Rationale

Importing is part of complying with the schema: Raptor's import
diagnostics (REQ-RAP-0012) bring a document into the schema, then this
mode judges whether each imported record is well written. Prose evaluation
uses only records that pass both.

### Success Criteria

**Acceptance Criteria:**

- [ ] A record whose statement has no observable pass or fail outcome
  reports `no` with a path naming the testable node.
- [ ] A record Raptor rejected is not sent to Jev.
