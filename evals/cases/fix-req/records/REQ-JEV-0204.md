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

