# REQ-JEV-0002

Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.

| text | failing statements per run | failing runs | mean margin |
|---|---|---|---|
| orig | [7, 8, 8, 8, 7, 7] | 6/6 | 0.727 |
| greedy | [0, 0, 0, 0, 0, 0] | 0/6 | 0.779 |
| final | [0, 0, 0, 0, 0, 0] | 0/6 | 0.779 |

Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): greedy fails [0, 0, 0] margin 0.782; final fails [0, 0, 0] margin 0.781.

Selection: fixes-only (paired runs: fixes-only 0 failing runs, margin 0.7801; pruned 0 failing runs, margin 0.7591).

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
@@ -3,6 +3,24 @@
 **Status:** Draft  
 
 ### Requirement Statement
+
+Definitions: Jev is TypeSafe's hosted judge model: it answers each
+multiple-choice question about a text with one choice and a confidence from
+0 to 1. A Jev request is one call to it. The batch command is `jev_judge.py
+batch`: it reads request lines (one JSON request per line), sends each to
+Jev and writes a result line. A result envelope is the JSON result line for
+one request, holding its answers or its error
+(`assets/schemas/jev-batch-result.schema.json`). A typed error code is a
+stable dotted code naming a failure, such as `JEV.NETWORK` or
+`JEV.RATE_LIMITED`. The fixed retry policy is one retry of a call that
+failed with a recoverable or transient error (`JEV.RATE_LIMITED`,
+`JEV.OVERLOADED`, `JEV.NETWORK`, `JEV.RESPONSE_INVALID`), after the
+response's Retry-After delay capped at 30 seconds, or after 1 second without
+one. The request size limit is the `--max-request-bytes` value, at most
+64000 bytes; by default 24000 bytes with `--gate plan` and 64000 bytes with
+`--gate dev`. The sc-observability logger is the JSON-lines logger of the
+sc-observability package (version 1.5.0), which writes
+`.sc/judge-jev/logs/judge-jev.log.jsonl`.
 
 **MUST statements:**
 

```

## Diff: greedy (previous commit) -> final

```diff
(no change)
```

## Original text

````markdown
## REQ-JEV-0002: One batch command calls Jev

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- judge-jev MUST send every Jev request through one batch command.
- The batch command MUST read request lines.
- The batch command MUST write one result envelope per request.
- The batch command MUST use typed error codes.
- The batch command MUST apply a fixed retry policy.
- The batch command MUST enforce request size limits.
- The batch command MUST log every request through the sc-observability
  logger (REQ-JEV-0008).
- The batch command MUST log every answer through the sc-observability
  logger (REQ-JEV-0008).

### Rationale

One call path keeps the Jev core stable while a Rust implementation
replaces it (ADR-JEV-0001).

### Success Criteria

**Acceptance Criteria:**

- [ ] A request file of three lines produces three result envelopes and
  three log entries.
````

## Final text

````markdown
## REQ-JEV-0002: One batch command calls Jev

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. The batch command is `jev_judge.py
batch`: it reads request lines (one JSON request per line), sends each to
Jev and writes a result line. A result envelope is the JSON result line for
one request, holding its answers or its error
(`assets/schemas/jev-batch-result.schema.json`). A typed error code is a
stable dotted code naming a failure, such as `JEV.NETWORK` or
`JEV.RATE_LIMITED`. The fixed retry policy is one retry of a call that
failed with a recoverable or transient error (`JEV.RATE_LIMITED`,
`JEV.OVERLOADED`, `JEV.NETWORK`, `JEV.RESPONSE_INVALID`), after the
response's Retry-After delay capped at 30 seconds, or after 1 second without
one. The request size limit is the `--max-request-bytes` value, at most
64000 bytes; by default 24000 bytes with `--gate plan` and 64000 bytes with
`--gate dev`. The sc-observability logger is the JSON-lines logger of the
sc-observability package (version 1.5.0), which writes
`.sc/judge-jev/logs/judge-jev.log.jsonl`.

**MUST statements:**

- judge-jev MUST send every Jev request through one batch command.
- The batch command MUST read request lines.
- The batch command MUST write one result envelope per request.
- The batch command MUST use typed error codes.
- The batch command MUST apply a fixed retry policy.
- The batch command MUST enforce request size limits.
- The batch command MUST log every request through the sc-observability
  logger (REQ-JEV-0008).
- The batch command MUST log every answer through the sc-observability
  logger (REQ-JEV-0008).

### Rationale

One call path keeps the Jev core stable while a Rust implementation
replaces it (ADR-JEV-0001).

### Success Criteria

**Acceptance Criteria:**

- [ ] A request file of three lines produces three result envelopes and
  three log entries.
````
