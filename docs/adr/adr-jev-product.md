# adr-jev-product - judge-jev Product Decisions

**ID Range:** ADR-JEV-0001 through ADR-JEV-0008  
**Version:** 0.1.0  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-08  
**Decision Date:** 2026-11-07  
**Owner:** Rand Lee  

## Context

judge-jev checks prompts, skills and task templates against requirement
records. These decisions fix where it gets records, how it calls Jev and
what the first version leaves out.

---

## ADR-JEV-0001: Keep the Jev core unchanged until its Rust replacement

**Status:** Draft  

### Context

judge-jev's Jev core (the batch command, request and result contracts,
key lookup and remote-judge consent) is copied from an existing
implementation, and a Rust implementation, exposed through PyO3 bindings or
a command-line interface (CLI), will replace that Python core. The problem
is whether the Python core may change before then: any change to its
architecture or contracts is a change the Rust replacement must reproduce,
or its callers break when the replacement lands.

### Decision

The Jev core keeps its architecture and contracts unchanged. It changes
only to fix a defect, or to replace its run log with the sc-observability
logger (REQ-JEV-0008).

### Rationale

An unchanged core lets the Rust implementation replace it with no change
to its callers.

### Consequences

**Positive:**

- The Rust replacement is a drop-in.

**Negative:**

- Improvements to the core wait for the Rust implementation.

### Alternatives Considered

#### Alternative 1: Improve the Python core before the Rust replacement

**Description:** Change the copied core's architecture or contracts now.

**Why Rejected:** The Rust implementation could then not replace the core
without a change to its callers.

## ADR-JEV-0002: Query records through Raptor over local SQLite

**Status:** Draft  

### Context

judge-jev needs requirement records to judge, and their source is
changing: requirements move from Markdown files to a Dolt server as the
single source of truth, with the Raptor command-line interface (CLI) as
the access path. Raptor owns the record schema and every conversion
(REQ-JEV-0001). The problem is how judge-jev reads records so that neither
the move to Dolt nor a Raptor schema change breaks it.

### Decision

judge-jev reads records only through Raptor, which queries a local SQLite
database: built on the fly from Markdown now, pulled from a Dolt branch
later.

### Rationale

Querying SQLite is the same work either way, so the source can change
without touching judge-jev.

### Consequences

**Positive:**

- The move to Dolt does not change judge-jev.

**Negative:**

- judge-jev depends on Raptor's query contract; Raptor notifies judge-jev
  maintenance before changing it.

### Alternatives Considered

#### Alternative 1: Parse record Markdown directly

**Description:** judge-jev reads the record Markdown files itself.

**Why Rejected:** Raptor owns the schema and every conversion; a parser in
judge-jev breaks when Raptor changes them (REQ-JEV-0001).

#### Alternative 2: Query the record store with SQL directly

**Description:** judge-jev runs its own SQL against the record store.

**Why Rejected:** Raptor owns the schema; judge-jev's own queries break when
Raptor changes it (REQ-JEV-0001).

## ADR-JEV-0003: Judge record quality instead of loosening the schema

**Status:** Proposed  

### Context

Raptor rejects records missing required sections, such as statements
written as plain prose, so corpora with prose-only records do not import.
judge-jev can judge only records with typed statements and criteria. The
problem is how such records get into a judgeable form: by loosening
Raptor's schema to accept them, or by keeping it strict and explaining
what to fix.

### Decision

Raptor's schema stays strict. Raptor's import diagnostics explain why a
record does not fit the schema; judge-jev's quality mode then explains why
an imported record is not well written.

### Rationale

An explained rejection gets the document fixed; a looser schema stores
records that cannot be judged.

### Consequences

**Positive:**

- Every record judge-jev uses has typed statements and criteria.

**Negative:**

- Corpora with prose-only records need editing before import, guided by
  the import diagnostics.

### Alternatives Considered

#### Alternative 1: Loosen Raptor's schema

**Description:** Accept records missing required sections, such as
prose-only statements.

**Why Rejected:** A looser schema stores records that cannot be judged.

## ADR-JEV-0004: Code references are outside the first version

**Status:** Draft  

### Context

Records will eventually govern code as well as prompts, but selecting code
needs tree-sitter grammars, which sc-agent defines and which may not be
complete yet. The problem is what the first version judges while those
grammars are unfinished.

### Decision

The first version judges prompts, skills and task templates only. Code
references come later through tree-sitter grammars that sc-agent defines;
judge-jev never defines its own grammars. sc-agent's grammars may not be
complete yet.

### Rationale

Prompt and task wording is the immediate risk; code selection needs the
tree-sitter work first.

### Consequences

**Positive:**

- The first version ships without a code-reference model.

