# `judge-jev check --profile`: fan-out and aggregation

> **Planned, not in this release.** `check` (compliance: does code or a prompt meet its record) has no subcommand in `jev_judge.py`; this diagram is its design.

```mermaid
flowchart LR
    PF["--profile &lt;profile.toml&gt;<br/>[--questions &lt;file&gt;]"] --> E["[[location]]:<br/>loc, mode, records, vars"]
    E --> PAIRS["(record, location, mode) pairs<br/>listed pairs only"]
    PAIRS --> C["Compose each pair as in check.md"]
    C --> DR{"--dry-run?"}
    DR -- yes --> AU["One audit entry per request"]
    DR -- no --> S["Stream of single requests"] --> J[Jev]
    J --> L["Log each request, answers, verdict<br/>(sc-observability)"]
    L --> PV["Verdict per pair;<br/>names override if used"]
    PV --> A[Aggregate]
    A --> BR["Per record:<br/>met everywhere, or failing locations"]
    A --> BL["Per location:<br/>records met / failed"]
```

No extra prompt is composed here: each pair is composed exactly as in
[check.md](check.md). The report holds every pair's verdict plus both
aggregates.
