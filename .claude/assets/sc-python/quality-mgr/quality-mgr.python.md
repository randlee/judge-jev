# Python Quality Manager Supplement

This file augments `quality-mgr.md` for Python repositories. It does not replace
the core prompt. The reviewer matrix and commands are data in
`.claude/project/quality-mgr.toml`; this file says how the two Python
reviewers are used and how to render their assignments.

## Python Reviewers

- `python-qa-agent`: runs `pyright` and the test suite on the changed files,
  checks that tests are deterministic, and reads the tests against the code.
- `python-best-practices-agent`: structural review keyed by stable practice
  ids `PBP-001` to `PBP-007` (Result not raise, Rust types and traits,
  pydantic schemas, pyright clean, module seams, typed errors, deterministic
  tests). The ids are defined in its prompt.

The generic reviewers (`req-qa`, `arch-qa`, `flaky-test-qa`, the ceremony
reviewers, `blastr`) are language-independent and run from the core prompt.

## Assignment Types

### Plan gate

Docs-only. Add `python-best-practices-agent` in `doc_review` mode when the
requirements or ADRs under review imply a Python design decision (an error
model, a schema, a Rust-binding boundary). Do not launch `python-qa-agent`.

### Sprint and fix QA

- Always launch `python-qa-agent` when Python changed.
- Launch `python-best-practices-agent` in `sprint_review` mode with the
  manifest's `practice_ids_sprint`.

#### Fix-round dispatch gate

The best-practices reviewer digs aggressively and surfaces new issues even
when a fix is right, so a fix round does not re-run it open-ended:

- In a fix round, dispatch it only when a triaged `PBP-*` finding is assigned
  to verify. Pass `carry_forward_findings_json` with those ids so the rendered
  assignment sets `findings_scope_locked: true`; it then reports a disposition
  for those ids only.
- An initial or phase-end review has no prior findings: omit
  `carry_forward_findings_json` (it defaults to `"[]"`).
- A new finding surfaced during a scope-locked round is not part of that
  round's verdict. Send it to the lead for a later triage pass.

### Phase-end review

Launch `python-qa-agent` and `python-best-practices-agent` in `phase_end` mode
with `practice_mode: all`.

## Rendering Assignments

Render with `sc-compose` from `templates_root` in the manifest. Every
assignment carries the parent assignment's exact `branch`, `commit` and
`worktree_path`; they are pinning fields, not hints.

```bash
_VARS=$(mktemp)
cat > "$_VARS" <<'JSON'
{
  "review_mode": "sprint_review",
  "worktree_path": "/absolute/path/to/worktree",
  "branch": "feat/branch-name",
  "commit": "abc1234",
  "review_targets": ["plugins/", "scripts/", "tests/"],
  "practice_mode": "selected",
  "practice_ids": ["PBP-001", "PBP-003", "PBP-004"]
}
JSON
sc-compose render \
  --root .claude/assets/sc-python/quality-mgr/templates \
  --file python-best-practices-assignment.json.j2 \
  --var-file "$_VARS"
rm -f "$_VARS"
```

`python-qa-assignment.json.j2` takes the same fields without the practice
fields.

## Render Verification Rule

When editing a template, render it with `sc-compose` for `doc_review`,
`sprint_review` and `phase_end` before stopping. Use native arrays for
list-shaped fields (`review_targets`, `practice_ids`).
