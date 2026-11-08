# judge-jev Requirements - Prose Evaluation

**ID Range:** REQ-JEV-0201 through REQ-JEV-0209  
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
- `judge-jev check` MUST take exactly one of `--req`, `--adr` or `--nfr`
  with one record id, plus one `--location` and one `--mode`, or a
  `--profile`.
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
- Each Jev request MUST carry exactly one record and one location.
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
- judge-jev MUST support the target modes `prompt`, `skill`, `task` and
  `code`.
- In `task` mode judge-jev MUST judge both the raw template and an
  assignment rendered by sc-compose in strict mode from the vars file named
  by `--vars` or by the profile.
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
- `judge-jev check --profile <profile>` MUST check every listed pair and
  report each pair's verdict, aggregated per record and per location.

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
- judge-jev MUST ship its question sets, one per record kind and target
  class (agent text or code), plus one quality decision tree per record kind.
- Every shipped question and prompt text MUST be approved by Rand before
  it ships.
- Question sets and quality decision trees MUST be data files shipped
  with the tool, so changing a question, a tree branch or a wave needs no
  code change.
- The released tool MUST accept an override file for any question set or
  tree, so a variation is tried by writing a file, never by changing or
  rebuilding code.
- Every result and log entry MUST carry the question-set id and the
  content digest of the file used, so results from many variations of the
  same set can be told apart and compared.

### Rationale

Rand: "I do not trust non-frontier agents to write prompts. I do not even
trust frontier agents to write them." The question sets are the tool's
system prompts. Getting them production-worthy means running thousands of
question variations against the released tool; a variation that needs a
code change cannot be run at that scale.

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
- A location MUST be `path` (whole file), `path#Heading` (a Markdown
  section, from the heading to the next heading of the same or higher
  level), or `path::Symbol` (a code symbol resolved by sc-agent's
  tree-sitter grammars).
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
- `quality` and `check` MUST accept `--dry-run`, which composes every
  request without calling Jev.
- Each dry-run entry MUST report the record id and its Raptor source, the
  resolved location (path, section or symbol, digest of the selected
  text), the mode, the question set (shipped id or override path), for
  `task` mode the vars file and rendered text, the full composed request,
  and its size against the request limit.
- For `quality`, the dry run MUST report the decision tree and the composed
  wave-1 request; later waves depend on live answers.
- A dry run MUST fail with a typed error on anything that would make the
  live request wrong: an unresolved record or location, a render failure,
  or an oversize request.

### Rationale

The caller must know the prompt will be built correctly before any text
leaves the machine.

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
- `judge-jev quality` MUST take one or more record ids, each given with
  `--req`, `--adr` or `--nfr` (repeatable), and judge each record with its
  kind's quality decision tree (REQ-JEV-0101).
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
