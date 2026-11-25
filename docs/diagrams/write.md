# Write workflow (`references/write-records.md`)

Reader: an agent or person rewriting a record whose problems are structural
(a joined statement, or many weak statements), or writing a new one.

```mermaid
flowchart TD
    IN["Record fails verify with a joined statement,<br/>3+ weak statements, two fix rounds kept nothing,<br/>or a new record"] --> SU["Set up: record.json (record text, PRD sources)"]
    SU --> T["Tenets writer (frontier model, knows the PRD):<br/>render record-tenets.md.j2 → tenets.json"]
    T --> C{"conflicts > 0?"}
    C -- yes --> OWN["Stop: list for the owner"]
    C -- no --> W["Render record-write.md.j2 without the old text;<br/>two or more record writers, 3 candidates each"]
    W --> CV{"Every tenet covered,<br/>one tenet per statement (REQ/NFR)?"}
    CV -- no --> RJ["Rejected"]
    CV -- yes --> AP["Replace the record's sections with the candidate;<br/>verify &lt;writer&gt;-c&lt;n&gt; (gate.md); restore"]
    AP --> PS{"Any candidate pass=true?"}
    PS -- no --> UNR["Unresolved: list it"]
    PS -- yes --> BEST["Keep the passing candidate with the highest lowest median"]
    BEST --> G{"Fix-strategy guard OK and the tenets<br/>writer says it requires every tenet<br/>and nothing else?"}
    G -- no --> NEXT["Take the next best"] --> G
    G -- yes --> ACC["Accept and freeze (accepted.jsonl), commit"]
```

The coordinator fills templates only from files, never rewords a tenet and
never picks a candidate by reading it. Writers never see Jev's scores.
