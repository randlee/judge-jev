# Fix workflow (`references/fix-strategy.md`)

Reader: an agent or person fixing one record that fails the gate; the owner
reviewing what such an agent did. This is the workflow as shipped (unchanged in 0.8.1).

```mermaid
flowchart TD
    S["Set up once: .sc/judge-jev/fix/&lt;ID&gt;/<br/>original.md, env, state.jsonl"] --> V["verify base: three quality runs on identical text,<br/>jev_gate.py (gate.md)"]
    V --> P{"pass?"}
    P -- yes --> ACC
    P -- no --> DG["diagnose: one run with diag-&lt;kind&gt;.json;<br/>read the d_* answers (Jev says why)"]
    DG --> WR{"A statement with obligations 2+ joined by<br/>and-list / alternatives / obligation+rationale,<br/>or three or more weak statements?"}
    WR -- yes --> WRITE["Write the record from its tenets (write.md)"]
    WR -- no --> ST["Pick strategies: table rows whose trigger matches<br/>the weak gate answer and its d_* answers (3 at most);<br/>term answers first"]
    ST --> PR["One jev-fix-proposer per statement and strategy,<br/>in parallel, no shared context → one candidate each"]
    PR --> GU{"old text occurs once,<br/>and the guard keeps every number,<br/>record id, code span, MUST, MUST NOT?"}
    GU -- no --> RJ["Rejected"]
    GU -- yes --> MS["Apply, verify c&lt;n&gt;, restore base"]
    MS --> KP{"Own weak answer rose,<br/>no other answer fell > 0.05<br/>or newly below T?"}
    KP -- no --> RJ
    KP -- yes --> KEPT["Kept"]
    KEPT --> AP["Apply the kept candidates together, verify comb;<br/>drop the smallest-gain one while comb loses a gain;<br/>restore base if the gains do not hold"]
    AP --> V
    RJ --> RN{"Any candidate kept<br/>this round?"}
    RN -- "yes: others kept" --> KEPT
    RN -- no --> RD{"Two rounds in a row<br/>kept no candidate?"}
    RD -- no --> V
    RD -- yes --> UNR["Unresolved: keep best text;<br/>to write.md once"]
    ACC["Accept: guard and diff against original (rule 1: obligations unchanged);<br/>append id, sha256, runs, lowest to .sc/judge-jev/accepted.jsonl (frozen)"]
```

Rules: obligations do not change; nothing is invented; no checked-by clause;
the gate is not edited; no record or statement is removed to make a record
pass.
