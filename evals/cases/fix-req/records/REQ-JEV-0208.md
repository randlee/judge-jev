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

