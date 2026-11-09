# judge-jev Requirements - Record Validation

**ID Range:** REQ-JEV-0101 through REQ-JEV-0101  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-08  
**Owner:** Rand Lee  
**Version:** 0.2.1  

---

## Overview

judge-jev verifies that a REQ, NFR or ADR is well written.

---

## REQ-JEV-0101: Record quality mode

**Status:** Proposed  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. Raptor is the requirements tool
that imports Markdown records into its record store and serves them to other
tools (ADR-JEV-0002). Diagnostics are the problems Raptor's import reports
for a record, and the structure it checks is the record format. A quality
decision tree is a data file of prompts (questions to Jev) in waves; a wave
is one set of questions, and its reason is the report of its questions and
Jev's answers. A per-statement wave asks its questions once for each MUST
and MUST NOT statement. A verdict rule is a rule in the tree file that turns
a wave's answers into a verdict (`yes` or `no`). The walk is the sequence of
waves from the first to the one that gives the verdict; its decision-tree
path is the list of those waves' ids. A consumer is a repository that uses
judge-jev.

**MUST statements:**

- judge-jev MUST provide a mode that reports, for one requirement (REQ),
  non-functional requirement (NFR) or architecture decision record (ADR),
  the verdict of that record kind's quality decision tree.
- The mode MUST judge only records that Raptor imported without
  diagnostics.
- The mode MUST run as a decision tree of prompts: each wave sends several
  questions, and the answers to one wave select the next wave's questions.
- Every wave MUST report, as its reason, each of its questions with the
  question's id and text, Jev's choice and Jev's confidence.
- A wave the tree marks per statement MUST send one request for each MUST
  and MUST NOT statement of the record.
- Each per-statement request MUST carry its statement with the whole record
  as context.
- A per-statement wave's reason MUST list each statement's index and text
  with each question's id, choice and confidence.
- A per-statement wave's verdict rule MUST be able to fire when any one
  statement's answers match it.
- A per-statement wave's verdict MUST name the statements whose answers
  fired its rule.
- A per-statement request that gets no answer MUST fail with an error that
  names its statement.
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

Rand (2026-11-08) approved per-statement waves: one request per MUST / MUST
NOT statement, with that statement plus the whole record as context, so a
failure names the statement to fix.

### Success Criteria

**Acceptance Criteria:**

- [ ] Fixed answers to a wave select the same next wave every run.
- [ ] Every wave's result lists each of its questions with id, text,
  choice and confidence.
- [ ] A live run's log holds each wave's request, answers, reason and
  selected branch or verdict.
- [ ] A REQ with two MUST statements and one SHOULD statement sends two
  wave-1 requests, one per MUST statement.
- [ ] A REQ whose third statement answers `check: none` reports `no`, names
  statement 3, and lists every statement's answers in wave 1's reason.
- [ ] A dry run shows the composed wave-1 request for every statement.
- [ ] A record Raptor rejected is not sent to Jev.

### Implementation Notes

Logging goes through the sc-observability logger (REQ-JEV-0008). A
per-statement node sets `"per": "statement"`, `statements` (the record
field holding the statements) and `modals` (the modals judged); each
statement is one request whose item text is `{statement, record}`. The
shipped REQ and NFR trees ask, per statement, `obligations`, `joined_by`,
`term` and `check`; the ADR tree asks, per record, `context`,
`alternatives` and `consequences`. Each option's criterion carries its fix
hint, and the reason reports it.
