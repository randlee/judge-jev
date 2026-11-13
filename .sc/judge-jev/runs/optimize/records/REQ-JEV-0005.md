# REQ-JEV-0005

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [3, 3, 3, 3, 3, 3] | 6/6 | 0.680 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.739 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.726 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.743; final fails [0, 0, 0] margin 0.737.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.7428; pruned 0 failing runs, margin 0.6495).

## Kept tweaks (text present in the final record) and measured effect

None: the final text equals the greedy text.

## Definitions pruned (greedy -> final)

None.

## Definitions added or reworded (greedy -> final)

None.

## Diff: original (origin/docs/record-fixes) -> final

```diff
--- original
+++ final
@@ -3,6 +3,13 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: A harness is an agent tool judge-jev installs into: Claude
+(Claude Code), Codex or Cursor. A marketplace plugin is a plugin a harness
+installs from a plugin marketplace. A harness is locked when the install
+lock records it, installed when its `.<harness>/skills/judge-jev/` directory
+exists, and present when its `.<harness>/` directory exists in the
+repository. An upgrade is an install of a newer judge-jev version.
 
 **MUST statements:**
 

```

## Diff: greedy (previous commit) -> final

```diff
(no change)
```

## Original text

````markdown
## REQ-JEV-0005: Marketplace and installer

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST ship as a marketplace plugin for Claude.
- judge-jev MUST ship as a marketplace plugin for Codex.
- judge-jev MUST ship as a marketplace plugin for Cursor.
- An upgrade MUST update every harness that is locked, installed or present.

### Rationale

No harness is left on an old version.

### Success Criteria

**Acceptance Criteria:**

- [ ] Upgrading in a repository with Claude, Codex and Cursor installs
  updates all three.
````

## Final text

````markdown
## REQ-JEV-0005: Marketplace and installer

**Status:** Draft  

### Requirement Statement

Definitions: A harness is an agent tool judge-jev installs into: Claude
(Claude Code), Codex or Cursor. A marketplace plugin is a plugin a harness
installs from a plugin marketplace. A harness is locked when the install
lock records it, installed when its `.<harness>/skills/judge-jev/` directory
exists, and present when its `.<harness>/` directory exists in the
repository. An upgrade is an install of a newer judge-jev version.

**MUST statements:**

- judge-jev MUST ship as a marketplace plugin for Claude.
- judge-jev MUST ship as a marketplace plugin for Codex.
- judge-jev MUST ship as a marketplace plugin for Cursor.
- An upgrade MUST update every harness that is locked, installed or present.

### Rationale

No harness is left on an old version.

### Success Criteria

**Acceptance Criteria:**

- [ ] Upgrading in a repository with Claude, Codex and Cursor installs
  updates all three.
````
