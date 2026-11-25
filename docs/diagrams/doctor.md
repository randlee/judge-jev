# `judge-jev doctor`: check everything judge-jev loads

Reader: anyone who changed a tree, a question set or a definitions file and
wants to know it loads before any Jev call.

```mermaid
flowchart LR
    S["Scope: shipped trees and question sets,<br/>.sc/judge-jev/ top level,<br/>and the PATH arguments (folders searched)"] --> F["Each file once"]
    F --> EXT{".json or .ttl?"}
    EXT -- no --> ERRV["error: VALIDATION.INPUT"]
    EXT -- yes --> EX{"Exists?"}
    EX -- no --> ERR["error: INPUT.MISSING"]
    EX -- yes --> K["By kind: tree (.json / .ttl), question set,<br/>definitions (.ttl): model and shapes"]
    K -. invalid .-> ERR2["error, naming file and rule"]
    K --> DUP{"One question IRI<br/>in several tree files?"}
    DUP -- yes --> ERR3["error: QUESTIONS.DUPLICATE_IRI"]
    K -. "same question id twice in one tree" .-> ERR4["error: QUESTIONS.DUPLICATE_ID"]
    K --> DS{"Definitions across files form one set?<br/>(one IRI per definition)"}
    DS -- no --> ERR5["error: DEFINITIONS.INVALID"]
    IX -. "index names no metadata.repository" .-> W2["warning: DEFINITION.REPOSITORY_UNKNOWN"]
    W2 --> R
    IX["--index (optional)"] --> AT{"Definition attachments name<br/>records the index holds?"}
    K --> AT
    AT -- no --> W["warning"]
    IX -. absent .-> N["note: DOCTOR.INDEX_SKIPPED"]
    DUP -- no --> R{"Any error?"}
    W --> R
    R -- yes --> FAIL["DOCTOR.FAILED, exit 2,<br/>report in data"]
    R -- no --> OK["ok: true, warnings and notes, exit 0"]
```

Calls nothing, needs no key, writes no log. A `path::Symbol` location is
checked for its file only.