**Negative:**

- Code is not judged until the tree-sitter extension exists.

### Alternatives Considered

#### Alternative 1: judge-jev defines its own tree-sitter grammars

**Description:** Ship grammars inside judge-jev so code is judged now.

**Why Rejected:** sc-agent owns the grammars so every consumer selects code
the same way (REQ-JEV-0203).

#### Alternative 2: Line-range locations for code

**Description:** Reference code by file line ranges instead of symbols.

**Why Rejected:** Line ranges drift on every edit; symbols survive
(REQ-JEV-0207).

---

## ADR-JEV-0005: Pydantic models validate every JSON input

**Status:** Draft  

### Context

judge-jev reads JSON written by people and agents (quality trees, question
sets, answers files, request streams), by Raptor (the import index) and by
Jev (responses). Quality trees will be varied thousands of times
(REQ-JEV-0205). Hand-written type checks let fourteen input shapes crash
the script or fail only after a paid Jev call, found by review of PRs #13
and #14. The problem is how to make every input either accepted, or refused
with the exact field, before the first call.

### Decision

Every JSON input is parsed into a pydantic v2 model in strict mode before
it is used, and code after parsing receives model instances, not
dictionaries. Each model is the single definition of its input's shape.
Rules that span fields (a rule's choices are options of its question, a
`goto` names a node, no cycle, a final rule without conditions) are model
validators. `judge-jev validate` (REQ-JEV-0210) runs the same models
without calling Jev. The JSON shapes of the Jev core's contracts do not
change (ADR-JEV-0001); only how they are checked does.

### Rationale

One model per input replaces scattered checks that each had to anticipate
every wrong type, and pydantic reports the field path of every refusal.

### Consequences

**Positive:**

- Every refusal names the field and the rule it breaks.
- Tree authors check a variation with `judge-jev validate` before a run.

**Negative:**

- pydantic (with its compiled core) becomes a dependency, pinned in the
  script's PEP 723 header and in CI.
- Refusal wording follows pydantic's messages.

### Alternatives Considered

#### Alternative 1: Keep hand-written checks

**Description:** Extend the `isinstance` checks for each new crash found.

**Why Rejected:** Each new shape needs a new check; review of #13 and #14
found fourteen that were missed.

#### Alternative 2: JSON Schema validated by `jsonschema`

**Description:** One schema file per input, validated at load.

**Why Rejected:** Rules that span fields stay hand-written, and code after
validation still handles untyped dictionaries.

---

## ADR-JEV-0006: Quality trees and their answers are an RDF graph

**Status:** Draft  

### Context

A quality tree is a graph: waves, questions, options and rules, with edges
between them. As JSON, a question shared by two trees or two waves is
copied, list position carries rule priority, and every structural check is
code judge-jev maintains. Answers live in log files apart from the questions
that produced them, so comparing thousands of question variations means
scraping logs. The problem is how to represent trees and answers so that
questions are shared, structure is checked by existing tools, and every
verdict can be traced through its answers to the exact question and option.

### Decision

Quality trees are written in Turtle (TTL) against a judge-jev ontology:
waves, questions, options and rules are resources linked by edges, and a
question is one resource with an IRI that any wave may use. Order is a
`rank` property: rules are tried by rank and the reason lists questions by
rank; questions within a wave are otherwise unordered. SHACL shapes over the
ontology validate the graph and its edges (each rule's choices are options
of its question, each `goto` names a node, no cycle, a final rule without
conditions). Pydantic models (ADR-JEV-0005) validate each node's body,
including the per-wave JSON compiled from the graph and sent to Jev. Runs,
answers, fired rules and verdicts are recorded as triples linked to the
questions, options and Raptor records they concern, in an Oxigraph store
(`pyoxigraph` in judge-jev). A tree's digest is the SHA-256 of its
canonical form (RDFC-1.0).

The vocabulary, prefix `jj: <urn:judge-jev:ontology#>`:

- Tree: `jj:Tree` (`jj:start`, `jj:node`, `jj:kind`), `jj:Wave`
  (`jj:asks` a `jj:Question`, `jj:rule`, `jj:per`, `jj:statements`,
  `jj:modal`), `jj:Leaf` (`jj:verdict`).
- Question: `jj:Question` (`jj:instructions`, `jj:option` a `jj:Option`,
  `jj:rank`), `jj:Option` (`jj:label`, `jj:criterion`).
- Rule: `jj:BranchRule` (`jj:goto`) and `jj:VerdictRule` (`jj:verdict`),
  each with `jj:rank` and `jj:whenAll` / `jj:whenAny` a `jj:Condition`
  (`jj:question`, `jj:choice` an `jj:Option`).
