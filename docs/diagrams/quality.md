# `judge-jev quality`: Jev prompt composition

```mermaid
flowchart LR
    ID["(--req | --adr | --nfr &lt;id&gt;)...<br/>one run name"] --> R[Raptor: fetch each record]
    R --> D{Imported without<br/>diagnostics?}
    D -- no --> X[Typed error: fix import first]
    D -- yes --> T[Record text]
    ID --> K[Record kind]
    K --> TR["Quality decision tree for that kind<br/>or --questions override"]
    T --> P{"per: statement?"}
    TR --> P
    P -- no --> W["Wave request<br/>record + this wave's questions"]
    P -- yes --> WS["One request per MUST / MUST NOT statement<br/>statement + record + this wave's questions"]
    WS --> DR
    W --> DR{"--dry-run?"}
    DR -- yes --> AU["Audit: record id, Raptor source,<br/>tree (shipped id or override path),<br/>wave-1 request(s), size vs limit"]
    DR -- no --> J[Jev] --> A["Wave reason: every question's<br/>id, text, choice, criterion, confidence<br/>(per statement: index + text)"]
    A --> L["Log wave: request, answers, reason,<br/>branch or verdict (sc-observability)"]
    L --> N{Next wave?}
    N -- "yes: answers select it; it refines them" --> P
    N -- "no: verdict_rules" --> V["Verdict, path and every wave's reason;<br/>statements that fired the rule;<br/>names override if used"]
```

Each wave is one request carrying several questions about the same record,
and reports every question's answer as its reason. A per-statement wave
sends one such request per MUST / MUST NOT statement and reports each
statement's answers; its rules fire when any one statement matches. Answers pick the next
wave from the tree, and a wave with no next wave gives the verdict by the
tree's rule; no model chooses questions. The shipped trees hold wave 1
only: a wave 2 is designed from wave 1's observed answers. A dry run
composes wave 1 only, since later waves depend on live answers.
