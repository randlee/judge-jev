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
- The mode MUST run as a decision tree of prompts: each wave sends several
  questions, and the answers to one wave select the next wave's questions,
  narrowing in until a leaf verdict is reached.
- The tree MUST ship with the tool as a data file a consumer can override
  (REQ-JEV-0205); answers select the branch, never a model choosing the
  next questions.
- A failing answer MUST report the decision-tree path that failed.
- A live run MUST log every wave as output: its composed request, Jev's
  answers and the branch they selected.

**MUST NOT statements:**

- The mode MUST NOT check structure that Raptor's import checks.

### Rationale

Importing is part of complying with the schema: Raptor's import
diagnostics (REQ-RAP-0012) bring a document into the schema, then this
mode judges whether each imported record is well written. Prose evaluation
uses only records that pass both.

Rand (2026-11-08): "for the 'is this adr/nfr/req high quality' mode, I
would expect this to be a decision tree of prompts. each layer of the tree
would output several questions which based on the wave-1 outputs would
result in a new set of questions to narrow in." On a dry run showing only
wave 1: "as long as real run logs all info as output (sc-agent will do logging and is
almost ready to start testing)."

### Success Criteria

**Acceptance Criteria:**

- [ ] Fixed wave-1 answers select the same wave-2 questions every run.
- [ ] A live run's log holds each wave's request, answers and selected
  branch.
- [ ] A record whose statement has no observable pass or fail outcome
  reports `no` with a path naming the testable node.
- [ ] A record Raptor rejected is not sent to Jev.

### Implementation Notes

Logging goes through the sc-observability logger (REQ-JEV-0008).
