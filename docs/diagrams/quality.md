# `judge-jev quality`: Jev prompt composition

```mermaid
flowchart LR
    ID["--req | --adr | --nfr &lt;id&gt;"] --> R[Raptor: fetch record]
    R --> D{Imported without<br/>diagnostics?}
    D -- no --> X[Typed error: fix import first]
    D -- yes --> T[Record text]
    ID --> K[Record kind]
    K --> TR["Quality decision tree for that kind<br/>or --questions override"]
    T --> W["Wave request<br/>record + this wave's questions"]
    TR --> W
    W --> DR{"--dry-run?"}
    DR -- yes --> AU["Audit: record id, Raptor source,<br/>tree (shipped id or override path),<br/>wave-1 request, size vs limit"]
    DR -- no --> J[Jev] --> A[Wave answers]
    A --> L["Log wave: request, answers,<br/>selected branch (sc-observability)"]
    L --> N{Leaf?}
    N -- "no: tree selects next wave" --> W
    N -- yes --> V["Verdict; names override if used<br/>fail: tree path"]
```

Each wave is one request carrying several questions about the same record.
Answers pick the next wave from the shipped tree; no model chooses questions.
A dry run composes wave 1 only, since later waves depend on live answers.
