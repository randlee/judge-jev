## REQ-JEV-0204: Profiles map locations to records

**Status:** Draft  

### Requirement Statement

Definitions: TOML is Tom's Obvious Minimal Language, a configuration file
format. A profile is a TOML file listing locations, each with its mode and
the ids of the records that govern it. A location is the text judged against
a record: a whole file (`path`), a Markdown section (`path#Heading`) or a
code symbol (`path::Symbol`) (REQ-JEV-0207). A mode (target mode) names what
a location holds: `prompt` (prompt text), `skill` (a skill file), `task` (a
task template) or `code` (source code). A pair is one (record, location)
pair. A vars file holds the values of a task template's variables.

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

