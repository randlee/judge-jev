# judge-jev Requirements - Prose Evaluation

**ID Range:** REQ-JEV-0201 through REQ-JEV-0215  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-08  
**Owner:** Rand Lee  
**Version:** 0.1.0  

---

## Overview

judge-jev judges whether a location (prompt, skill, task template or code)
meets a Raptor-supplied REQ, NFR or ADR record. The CLI is defined in
`docs/cli.md`.

---

## REQ-JEV-0201: One record per check

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev check` MUST take one of two argument forms: a single record
  with a location and a mode, or a `--profile`.
- In the single-record form, `judge-jev check` MUST take one record id,
  given with exactly one record-kind flag: `--req` (requirement), `--adr`
  (architecture decision record) or `--nfr` (non-functional requirement).
- In the single-record form, `judge-jev check` MUST take exactly one
  `--location`.
- In the single-record form, `judge-jev check` MUST take exactly one
  `--mode`.
- Each record kind MUST use its own question set.

### Rationale

A requirement, a decision and a non-functional requirement are each
violated in a different way.

### Success Criteria

**Acceptance Criteria:**
- [ ] The same location checked with `--req` and with `--adr` sends
  different question sets.

---

## REQ-JEV-0202: One record and one location per request

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- Each Jev request MUST carry exactly one record.
- Each Jev request MUST carry exactly one location.
- A run over many pairs MUST send them as a stream of single requests.

### Rationale

Jev judges one record and location at a time; packing records into one request hides
which one failed. Batching is streaming single requests, which the batch
command already does.

### Success Criteria

**Acceptance Criteria:**
- [ ] A profile mapping one file to three records sends three requests.

---

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

## REQ-JEV-0204: Profiles map locations to records

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- judge-jev MUST read a TOML profile listing locations, each with its
  mode, the record ids that govern it, and for `task` mode a vars file.
- `judge-jev check --profile <profile>` MUST check every listed pair.
- `judge-jev check --profile <profile>` MUST report each pair's verdict.
- `judge-jev check --profile <profile>` MUST aggregate the verdicts per
  record.
- `judge-jev check --profile <profile>` MUST aggregate the verdicts per
  location.

**MUST NOT statements:**
- A profile run MUST NOT judge a pair the profile does not list.

### Rationale

The profile states which records govern which locations, so a run checks
exactly those pairs. A record id carries its kind, so one profile holds
all kinds.

### Success Criteria

**Acceptance Criteria:**
- [ ] A run over a profile produces one result per (record, location)
  pair and none for unlisted pairs.
- [ ] The report states, per record, whether it is met at every listed
  location, and names the failing locations.

---

## REQ-JEV-0205: Question sets ship with the tool

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- judge-jev MUST ship one question set per combination of record kind and
  target class (agent text or code).
- judge-jev MUST ship one quality decision tree per record kind.
- Every shipped question and prompt text MUST be approved by Rand before
  it ships.
- Question sets MUST be data files shipped with the tool.
- Quality decision trees MUST be data files shipped with the tool.
- The released tool MUST accept an override file for any question set.
- The released tool MUST accept an override file for any quality decision
  tree.
- Every result MUST carry the question-set id.
- Every result MUST carry the content digest of the file used.
- Every log entry MUST carry the question-set id.
- Every log entry MUST carry the content digest of the file used.

### Rationale

Rand: "I do not trust non-frontier agents to write prompts. I do not even
trust frontier agents to write them." The question sets are the tool's
system prompts. Getting them production-worthy means running thousands of
question variations against the released tool; a variation that needs a
code change cannot be run at that scale.

Because question sets and trees are data files, changing a question, a
tree branch or a wave needs no code change. An override file lets a
variation be tried by writing a file, never by changing or rebuilding code.
The question-set id and file digest on every result and log entry let
results from many variations of the same set be told apart and compared.

### Success Criteria

**Acceptance Criteria:**
- [ ] Each shipped question file names the approval that admitted its text.
- [ ] A result produced with an override names the override file and its
  digest.
- [ ] Two override files differing in one question produce results with
  different digests, run on the same released build.
- [ ] Adding a wave to a quality tree changes only the tree file.

---

## REQ-JEV-0206: One judgment per record and location

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- When a record is satisfied in more than one location (prompt, skill,
  agent, template or code), judge-jev MUST judge the record separately at
  each location.
- judge-jev MUST report one result per (record, location) pair.

**MUST NOT statements:**
- judge-jev MUST NOT combine a record's locations into one judgment.

### Rationale

Rand (2026-11-07): "from raptor config standpoint for judge-jev, we must
have single requirements mapped to multiple places in
prompts/skills/agents/code I would expect a separate jev query for each
location it is satisfied. We may be able to fan out a single jev call w/
<location> - <question-1-req-1> | <question-2-req-1> | <question-3-req-2>
| <question-4-req-2> | ... depending on how we can fit items in context"
Rand (2026-11-08): "batching is simply streaming of single requests."

### Success Criteria

**Acceptance Criteria:**
- [ ] A record mapped to three locations produces three results, one per
  location.
- [ ] A failure at one location is reported against that location only.

---

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

## REQ-JEV-0208: Dry run audits the composed request

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev quality` MUST accept `--dry-run`.
- `judge-jev check` MUST accept `--dry-run`.
- A dry run MUST compose every request without calling Jev.
- Each dry-run entry MUST report the record id.
- Each dry-run entry MUST report the record's Raptor source.
- Each dry-run entry MUST report the resolved location as its path, section
  or symbol.
