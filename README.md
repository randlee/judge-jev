# judge-jev

judge-jev verifies that a repository's implementation meets its
requirements. For every requirement record (REQ, NFR, ADR) and every place
that implements it, whether a prompt, agent, skill, task template or code, it
reports whether that place meets the requirement, and why not when it fails.

The output is one verdict per (record, location) pair (REQ-JEV-0206): which
requirements are met, where, and which are not.

## How it works

Each run has four steps:

1. **Locate requirements.** It reads the records from the repository through
   Raptor, never by parsing Markdown itself (REQ-JEV-0001, REQ-JEV-0006).
2. **Link each requirement to its implementation.** A profile maps each
   record to the locations that implement it (REQ-JEV-0204). One record
   usually has several locations.
3. **Select the target mode.** Each location is judged in its target mode,
   with that mode's questions (see Modes).
4. **Judge.** For each (record, location) pair, approved questions are sent
   to TypeSafe's Jev, and its typed answers decide pass or fail
   (REQ-JEV-0201, REQ-JEV-0205).

## CLI

Two primitives, each composing single Jev requests, plus a profile run that
aggregates them, and `validate` checks an input file without calling Jev.
Full definitions: [docs/cli.md](docs/cli.md); prompt
composition diagrams: [docs/diagrams/](docs/diagrams/).

```
judge-jev quality (--req|--adr|--nfr <id>)... [--definitions <file>]...
judge-jev check   --req|--adr|--nfr <id> --location <loc> --mode prompt|skill|task|code
judge-jev check   --profile <profile>
judge-jev validate --tree|--questions|--answers|--index|--requests <file>   # '-' = stdin
judge-jev compare-definition (--req|--adr|--nfr <id>) --index <file> --definition <iri>...
judge-jev doctor [<path>...] [--index <file>]
# check, quality: [--questions <file>] [--dry-run]
```

`validate` checks a file with the model judge-jev applies to it before its
first request: no Jev call, no key, no log (REQ-JEV-0210). Check a tree
variation with `judge-jev validate --tree <file>` before a run.

A **definition** (`.sc/judge-jev/*.definitions.ttl`) tells Jev what a term
means for a record, or for a record and a location, and travels in the request
state without changing a question (ADR-JEV-0008). `compare-definition` runs a
record without and with candidate definitions and says whether they are
material: an answer's choice flips or its confidence crosses the decision
threshold. `doctor` checks every tree and definitions file in the repository
and calls nothing: errors for invalid files, warnings for an unattached
definition, a record the index lacks, or a missing location or source.

## Modes

What is judged:

- **Compliance:** does a location meet a record? The record kind is chosen
  with exactly one of `--req`, `--adr` or `--nfr`, each with its own question
  set (REQ-JEV-0201).
- **Record quality:** is a single REQ, NFR or ADR well written? Runs only on
  a record Raptor imported without diagnostics (REQ-JEV-0101).

Target modes, for compliance (REQ-JEV-0203):

- `prompt`: an agent prompt or other prompt text.
- `skill`: a skill file.
- `task`: a task template, judged both raw and as a rendered assignment.
- `code`: source code, located through the tree-sitter grammars sc-agent
  defines (judge-jev never defines its own). Deferred until those grammars
  exist (ADR-JEV-0004).

## Scope

In scope:

- The four steps above, for REQ, NFR and ADR records.
- Judging whether a single record is well written (REQ-JEV-0101).
- A marketplace plugin and installer for Claude, Codex and Cursor
  (REQ-JEV-0005).

Out of scope:

- Parsing records or querying the record store. Raptor owns both
  (ADR-JEV-0002).
- Structure checks that Raptor's import already makes (ADR-JEV-0003).
- Changes to the Jev core other than defect fixes or the logger move
  (ADR-JEV-0001, REQ-JEV-0008).

## Install

The marketplace plugin `sc-judge-jev` exposes one skill, `judge-jev-installer`, which installs the `judge-jev` skill into a folder you choose (a repository, or a parent folder of repositories; never a global location).

Claude Code:

```text
/plugin marketplace add randlee/judge-jev
/plugin install sc-judge-jev@judge-jev
```

Codex: `codex plugin marketplace add randlee/judge-jev`, then open `/plugins` and install **Judge Jev**. Cursor: in Customize, import this GitHub repository (it reads `.cursor-plugin/marketplace.json`), then install **sc-judge-jev**.

Then ask the agent to install judge-jev, or run the `judge-jev-installer` skill. It reports the installed and available versions, asks once whether record text may be sent to TypeSafe, and runs:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/install.py" --dest <folder> --allow-remote-judge|--no-remote-judge [--target claude,codex,cursor]
```

From a checkout of this repository the same command is `uv run plugins/sc-judge-jev/install.py ...`; `--status --dest <folder>` reports the versions without writing. Rerun it to upgrade. Details: the installed `references/installation-and-troubleshooting.md`.

| Need | For | Notes |
| --- | --- | --- |
| `uv` | the installer and every `jev_judge.py` run | `uv run --script` supplies the Python dependencies (pydantic, sc-observability, PyYAML, pyoxigraph, pyshacl) |
| Python 3.11+ | everything | |
| Raptor (`integration/judge-jev`) and a Rust toolchain | building the record index | `git clone -b integration/judge-jev https://github.com/randlee/raptor`, then `uv venv .venv -p 3.11 && uv pip install -p .venv/bin/python . markdown` in the clone; see its `templates/README.md` |
| `TYPESAFE_API_KEY` | live Jev calls | Get a key at typesafe.ai; export it in the shell that launches the harness |
| `allow_remote_judge: true` in `.sc/judge-jev/settings.yaml` | live Jev calls | The user's one-time answer, set by the installer; commit the file |

`--dry-run`, `validate` and `doctor` need neither the key nor the setting.

## Requirements

Records: `docs/requirements/` (raptor-integration, record-validation,
prose-evaluation) and `docs/adr/adr-jev-product.md`. Raptor configuration is
in `.raptor/`.

The wheel migration retains the [product ADR boundaries](docs/adr/adr-jev-product.md):
ADR-JEV-0008 governs definition targeting, `doctor` and request/log size checks.
ADR-JEV-0002 keeps record access with Raptor; ADR-JEV-0003 keeps Raptor's schema
strict and separate from quality judgments; ADR-JEV-0004 retains the existing
code-reference scope limit. Transport replacement adds no record parser,
schema relaxation or code-reference support. These references do not change
any record's approval status.

## Open questions

See the Open list in [docs/cli.md](docs/cli.md).
