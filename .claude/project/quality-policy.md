# Repository Quality Policy

Repository-specific QA policy. Reusable agents and skills read this file
instead of embedding repository names, commands, interfaces or approval
authorities in their prompts. What `quality-mgr` executes (reviewer matrix,
commands, templates) is in `.claude/project/quality-mgr.toml`; this file holds
what a reviewer interprets. Do not repeat the matrix here.

## Repository Baseline

- Default comparison branch: `develop`; release branch `main`.
- Requirements: `docs/requirements/*.md`. Each `## REQ-JEV-nnnn:` or
  `## NFR-JEV-nnnn:` section is a record.
- ADRs: `docs/adr/*.md`. Each `## ADR-JEV-nnnn:` section is a record.
- CLI contract: `docs/cli.md`. Diagrams: `docs/diagrams/`.
- Product code: `plugins/sc-judge-jev/` (templates rendered by the installer)
  and `scripts/`. Tests: `tests/sc-judge-jev/`.
- No sprint docs or project plan exist. A QA assignment is an ATM message from
  `jj-lead` naming a PR, branch and commit.
- Binding records: a REQ, NFR or ADR is binding when its status is Active or
  Approved. Draft and Proposed records do not bind, and no change may depend
  on one.

## Prompt and skill review

Every agent prompt, skill, command and reference file is reviewed against
`claude-code-skills-agents-guidelines.md` in randlee/synaptic-canvas:

- Git URL: https://github.com/randlee/synaptic-canvas/blob/main/docs/claude-code-skills-agents-guidelines.md
- Usual local copy: `../synaptic-canvas/docs/claude-code-skills-agents-guidelines.md`

Read the local copy when it exists; otherwise fetch the URL. A prompt that
breaks the guidelines (versioned frontmatter, one responsibility, fenced JSON
output, progressive disclosure, CLI dependency check) is a finding. That
applies to shipped templates under `plugins/` and to `.claude/` here.

## Python standards

Applies to all Python in this repository. The sc ecosystem follows a
Python-over-Rust pattern; reviewers hold Python to it
(`python-best-practices-agent`, practice ids `PBP-*`):

- `pyright` is the type checker. New and changed code passes it. No `Any`
  where a type exists; a `# type: ignore` names the error code and the reason.
- Fallible functions return a `Result[T, E]` and do not raise. An exception is
  allowed for a programmer error, or at a process boundary that must turn it
  into a typed error.
- Use the PyO3-bound Rust types the ecosystem exposes. Write modular code
  against Protocols that mirror the Rust traits. Do not re-implement a type or
  trait the bindings provide.
- Every schema (requests, results, settings, records, fixtures) is validated
  by pydantic or an equivalent. A raw `dict` does not cross a module boundary.
- Errors are typed: `code`, `message`, `recoverable`, `suggested_action`.

`pyright` is not yet configured in this repository. Until it is, reviewers run
`pyright` on the changed `.py` files and treat each error as a finding; adding
the configuration is its own planned change.

## Validation Policy

Flaky tests are prohibited by design. A test that relies on a race, timing, a
sleep, event-loop ordering or load is redesigned to drive the logic with
controlled inputs. Retries, skips, serialization and longer timeouts are not
fixes. `flaky-test-qa` applies this.

Phase-end and PR proof commands are in the manifest. CI (`tests.yml`) runs the
same unit suite, `check_version_sync.py` and the installer jobs.

## Versioning

Every PR that changes code or a published skill raises `VERSION` and adds a
`CHANGELOG.md` entry; `check_version_sync.py` requires the 21 declarations to
agree. A docs-only change does not bump.

## Reviewer discipline

- `req-qa` and `arch-qa` run on every round. Later rounds are scoped to the
  carried findings and the fix diff.
- `extensibility-qa` runs every round: open-ended on the first, and on later
  rounds locked to its carried findings plus the fix diff when that diff
  changes a public surface or removes an option, so cuts made to simplify are
  checked against named consumers.
- `ceremony-finding-screen` runs over every round that has findings, before the
  report is posted. `blastr` runs over blocking and important findings. Both
  recommend only; the lead and the user decide.
- `ceremony-qa` runs on any change that adds a process artifact, gate, check or
  document the user did not ask for.
- A reviewer never downgrades or drops a finding on a recommender's say-so.

## Governed Interfaces

No governed interface is declared. Until this section names one, its
compatibility rule and approval authority, `schema-reviewer` is not used.

## Repository Exceptions

None.
