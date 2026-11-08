# `judge-jev quality`: Jev prompt composition

```mermaid
flowchart LR
    ID["--req | --adr | --nfr &lt;id&gt;"] --> R[Raptor: fetch record]
    R --> D{Imported without<br/>diagnostics?}
    D -- no --> X[Typed error: fix import first]
    D -- yes --> T[Record text]
    ID --> K[Record kind]
    K --> TR["Quality decision tree for that kind<br/>or --questions override"]
    T --> W1["Wave 1 request<br/>record + wave-1 questions"]
    TR --> W1
    W1 --> DR{"--dry-run?"}
    DR -- yes --> AU["Audit: tree + composed wave-1 request"]
    DR -- no --> J1[Jev] --> A1[Wave-1 answers]
    A1 --> SEL["Tree selects wave-2 questions"]
    SEL --> W2["Wave 2 request<br/>record + wave-2 questions"] --> J2[Jev] --> A2[Wave-2 answers]
    A2 --> N{Leaf?}
    N -- no --> SEL2["Next wave …"]
    N -- yes --> V["Verdict<br/>fail: tree path"]
```

Each wave is one request carrying several questions about the same record.
Answers pick the next wave from the shipped tree; no model chooses questions.
