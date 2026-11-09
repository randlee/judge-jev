# Contributing

## What a good change looks like

- **Script and docs together.** A new flag, field, verdict, error code or exit code lands with its reference text and a test. Existing names are never renamed or removed in a patch; add only.
- **Prompts and scripts are templates.** Every installed prompt (the skill, its references and assets templates, the agent bodies) and every script has its source in `plugins/sc-judge-jev/install/templates/` as a `<file>.md.j2` or `<script>.py.j2` (sc-compose, rendered with `version`) and is installed only by `install.py`. Agent frontmatter and registries live in `install/harness/<target>/`. The plugin itself exposes only `skills/judge-jev-installer/`. After a release, run `python3 scripts/gen_install_data.py` to refresh `install/legacy-owned.json` (the byte list of earlier releases).
- **Tests green.** `uv run --no-project --python 3.11 --with sc-observability==1.5.0 --with pyyaml --with 'jsonschema>=4,<5' --with 'sc-compose>=1.7.0,<2' --with 'pydantic>=2.7,<3' --with 'pyoxigraph>=0.5,<0.6' --with 'pyshacl>=0.30,<1' python -m unittest discover -s tests/sc-judge-jev` (or `python3 -m unittest ...` in an interpreter that has those packages) and `python3 scripts/check_version_sync.py` both pass before you open the PR.
- **Never a secret.** No keys, no live run output containing private plan text. Fixture answers and dry runs are how tests touch Jev.

## Versioning

`VERSION` at the repo root is the single source of truth. Every version declared in shipped metadata equals it exactly: the plugin manifests, the marketplace manifests that carry a version, `SKILL.md`, each `references/*.md`, each harness agent, and each `registry.yaml` entry. Nothing has its own patch line.

`judge-jev` is unpublished, so `VERSION` is `0.0.0` until the first publish: no PR bumps it. Describe each change under `## Unreleased` in `CHANGELOG.md`.

`scripts/check_version_sync.py` enforces this: by default it checks that every declaration it finds by glob equals `VERSION` and that the changelog has a `## Unreleased` section or a `## <VERSION>` entry. `tests/sc-judge-jev/test_version_ssot.py` runs the same discovery in the suite. Template `metadata.version` and `schema_version` values are wire-contract versions pinned by the JSON schemas, not release versions.

## Proposing a change as an agent

1. Read `SKILL.md`, then only the reference you intend to change.
2. Make the change, and add a bullet under `## Unreleased` in the changelog. Do not change `VERSION`.
3. Run the tests and the version check.
4. Open the PR with: what changed, which aspect, the evidence (test names).

## What not to propose

- A rename of a flag, field, verdict or error code. Deprecate by adding the new name and keeping the old.
