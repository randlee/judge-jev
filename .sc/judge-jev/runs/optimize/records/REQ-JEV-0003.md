# REQ-JEV-0003

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [1, 1, 1, 1, 1, 1] | 6/6 | 0.567 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.641 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.649 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.647; final fails [0, 0, 0] margin 0.642.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.6441; pruned 0 failing runs, margin 0.5544).

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
@@ -3,6 +3,11 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: TypeSafe is the company whose API (application programming
+interface) serves Jev, the judge model; the TypeSafe API key authenticates
+calls to it. The platform credential store is the macOS Keychain, the
+Windows Credential Manager or, on Linux, the Secret Service (`secret-tool`).
 
 **MUST statements:**
 

```

## Diff: greedy (previous commit) -> final

```diff
(no change)
```

## Original text

````markdown
## REQ-JEV-0003: TypeSafe key lookup

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST read the TypeSafe API key from `TYPESAFE_API_KEY` first,
  then from the platform credential store, service `plan-anchor`, account
  `typesafe-api-key`.

### Rationale

Tools that call Jev share one stored key, saved once.

### Success Criteria

**Acceptance Criteria:**

- [ ] A key stored under that service and account is found with no other
  setup.
````

## Final text

````markdown
## REQ-JEV-0003: TypeSafe key lookup

**Status:** Draft  

### Requirement Statement

Definitions: TypeSafe is the company whose API (application programming
interface) serves Jev, the judge model; the TypeSafe API key authenticates
calls to it. The platform credential store is the macOS Keychain, the
Windows Credential Manager or, on Linux, the Secret Service (`secret-tool`).

**MUST statements:**

- judge-jev MUST read the TypeSafe API key from `TYPESAFE_API_KEY` first,
  then from the platform credential store, service `plan-anchor`, account
  `typesafe-api-key`.

### Rationale

Tools that call Jev share one stored key, saved once.

### Success Criteria

**Acceptance Criteria:**

- [ ] A key stored under that service and account is found with no other
  setup.
````