- Run: `jj:Run` (`jj:tree`, `jj:treeDigest`, `jj:record` the Raptor
  record's IRI), `jj:WaveRun` (`jj:inRun`, `jj:node`, `jj:requestId`,
  `jj:statement`, `jj:fired` a rule), `jj:Answer` (`jj:ofWaveRun`,
  `jj:toQuestion`, `jj:chose` an `jj:Option`, `jj:confidence`,
  `jj:probability` a `jj:OptionProbability` with `jj:option` and `jj:p`),
  `jj:verdictValue` on a run.

### Rationale

Validation of the graph moves to SHACL and of node bodies to pydantic, so
judge-jev's own checking code shrinks to the compile step. One graph of
records, questions and answers makes any verdict traceable and any two
question variations comparable with one query.

### Consequences

**Positive:**

- A question is written once and used by IRI.
- A query over the graph compares question variations across runs.
- The graph renders in a graph viewer for authoring and diagnosis.
- The Rust Jev tool in sc-agent can process the same ontology with
  Oxigraph.

**Negative:**

- `pyoxigraph` and a SHACL validator become dependencies.
- Each wave needs a compile step from the graph to Jev's JSON request.
- Tree authors write Turtle instead of JSON.

### Alternatives Considered

#### Alternative 1: JSON trees with references to shared question files

**Description:** Keep JSON; a wave lists `$ref`s that judge-jev resolves.

**Why Rejected:** It removes duplication only; structure checks stay in
judge-jev's code, and answers stay apart from questions.

#### Alternative 2: JSON trees as today

**Description:** Keep one JSON file per tree with inline questions.

**Why Rejected:** Questions are copied, priority is list position, and
answers cannot be joined to questions without scraping logs.

---

## ADR-JEV-0007: The seam to sc-agent's Jev tool

**Status:** Draft  

### Context

sc-agent's Rust Jev tool will replace judge-jev's Python Jev core
(ADR-JEV-0001). Its first version will not include Oxigraph, though a later
one may. Quality trees and their answers become an RDF graph
(ADR-JEV-0006). The problem is where the boundary lies, so that judge-jev
works with a Jev tool that has no graph store today, and one with Oxigraph
later takes over graph work without judge-jev changing its callers.

### Decision

judge-jev has two ports:

- **Transport:** sends the request lines of one wave and returns their
  result lines. Its contract is the existing batch request and result
  schemas (`assets/schemas/jev-batch-request.schema.json`,
  `jev-batch-result.schema.json`), unchanged. The Python core implements it
  now; sc-agent's Jev tool implements it later.
- **Graph store:** loads a tree, validates it with SHACL, compiles a wave
  to its JSON questions, records a run's triples and answers queries.
  judge-jev implements it now with `pyoxigraph` and a SHACL validator; a
  Jev tool with Oxigraph may implement it later.

Only JSON crosses the transport. The result lines in the sc-observability
log are the record of a run; a run's triples are a projection of those
lines and the tree, so they can be rebuilt from the log at any time. The
tree walk (which wave next, which verdict) uses only the compiled waves and
the answers, so it runs on either side of the seam.

### Rationale

A Jev tool without a graph store needs only the JSON contract it already
has. Because the triples are rebuilt from the log, no run is lost when the
store moves to the other side of the seam.

### Consequences

**Positive:**

- sc-agent's first Jev tool replaces the Python core with no graph work.
- Moving the graph store into sc-agent changes the port's implementation,
  not its callers.

**Negative:**

- Until sc-agent hosts the store, judge-jev carries the graph dependencies.
- The projection from result lines to triples must stay in step with the
  ontology.

### Alternatives Considered

#### Alternative 1: sc-agent's Jev tool reads trees and writes triples

**Description:** Send the TTL tree and the record; the tool walks the tree
and stores the triples.

**Why Rejected:** Its first version has no graph store, so judge-jev would
wait for it.

#### Alternative 2: Triples as the only record of a run

**Description:** Write runs to the graph store instead of the log.

**Why Rejected:** A tool without a store could not record a run, and a lost
store loses the runs.

---

## ADR-JEV-0008: Definitions are graph nodes targeted at records

**Status:** Draft  

### Context

A record can use a term that neither the record nor anything Jev sees
defines, and Jev then has to guess. judge-jev runs over 1000 to 2000 REQ,
ADR and NFR records, each with 1 to 200 code locations. A single definitions
file prepended to every request would be sent tens of thousands of times,
almost always to requests that do not need it. Unrelated material lowers
Jev's accuracy and uses up the request budget. The problem is how to supply
a definition only where it changes an answer, and how to find definitions
that no longer serve anything.

### Decision

A definition is a node in the judge-jev graph (ADR-JEV-0006):

