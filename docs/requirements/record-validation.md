# judge-jev Requirements - Record Validation

**ID Range:** REQ-JEV-0101 through REQ-JEV-0101  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-08  
**Owner:** Rand Lee  
**Version:** 0.2.0  

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
  questions, and the answers to one wave select the next wave's questions.
- Every wave MUST report, as its reason, each of its questions with the
  question's id and text, Jev's choice and Jev's confidence.
- A wave after the first MUST refine the answers of the wave before it.
- A wave after the first MUST be designed from the observed live results
  of the wave before it.
- A wave with no next wave MUST end the walk, with its verdict given by a
  rule in the tree file over that wave's answers.
- The tree MUST ship with the tool as a data file a consumer can override
  (REQ-JEV-0205); answers select the branch and the verdict, never a model
  choosing the next questions.
- A failing answer MUST report the decision-tree path that failed.
- A live run MUST log every wave as output: its composed request, Jev's
  answers, its reason and the branch or verdict they selected.

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

Rand (2026-11-08), after the first live run reported only fixed leaf text:
"every wave needs to provide some 'reason' the next wave is just to refine
it. You can't design wave-2 until you see wave-1 results so you know what
wave-2 should ask." The shipped trees therefore hold wave 1 only; a wave 2
is designed from wave 1's observed answers.

### Success Criteria

**Acceptance Criteria:**

- [ ] Fixed answers to a wave select the same next wave every run.
- [ ] Every wave's result lists each of its questions with id, text,
  choice and confidence.
- [ ] A live run's log holds each wave's request, answers, reason and
  selected branch or verdict.
- [ ] A REQ whose wave-1 `testable` question answers `no` reports `no`,
  with that answer in wave 1's reason.
- [ ] A record Raptor rejected is not sent to Jev.

### Implementation Notes

Logging goes through the sc-observability logger (REQ-JEV-0008). The
shipped trees' wave-1 rule is: `no` when any question answers `no`, else
`unclear` when any answers `unclear`, else `yes`.
