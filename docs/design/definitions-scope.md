# Design: a definition for every record, carried only where used

Status: design only, no code (owner brief, 2026-11-25). Follows ADR-JEV-0009 and REQ-JEV-0217.

## Today

A definition reaches a request only through a `jj:Attachment` naming one record (and optionally one location). `DefinitionSet.for_request(record_iri, location)` (`scripts/jev_definitions.py`) returns the attached ones. A shared term used by 20 records needs 20 attachments, and a record that uses the term but lacks an attachment is judged as if the term were undefined. That is the beta tester's "no definition" report.

## Problem 1: apply a definition to every record without listing each

| Option | How | Size |
| --- | --- | --- |
| A. Repository attachment | A new attachment form `a:x a jj:Attachment ; jj:scope jj:Repository .` reaches every record. `reaches()` returns true for it. | SHACL shape +6 lines; `Definition.reaches` +3; doctor: no `RECORD_UNKNOWN` for it. About 15 lines plus 4 tests. |
| B. Unattached means everywhere | A definition with no attachment reaches every record. | About 5 lines. But it silently changes the meaning of today's files: `DEFINITION.UNATTACHED` is a warning now, and old unattached definitions would start reaching every request and change every digest. |
| C. Pattern attachment | `jj:recordPattern "REQ-JEV-02*"` matches record ids. | About 25 lines plus pattern validation and tests. Only worth it if a term means different things in different id ranges, which REQ-JEV-0217 (one meaning per shared term) rules out. |

Recommendation: A. It is explicit, keeps old files byte-identical in meaning, and is the smallest safe change.

## Problem 2: a request carries only the terms its record uses

With A alone, every record's request carries every repository definition: more bytes against `--max-request-bytes` and more noise for Jev.

| Option | How | Size |
| --- | --- | --- |
| D. Text match | Of the repository-scoped definitions, carry those whose `jj:term` (or an optional `jj:alias`, for plurals and spellings) occurs in the record text as a whole word, case-insensitive. Record- and location-attached definitions are carried as today. | About 25 lines in `for_request` (it takes the record text), `jj:alias` in the ontology and shape (+8), tests with controlled record text (deterministic). The log's `definitions` list already records exactly what was carried. |
| E. Record declares its terms | A record lists the shared terms it uses (a `Uses terms:` line). | Small in code, but edits every record and duplicates what the text already says; a missing line is a new "no definition". |
| F. Raptor supplies used terms | Raptor's index lists each record's terms. | Depends on Raptor's schema (an `integration/judge-jev` change); larger and out of this repo. |

Recommendation: D, with `jj:alias`. Risk: a term used only through a synonym is missed; doctor can warn when a repository definition matches no record (`DEFINITION.UNUSED`, about 10 lines).

## Combined size of A + D

About 60 lines of code across `jev_definitions.py`, `jev_graph.py`, the ontology and the SHACL shape, plus about 10 tests. `references/definitions.md` gains one subsection. No change to the request format: `state.definitions` stays `[{term, text}]`.
