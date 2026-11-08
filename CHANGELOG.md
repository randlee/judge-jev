# Changelog

`VERSION` is the single source of truth: every version in shipped metadata (plugin and marketplace manifests, `SKILL.md`, each reference, each agent, each registry) equals it exactly. A PR that changes shipped content raises `VERSION`, moves every version with it, and adds a `## X.Y.Z — date` section here. `scripts/check_version_sync.py` and `tests/sc-judge-jev/test_version_ssot.py` enforce it (see CONTRIBUTING.md).

## 0.1.0 — 2026-11-07

- The judge-jev marketplace: `.claude-plugin/`, `.cursor-plugin/` and
  `.agents/plugins/` catalogs list one plugin, `sc-judge-jev`, which ships only
  the `judge-jev-installer` skill and a SessionStart hook.
- `install.py` installs the `judge-jev` skill into a repository or a parent
  folder (`.claude/`, `.codex/`, `.cursor/`), with the install lock
  `.sc/judge-jev/install-lock.json`, sha256 ownership, `--overwrite` backups,
  `--dry-run`, `--status`, `--allow-remote-judge` / `--no-remote-judge`, and
  `target_reasons` / `missing_targets`. Global destinations are refused with
  `INSTALL.DEST_GLOBAL`.
- `judge_jev_settings.py` reads and sets `.sc/judge-jev/settings.yaml`
  (`schema_version`, `allow_remote_judge`).
