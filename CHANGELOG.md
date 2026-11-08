# Changelog

`VERSION` is the single source of truth: every version in shipped metadata (plugin and marketplace manifests, `SKILL.md`, each reference, each agent, each registry) equals it exactly. A PR that changes shipped content raises `VERSION`, moves every version with it, and adds a `## X.Y.Z — date` section here. `scripts/check_version_sync.py` and `tests/sc-judge-jev/test_version_ssot.py` enforce it (see CONTRIBUTING.md).

## 0.3.0 — 2026-11-08

- `quality`: every wave reports its reason, each question's `id`, `text`,
  Jev's `choice` and `confidence`, in `data.results[].waves[].reason` and the
  `wave` log event (REQ-JEV-0101). A wave may end the walk with
  `verdict_rules` in the tree (`{any: {question: choice}, verdict}`, first
  match wins) instead of `next`; leaves still work. The leaf's fixed
  `reason` text is no longer reported.
- The shipped trees (`quality-req`, `quality-adr`, `quality-nfr`) hold wave 1
  only (wording unchanged, `approved: false`): `no` if any question answers
  `no`, else `unclear` if any answers `unclear`, else `yes`.
- `quality` takes repeated, mixed `--req/--adr/--nfr` ids and judges them all
  under one run name; output is `data.results`, one entry per record.
- The `quality` log is `.sc/judge-jev/logs/judge-jev.log.jsonl` (default
  `--run-dir` is now `.sc/judge-jev`; it was `.sc/judge-jev/logs`, which put
  the file under `logs/logs/`).

## 0.2.0 — 2026-11-08

- `jev_judge.py batch` logs through the sc-observability logger
  (`sc-observability==1.5.0`, REQ-JEV-0008) instead of its own
  `anchor-runs/tournament-<run>.jsonl`: each result line is a `request`,
  `answer` and `result` event in `<run-dir>/logs/judge-jev.log.jsonl`. Stdout is
  unchanged. The script carries PEP 723 metadata (`uv run --script`) and needs
  Python 3.11 or newer; a missing package is `DEPENDENCY.SC_OBSERVABILITY`, a refused
  event `LOG.WRITE`.
- `jev_judge.py quality --req|--adr|--nfr <id> --index <raptor index>
  [--questions <file>] [--dry-run]` (REQ-JEV-0101, REQ-JEV-0209): judges one
  record from a Raptor import index with its kind's decision tree,
  `assets/questions/quality-{req,adr,nfr}.json` (drafts, `approved: false`), one
  batch request per wave; answers pick the next wave, a leaf gives the verdict
  and the path. Records with import diagnostics are refused. Every result and
  log event carries the tree id and the file's sha256.
- `batch` accepts a request line without `anchor`: it sends only the item,
  needs no roles and gets a null verdict. Anchored lines are gated as before.

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
