# `jev_gate.py`: when a record passes

Reader: anyone deciding whether a judged record is accepted, or reading why it was not.

```mermaid
flowchart LR
    R["Result files of quality runs<br/>on identical text (3 by convention)"] --> A["Per record: verdict of each run;<br/>per gate answer (statement, question): choice and confidence in each run"]
    A --> D{"Question id<br/>starts with d_?"}
    D -- yes --> SK["Skipped: diagnostic, never gates"]
    D -- no --> AS{"Asked in more than<br/>half of the runs?"}
    AS -- no --> NG["Listed with gating: false<br/>(e.g. joined_by asked in 1 of 3 runs)"]
    AS -- yes --> M["Median confidence over the runs that asked it;<br/>runner-up choice and its median"]
    M --> T{"Median ≥ threshold<br/>(--threshold, default 0.6)?"}
    A --> V{"Verdict yes in more<br/>than half of the runs?"}
    A --> C{"Comparable? every run has the record,<br/>same statement text"}
    C -- yes --> AND
    T -- "every gating answer: yes" --> AND{"comparable AND verdicts AND medians?"}
    V -- yes --> AND
    AND -- "all three" --> P["pass: true"]
    C -- no --> F["pass: false"]
    T -- "any: no" --> F
    V -- no --> F
    M --> LO["lowest = the gating answer with the lowest median<br/>(reported for passing and failing records)"]
```

With three runs, "more than half" is two. `jev_gate.py` exits 0 whenever it
computed the gate, failing records included; a record whose runs judged
different text is not comparable and does not pass. The fix and write
workflows ([fix.md](fix.md), [write.md](write.md)) call this gate as their
`verify` step.
