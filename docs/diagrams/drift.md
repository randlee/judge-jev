# `judge-jev drift`: does a rewrite still require what the original did?

Reader: anyone rewriting records (by hand, by the fix workflow or by the write
workflow) who must show that no obligation was added, dropped or changed.

```mermaid
flowchart LR
    IX["--old-index, --new-index<br/>(Raptor import indexes)"] --> SEL{"--req/--adr/--nfr ids<br/>or --changed?"}
    SEL -- "both or neither" --> E1["VALIDATION.INPUT"]
    SEL --> IDS["Records in both indexes;<br/>only in old: deleted; only in new: added"]
    IDS --> DG{"Import diagnostics<br/>in either index?"}
    DG -- yes --> E2["RECORD.DIAGNOSTICS"]
    DG -- no --> UN{"--changed and normative<br/>text identical?"}
    UN -- yes --> U["unchanged (not sent)"]
    UN -- no --> REQ["One request per record:<br/>original obligations + rewrite<br/>(--form diff | full),<br/>--question-set orthogonal | brief | sixteen"]
    REQ --> CTL["Controls for the first --controls records (default 3):<br/>original vs itself (expect no-drift);<br/>original with one obligation dropped (expect drift)"]
    CTL --> J["Jev (or --answers-file)"]
    REQ --> J
    J --> AS["Per record: drift_assess"]
    AS --> D1{"Any confident answer<br/>a drift choice?"}
    D1 -- yes --> DR["drift"]
    D1 -- no --> D2{"A feature group with no confident answer,<br/>over 20% of answers below --threshold,<br/>or only_reword (sixteen set) contradicts?"}
    D2 -- yes --> UC["uncertain"]
    D2 -- no --> ND["no-drift"]
    J --> CR{"Every control got its<br/>expected verdict? (drop control:<br/>the dropped obligation is the one found)"}
    CR -- no --> INV["valid: false (the run is not trusted)"]
    CR -- yes --> VAL["valid: true"]
```

List questions (a new measure, a new definition) never decide; a confident
yes is reported under `listed`. A contradiction with `only_reword` makes the
record uncertain even when a drift answer was confident.
