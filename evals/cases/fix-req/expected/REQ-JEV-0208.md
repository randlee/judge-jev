## REQ-JEV-0208: Dry run audits the composed request

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. Raptor is the requirements tool that imports Markdown records
(ADR-JEV-0002). A dry run is a run with `--dry-run`: it composes every
request and sends none. The digest of a text is its SHA-256. A mode (target
mode) names what a location holds: `prompt` (prompt text), `skill` (a skill
file), `task` (a task template) or `code` (source code). A question set is
the data file of questions sent to Jev; its shipped id is the `id` of a set
shipped with the tool, its override path the file given with `--questions`.
A vars file holds the values of a task template's variables. The request
limit is 24000 bytes by default. A quality decision tree is the data file of
questions that judges whether a record is well written: waves of questions
(REQ-JEV-0101). The wave-1 request is the request for its first wave.

**MUST statements:**
- `judge-jev quality` MUST accept `--dry-run`.
- `judge-jev check` MUST accept `--dry-run`.
- A dry run MUST compose every request with no Jev call.
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