- **`jj:Definition`** holds a `jj:term`, a `jj:text` (short, one line on
  average) and a `jj:source`, the repository file or record that the
  meaning comes from. Pydantic validates the body (ADR-JEV-0005), and SHACL
  validates the edges.
- **`jj:attachedTo`** links a definition to one or more attachments. Each
  attachment names one record (`jj:record`, its Raptor IRI) and optionally
  one location (`jj:location`, the code, prompt, skill or task template
  under evaluation). That gives two cases:
  - **Record only:** the record carries the definition into every Jev call
    about it, every question and every location. Use this when the record's
    own wording is the confusing part.
  - **Record and location:** the definition is added only when that record
    is checked against that location. Use this when the location's material
    needs the clarification, not the record.

  Every question of a request sees its definitions. An attachment is a node
  because an RDF edge links only two things.
- **Storage:** definitions are Turtle files committed in the repository
  under `.sc/judge-jev/`. The per-requirement tree-sitter queries will be
  kept there too, keyed by the same record IDs. Both may move into the
  Raptor database later, once real runs show the feature earns schema
  space. The files load into the store as their own named graph, so they
  never change a tree's digest.

- **Request:** a Jev request has two parts, the state (data) and the
  questions, and Jev answers every question in parallel against the same
  state. Definitions are data: a request carries
  `state = {record, definitions}` (with the location when one is under
  evaluation), followed by the questions. `definitions` holds the record's
  record-only definitions plus those attached to this record and this
  location. A request with no matching definition is the same as before.
  `quality` evaluates the record alone, so it uses record-only definitions. Definitions are never
  truncated. A request that the definitions push over the size limit is
  refused before it is sent. Every request and its log event record the
  digest of each definition carried, and a run's triples link the run to
  them.

- **Tuning:** definitions are added in tuning, and only when they make a
  material change. The steps are:

  1. A failing or `unclear` reason names a term the record leaves undefined.
  2. A definition is written from the repository's own material and named as
     its source.
  3. The requests the definition would reach (the record's, or the record
     and location's) are run with and without it.
  4. The definition is kept only if it can change an answer: an answer's
     choice flips, or its confidence crosses the threshold that decides it.
     A move that stays on the same side of the threshold (90% to 95%) is not
     material. Candidates can be compared together, so a move that does not
     cross on its own (20% to 50%) is material when the set's combined
     change crosses. A definition that changes nothing is removed.

  The commit that adds a definition is its approval record.

- **Question naming:** a question's identity is its IRI, and an IRI is
  declared in one tree file only, across the repository: judge-jev's own trees
  and any consumer extension's (two files declaring one IRI would silently merge
  in the store). Its `jj:id`, the key in requests and reasons, is unique within
  its tree. judge-jev's questions use
  `urn:judge-jev:question:<kind>.<id>`. An extension mints its questions under
  its own namespace.

**`judge-jev doctor`** checks everything judge-jev loads in a repository and
calls nothing:
- schema validation of every tree, question set and definitions file;
- SHACL conformance to the ontology, including edges and the absence of
  cycles;
- duplicate question ids in the scope, as errors;
- warnings, without failing, for:
  - a definition with no attachment;
  - an attachment to a record the Raptor index does not have, or to a
    location that does not exist;
  - a definition whose source does not exist.

### Rationale

Measuring a definition by its effect on Jev's answers keeps the
low-value ones out. "sc-agent" read as "a specific type of agent" may
already be inferred correctly. Targeting by record keeps every request as
small as before unless that record needs help. Definitions sourced from
the repository's own material and checked by A/B carry low risk.

### Consequences

**Positive:**

- Changing or removing a definition affects only the runs it reached, and
  a graph query lists exactly those runs.
- The A/B run spends Jev calls only on the records involved.
- Orphaned definitions and dead links are found by `doctor` rather than
  accumulating.

**Negative:**

- A definition is seen by every question of its record's waves, not only
  the one whose reason prompted it. The A/B run compares every answer, so
  an effect on another question is counted.
- Consumer extensions must follow the question naming rule, or `doctor`
  refuses the scope.

### Alternatives Considered

#### Alternative 1: One definitions file in every request

**Description:** A repository-wide glossary sent as context with every
request.

**Why Rejected:** At this scale it multiplies every request's size and
gives Jev unrelated material.

#### Alternative 2: Definitions inside the question text

**Description:** Append a definition to the instructions of the question
that needed it.

**Why Rejected:** Definitions are data, and Jev keeps data in the state.
The question text would also vary per record.

#### Alternative 3: A Raptor table now

**Description:** Store definitions and their links in Raptor's schema
from the start.

**Why Rejected:** The feature has to prove its value in real runs before
it gets schema space in Raptor.
