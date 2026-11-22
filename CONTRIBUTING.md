# Contributing

## What a good change looks like

- **Script and docs together.** A new flag, field, verdict, error code or exit code lands with its reference text and a test. Existing names are never renamed or removed in a patch; add only.
- **Prompts and scripts are templates.** Every installed prompt (the skill, its references and assets templates, the agent bodies) and every script has its source in `plugins/sc-judge-jev/install/templates/` as a `<file>.md.j2` or `<script>.py.j2` (sc-compose, rendered with `version`) and is installed only by `install.py`. Agent frontmatter and registries live in `install/harness/<target>/`. The plugin itself exposes only `skills/judge-jev-installer/`. After a release, run `python3 scripts/gen_install_data.py` to refresh `install/legacy-owned.json` (the byte list of earlier releases).
- **Tests green.** Run `python3 -m unittest discover -s tests/sc-judge-jev` in Python 3.11 or newer with the dependencies declared in `install.py` and `install/templates/skills/judge-jev/scripts/jev_judge.py.j2`, plus `jsonschema`. Install sc-decidr at the exact version pinned in `jev_judge.py.j2`; that pin also supplies the sitr API. Run `python3 scripts/check_version_sync.py` before opening a PR.
- **Never a secret.** No keys, no live run output containing private record text. Fixture answers and dry runs are how tests touch Jev.

For an unattended live integration run, use `scripts/integration.py` with a Python 3.11 venv containing the intended sc-decidr wheel and declared dependencies. The runner requires a temporary env file and results path and deletes the env file; use `--help` for the arguments. Keep live results out of the repository.

## Versioning

`VERSION` at the repo root is the single source of truth. Every version declared in shipped metadata equals it exactly: the plugin manifests, the marketplace manifests that carry a version, `SKILL.md`, each `references/*.md`, each harness agent, and each `registry.yaml` entry. Nothing has its own patch line.

Every PR to `main` raises `VERSION` by at least a patch (`0.2.0` to `0.2.1`); a PR that adds a command, flag, field or strategy raises the minor. The PR sets `VERSION`, every declaration and every template's own `version:` to the new number together, and adds its entry to `CHANGELOG.md` under `## <VERSION> — <date>`. Every integer version (question sets, trees, `schema_version`) stays `1`. (Before the first release the version was locked at `0.1.0`; that rule is retired.)

`scripts/check_version_sync.py` enforces this: by default it checks that every declaration it finds by glob equals `VERSION` and that the changelog has a `## Unreleased` section or a `## <VERSION>` entry. `tests/sc-judge-jev/test_version_ssot.py` runs the same discovery in the suite. Template `metadata.version` and `schema_version` values are wire-contract versions pinned by the JSON schemas, not release versions.

## Proposing a change as an agent

1. Read `SKILL.md`, then only the reference you intend to change.
2. Make the change, raise `VERSION` and every declaration by at least a patch, and add a `## <VERSION> — <date>` entry to the changelog.
3. Run the tests and the version check.
4. Open the PR with: what changed, which aspect, the evidence (test names).

## What not to propose

- A rename of a flag, field, verdict or error code. Deprecate by adding the new name and keeping the old.
