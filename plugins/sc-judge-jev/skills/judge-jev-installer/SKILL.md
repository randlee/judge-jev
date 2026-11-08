---
name: judge-jev-installer
description: Install or upgrade judge-jev (the judge-jev skill) into a repository or a parent folder of repositories. Use when the user asks to install, set up, upgrade or reinstall judge-jev, or when the session-start notice says a newer judge-jev is available. Never installs globally.
metadata:
  version: "0.2.0"
---

# judge-jev installer

This plugin ships only this skill. It installs judge-jev into a folder the
user names by running `install.py`, which sits in this plugin's directory
(`${CLAUDE_PLUGIN_ROOT}`; in any harness, two levels above this file).

The installer reads its templates, harness frontmatter and verbatim assets from
the plugin directory. From the folder, it reads `.sc/judge-jev/settings.yaml`
and whether `.git` exists (to find the
repository root; it never runs git). In the folder only, it reads the install
lock `.sc/judge-jev/install-lock.json` (only `--status` also reports the
nearest lock above) and the files already at the install paths, under
`.<target>/skills/judge-jev/`. It reads the home directory only to
refuse global folders and to stop its upward walks. It renders every Markdown
file and script (sc-compose runs in-process), and copies the verbatim assets.
It writes `.<target>/skills/judge-jev/` and `.<target>/agents/`, the lock,
the settings file and, with
`--overwrite`, `.backup/<UTC>/` and `.backup/.gitignore`; it removes unchanged files
this version no longer ships. It runs no external command.

## 1. Pick the folder and report versions

Ask which folder to install into when the user has not said: the current
repository, or a parent folder holding several repositories. Never the home
directory, `~/.claude`, `~/.codex`, `~/.cursor`, `~/.agents` or a plugin cache;
the installer refuses those with `INSTALL.DEST_GLOBAL`.

Before anything else, compare versions (read-only):

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/install.py" --dest <folder> --status
```

Report `data.message` to the user, for example "installed 0.1.0, installer
0.2.0" or "not installed in <folder>, installer 0.2.0". `data.state` is
`not_installed`, `older`, `current` or `newer` (exit 0 for each). When it is
`newer`, stop and tell the user this installer is older than what the folder
has; do not install.

## 2. Settings: ask once, only when missing

Read `<folder>/.sc/judge-jev/settings.yaml` if it exists.

- `allow_remote_judge`: when the folder's own file sets it, keep it (pass
  neither flag); the installer never copies a parent folder's answer.
  Otherwise ask the user once whether plan text may be sent to TypeSafe (Jev)
  for judging, and pass `--allow-remote-judge` or `--no-remote-judge` with the
  answer. Never infer consent from earlier runs, run files, committed evidence
  or other folders.

## 3. Install, or upgrade by rerunning

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/install.py" --dest <folder> \
  --allow-remote-judge|--no-remote-judge [--target claude,codex,cursor] [--dry-run]
```

An upgrade is the same command rerun for that folder; each install folder is
upgraded on its own. Without `--target` the installer covers every harness
the folder uses: the locked targets, every `.<target>/skills/judge-jev/`
and every `.claude/`, `.codex/` or `.cursor/` directory present (`claude` when
there is none); `--target` only adds a harness. `data.target_reasons` says why
each target was chosen, and `--status` lists `missing_targets` (harness
directories with no install).

Output is the JSON envelope `{success, data, error}`: exit 0 when it ran
(negative results are in `data`), exit 2 with a typed `error.code` otherwise
(`INSTALL.DEST_GLOBAL` for a global folder), exit 130 when interrupted
(`CANCELED`). On `INSTALL.CONFLICT`, show
`data.problems` and ask before rerunning with `--overwrite` (it moves each
listed file to `<folder>/.backup/`). Relay `data.notes` and tell the user to
commit `data.commit_paths`.

For the full guide, the installed copy's
`.claude/skills/judge-jev/references/installation-and-troubleshooting.md`
(or `.codex/`, `.cursor/`) covers parent-folder installs, per-repository
overrides and troubleshooting.
