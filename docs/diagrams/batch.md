# `judge-jev batch`: the low layer

Reader: anyone sending Jev requests that are not quality, drift or compare
(plan and dev gates), or debugging what those commands send.

```mermaid
flowchart LR
    IN["JSONL request lines<br/>(--input or stdin)<br/>jev-batch-request.schema.json"] --> V{"Each line valid?<br/>size within the gate's cap?"}
    V -- no --> E["Typed error<br/>(shorten the item; never raise the cap)"]
    V -- yes --> JOBS["Jobs: one per (item, candidate, repeat);<br/>roles from the candidate,<br/>else from --gate plan | dev question set"]
    ANC["--anchors anchors.json"] --> JOBS
    JOBS --> DR{"--dry-run?"}
    DR -- yes --> AU["Composed requests; nothing sent"]
    DR -- no --> FX{"--answers-file?"}
    FX -- yes --> FA["Fixture answers; no network"]
    FX -- no --> J["Jev (parallel workers)"]
    FA --> DEC
    J --> DEC["decide(): answers by role<br/>(relevance, compliance, conflict, evidence)<br/>→ verdict, min_confidence,<br/>leaning (verdict at threshold 0)"]
    DEC --> L["Log each result line<br/>(sc-observability)"]
    L --> OUT["One JSONL result line per job<br/>jev-batch-result.schema.json"]
```

`quality`, `drift` and `compare-definition` compose their own requests and
send them through the same job runner; `drift` reads its own verdict from the
answers (see [drift.md](drift.md)), not `decide()`.