- Each dry-run entry MUST report the digest of the location's selected
  text.
- Each dry-run entry MUST report the mode.
- Each dry-run entry MUST report the question set as its shipped id or its
  override path.
- In `task` mode, each dry-run entry MUST report the vars file.
- In `task` mode, each dry-run entry MUST report the rendered text.
- Each dry-run entry MUST report the full composed request.
- Each dry-run entry MUST report the composed request's size against the
  request limit.
- For `quality`, the dry run MUST report the decision tree.
- For `quality`, the dry run MUST report the composed wave-1 request.
- A dry run MUST fail with a typed error on anything that would make the
  live request wrong: an unresolved record or location, a render failure,
  or an oversize request.

### Rationale

The caller must know the prompt will be built correctly before any text
leaves the machine. A `quality` dry run stops at wave 1 because later
waves depend on live answers.

### Success Criteria

**Acceptance Criteria:**
- [ ] A dry run makes no network call and reports one entry per request a
  live run would send.
- [ ] A dry run over a task location with a missing variable fails naming
  the variable.

---

## REQ-JEV-0209: Record quality command

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev quality` MUST take one or more record ids.
- `judge-jev quality` MUST take each record id with one record-kind flag:
  `--req` (requirement), `--adr` (architecture decision record) or `--nfr`
  (non-functional requirement).
- Every record-kind flag of `judge-jev quality` MUST be repeatable.
- `judge-jev quality` MUST judge each record with its kind's quality
  decision tree (REQ-JEV-0101).
- All records of one `judge-jev quality` invocation MUST be logged under
  one run name.

### Rationale

Quality and compliance are separate questions about separate inputs. One
run name per invocation groups a measurement over many records in the
log.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every request `judge-jev quality --req <id>` sends carries only the
  record and questions from the REQ quality tree.

---

## REQ-JEV-0210: Validate command

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev validate` MUST take one input file with one input-kind flag:
  `--tree` (quality tree), `--questions` (question set), `--answers`
  (answers file), `--index` (Raptor import index) or `--requests` (batch
  request stream).
- `judge-jev validate` MUST check the file with the model `judge-jev`
  applies to that input kind before its first Jev request (ADR-JEV-0005).
- Every refusal from `judge-jev validate` MUST name the field path and the
  rule the field breaks.
- `judge-jev validate --answers` MUST apply the answers-file envelope that
  `--answers-file` applies before the first request: an object of string keys,
  each an object or a non-empty list of objects, an object with `__error__`
  holding only a string code of at most 64 characters. The answers file
  stands in for Jev's response, so what an answer holds (its questions,
  choices and probabilities) is not part of the envelope; it is checked after
  the send as `JEV.RESPONSE_INVALID`.

**MUST NOT statements:**
- `judge-jev validate` MUST NOT call Jev.

### Rationale

A tree variation checked before a run costs nothing; one refused after a
paid call wastes it.

### Success Criteria

**Acceptance Criteria:**
- [ ] Every input the sweep tests refuse in `quality` is refused by
  `judge-jev validate` with the same field path.
- [ ] The shipped trees and question sets pass `judge-jev validate`.

---

## REQ-JEV-0211: A typed result for every input

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- For every input, every `judge-jev` command MUST print exactly one JSON
  object: its result or a typed error.
