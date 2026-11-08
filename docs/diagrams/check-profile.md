# `judge-jev check --profile`: fan-out and aggregation

```mermaid
flowchart LR
    PF["--profile &lt;profile.toml&gt;"] --> E["[[location]]:<br/>loc, mode, records, vars"]
    E --> PAIRS["(record, location, mode) pairs"]
    PAIRS --> S["Stream of single requests<br/>each composed as in check.md"]
    S --> DR{"--dry-run?"}
    DR -- yes --> AU["One audit entry per request"]
    DR -- no --> A[Aggregate verdicts]
    A --> BR["Per record:<br/>met everywhere, or failing locations"]
    A --> BL["Per location:<br/>records met / failed"]
```

No extra prompt is composed here: each pair is composed exactly as in
[check.md](check.md). Unlisted pairs are not judged.
