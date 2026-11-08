# Contributing

## What a good change looks like

- **Script and docs together.** A new flag, field, verdict, error code or exit code lands with its reference text and a test. Existing names are never renamed or removed in a patch; add only.
- **Prompts and scripts are templates.** Every installed prompt (the skill, its references and assets templates, the agent bodies) and every script has its source in `plugins/sc-judge-jev/install/templates/` as a `<file>.md.j2` or `<script>.py.j2` (sc-compose, rendered with `version`) and is installed only by `install.py`. Agent frontmatter and registries live in `install/harness/<target>/`. The plugin itself exposes only `skills/judge-jev-installer/`. After a release, run `python3 scripts/gen_install_data.py` to refresh `install/legacy-owned.json` (the byte list of earlier releases).
- **Tests green.** `uv run --no-project --python 3.11 --with sc-observability==1.5.0 --with pyyaml --with 'jsonschema>=4,<5' --with 'sc-compose>=1.7.0,<2' python -m unittest discover -s tests/sc-judge-jev` (or `python3 -m unittest ...` in an interpreter that has those packages) and `python3 scripts/check_version_sync.py --base origin/main` both pass before you open the PR.
- **Never a secret.** No keys, no live run output containing private plan text. Fixture answers and dry runs are how tests touch Jev.

## Versioning

`VERSION` at the repo root is the single source of truth. Every version declared in shipped metadata equals it exactly: the plugin manifests, the marketplace manifests that carry a version, `SKILL.md`, each `references/*.md`, each harness agent, and each `registry.yaml` entry. Nothing has its own patch line.

A PR that changes shipped content (anything under `plugins/` or a marketplace manifest) raises `VERSION` (patch for a fix or addition, minor for a release-worthy change), sets every version above to it, and adds a `## X.Y.Z — date` section to `CHANGELOG.md`. A PR that touches only tests, `scripts/` or `docs/` needs no bump.

`scripts/check_version_sync.py` enforces this: by default it checks that every declaration it finds by glob equals `VERSION` and that the changelog has the entry; with `--base <ref>` (CI runs it on every pull request against `origin/main`, so a stacked PR is judged against what lands) it also checks that a PR changing shipped content raised `VERSION` and changed `CHANGELOG.md`. `tests/sc-judge-jev/test_version_ssot.py` runs the same discovery in the suite. Template `metadata.version` and `schema_version` values are wire-contract versions pinned by the JSON schemas, not release versions.

## Proposing a change as an agent

1. Read `SKILL.md`, then only the reference you intend to change.
2. Make the change; if it touches shipped content, raise `VERSION`, set every version to it, and add the changelog section.
3. Run the tests and the version check with `--base`.
4. Open the PR with: what changed, which aspect, the evidence (test names), and the before and after `VERSION`.

## What not to propose

- A rename of a flag, field, verdict or error code. Deprecate by adding the new name and keeping the old.
