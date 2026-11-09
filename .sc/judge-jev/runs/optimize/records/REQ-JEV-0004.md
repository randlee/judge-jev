# REQ-JEV-0004

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [1, 1, 1, 1, 1, 2] | 6/6 | 0.674 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.738 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.723 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.736; final fails [0, 0, 0] margin 0.742.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.7392; pruned 0 failing runs, margin 0.6558).

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
+Definitions: Jev is TypeSafe's hosted judge model: it answers each
+multiple-choice question about a text with one choice and a confidence from
+0 to 1. A Jev request is one call to it. A live Jev call is a request sent
+to Jev, as opposed to a dry run or an answers file.
+`POLICY.REMOTE_JUDGE_DISABLED` is the typed error code for a refused live
+call.
 
 **MUST statements:**
 

```

## Diff: greedy (previous commit) -> final

```diff
(no change)
```

## Original text

````markdown
## REQ-JEV-0004: Remote-judge consent

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST refuse every live Jev call with
  `POLICY.REMOTE_JUDGE_DISABLED` unless the committed
  `.sc/judge-jev/settings.yaml` sets `allow_remote_judge: true`.

**MUST NOT statements:**

- judge-jev MUST NOT write that setting without the user's answer.

### Rationale

Text sent to Jev leaves the machine; the user decides once per repository.

### Success Criteria

**Acceptance Criteria:**

- [ ] With the setting absent or false, a live call exits with
  `POLICY.REMOTE_JUDGE_DISABLED` and sends nothing.
````

## Final text

````markdown
## REQ-JEV-0004: Remote-judge consent

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. A live Jev call is a request sent
to Jev, as opposed to a dry run or an answers file.
`POLICY.REMOTE_JUDGE_DISABLED` is the typed error code for a refused live
call.

**MUST statements:**

- judge-jev MUST refuse every live Jev call with
  `POLICY.REMOTE_JUDGE_DISABLED` unless the committed
  `.sc/judge-jev/settings.yaml` sets `allow_remote_judge: true`.

**MUST NOT statements:**

- judge-jev MUST NOT write that setting without the user's answer.

### Rationale

Text sent to Jev leaves the machine; the user decides once per repository.

### Success Criteria

**Acceptance Criteria:**

- [ ] With the setting absent or false, a live call exits with
  `POLICY.REMOTE_JUDGE_DISABLED` and sends nothing.
````