- `judge-jev` MUST refuse an invalid tree, question set, index, request
  stream or run directory before its first Jev request.
- `judge-jev` MUST check that every log event of a request (the request,
  Jev's largest possible answer and the result) fits the logger's event
  size limit before sending the request.

### Rationale

Rand Lee, 2026-11-08: "Crash is not acceptable for any input." A refusal
after a paid call wastes the call; a crash loses its answer.

### Success Criteria

**Acceptance Criteria:**
- [ ] The sweep tests (every field of a tree, index and answers file
  replaced by each of a fixed list of wrong values, deleted or given an
  extra key, and raw JSON no value expresses) produce no `SCRIPT.INTERNAL`
  and no refusal after a request is sent.
- [ ] Invalid UTF-8 on stdin is refused with `INPUT.MALFORMED`.

---

## REQ-JEV-0212: Targeted definitions

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- A definition MUST be attachable to a record alone, or to a record and
  one location under evaluation.
- A request about a record MUST carry, in its state next to the record, only
  the definitions attached to that record alone, plus those attached to
  that record and the request's location.
- A request with no matching definition MUST be identical to the request
  sent without definitions.
- `judge-jev` MUST refuse, before sending, a request whose definitions take
  it over the size limit, and MUST NOT truncate a definition.
- Every request's log event MUST record the digest of each definition it
  carried.

### Rationale

Rand Lee, 2026-11-08: "we can NOT write a single definition file and add it
to every prompt" when running over 1000 to 2000 records with 1 to 200
locations each. A record-only definition "makes the req/nfr/adr w/ confusing
term carry the definition w/ it for all jev calls"; a record-and-location
definition "would only be added to specific data (code/prompt/skill) which
requires clarification".

### Success Criteria

**Acceptance Criteria:**
- [ ] With definitions linked to record A only, the requests for record B
  are byte-identical to a run without definitions.
- [ ] The requests for record A carry exactly A's definitions, and their log
  events list those definitions' digests.
- [ ] A definition attached to record A and location X is carried by A's
  request for X and by no other request about A.

---

## REQ-JEV-0213: A definition is kept only when it changes an answer

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev` MUST provide a comparison that runs the requests a candidate
  definition would reach, with and without it, and reports for each answer
  the change in choice and in confidence.
- The comparison MUST report whether the definition is material: whether
  any answer's choice changed, or its confidence changed by at least the
  given minimum.
- The comparison MUST record the minimum confidence change it applied.

### Rationale

Rand Lee, 2026-11-08: "if adding the definition does not impact the scores
used in the rubric, they aren't necessary to add"; "material would need to
impact confidence or flip answer".

### Success Criteria

**Acceptance Criteria:**
- [ ] With fixture answers where the definition flips one answer, the
  comparison reports it as material.
- [ ] With fixture answers that are the same with and without the
  definition, the comparison reports it as not material.

---

## REQ-JEV-0214: Question ids are unique within a scope

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- Every question loaded in one scope (by default the repository) MUST have
  a `jj:id` that no other question in that scope uses. This covers
  judge-jev's trees and every consumer extension's.

### Rationale

Rand Lee, 2026-11-08: "We would need to make sure all questions in
judge-jev AND in consumer extensions follow a naming policy for uniqueness
w/in that scope (repo is typical scope)."

### Success Criteria

**Acceptance Criteria:**
- [ ] Two trees in one scope that each define a question with the same
  `jj:id` but different IRIs are reported as an error naming both IRIs.

---

## REQ-JEV-0215: Doctor command

**Status:** Draft  

### Requirement Statement

**MUST statements:**
- `judge-jev doctor` MUST validate every tree, question set and definitions
  file in the scope against its schema and the ontology's shapes, including
  edges and cycles, and MUST report each failure as an error.
- `judge-jev doctor` MUST report, as warnings that do not fail the command:
  - a definition with no attachment;
  - an attachment to a record the Raptor index does not hold, or to a
    location that does not exist;
  - a definition whose source does not exist.
- `judge-jev doctor` MUST NOT call Jev.

### Rationale

Rand Lee, 2026-11-08: "I would expect judge-jev doctor to report orphans/dead
links as warnings, it would also run schema validation and verify ontology
followed and no cycles."

### Success Criteria

**Acceptance Criteria:**
- [ ] A scope with one orphan definition exits 0 with one warning naming it.
- [ ] A scope with a tree that has a cycle exits non-zero with an error
  naming the cycle.
