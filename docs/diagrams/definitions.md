# Definitions: from file to request

```mermaid
flowchart LR
    F[".sc/judge-jev/*.definitions.ttl<br/>or --definitions &lt;file&gt;"] --> LD{"Loads?<br/>UTF-8 Turtle"}
    LD -- no --> E1[Typed error: INPUT.MALFORMED<br/>or DEFINITIONS.INVALID]
    LD -- yes --> SH{"Closed shapes + body model<br/>one IRI per definition across files"}
    SH -- no --> E1
    SH -- yes --> G["Own named graph<br/>(a tree's digest is unchanged)"]
    G --> M{"Attached to this record<br/>(and this location)?"}
    R[Record + location of the request] --> M
    M -- none --> Q["Request exactly as without definitions"]
    M -- some --> S["state.definitions = [{term, text}] sorted by term<br/>never truncated"]
    S --> J[Jev]
    Q --> J
    J --> L["Log request, answer, result, wave, verdict<br/>each with definitions: iri, term, digest"]
    L --> T["Run triples: run jj:carriedDefinition definition"]
```

A record-only attachment puts the definition in every request about the
record; a record-and-location attachment puts it only in a request made at
that location. Shipped question wording is never changed.
