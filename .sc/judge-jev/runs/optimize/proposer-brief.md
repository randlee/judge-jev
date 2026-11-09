# Proposer brief: small tweaks to judge-jev REQ/NFR records

You propose small, independent text tweaks to requirement records. The author applies each tweak ALONE to the record's current text and re-judges it with live Jev, a judge model. You never judge anything and you never edit files in the repo. You only write one JSON file (path given in your task).

## How a record is judged
Each MUST / MUST NOT bullet is a statement. Jev sees the statement plus the whole record as context and answers four questions:
- obligations: 1 | 2 | 3 | 4+
- joined_by: none | and-list | condition+obligation | alternatives | obligation+rationale
- term: none | project term defined in a linked record | project term defined nowhere | vague qualifier | undefined acronym
- check: unit test | CLI run | inspection or grep | needs a measure | none

A statement FAILS when rule 1 fires (obligations is 2, 3 or 4+ AND joined_by is and-list, alternatives or obligation+rationale) or rule 2 fires (term is "project term defined nowhere", "vague qualifier" or "undefined acronym", OR check is "needs a measure" or "none").
Primary score: number of failing statements (lower is better). Jev is noisy: answers below about 0.35 confidence flip run to run.

## Tweak types (use the type names exactly)
- define: define a term or acronym in the record (usually in its `Definitions:` paragraph).
- cite: name the record or doc that defines a term, e.g. "(REQ-JEV-0207)", instead of or in addition to defining it.
- measure: replace a vague qualifier with the measure the code or tests use. Look it up in the repo; never invent a number.
- threshold: add a threshold the code enforces. Look it up; never invent.
- split: split a compound statement into separate MUST bullets. The obligations must stay exactly the same.
- move-rationale: move a reason or purpose clause out of a statement into the Rationale section.
- reword: reword for clarity without changing the obligation.
- remove: remove a definition sentence, a clause of a definition, or another clause that does not carry an obligation. A definition must earn its place: a definition that defines a term no statement uses, or a term Jev would understand as common usage, is a removal candidate. (The author already tries removing each whole definition sentence one at a time, so prefer removals of PART of a sentence, of redundant restatements, or of definitions for terms appearing only outside the statements.)

## Rules
1. Each tweak is one replacement inside ONE record: `old` must be an exact substring of that record's CURRENT TEXT (whitespace and line breaks are matched loosely), and `new` is its replacement (empty string deletes). Keep `old` short but unique within the record.
2. Never change the meaning of an obligation: do not add, drop, weaken or strengthen one. No new numbers or thresholds unless you cite where the code or tests enforce them (file:line).
3. Text quoted from Rand (the Rationale quotes "Rand ...: \"...\"") stays verbatim. Do not touch it.
4. Do not edit anything outside the record's REQ/NFR section. Do not touch question trees, rules, code or ADRs.
5. Prioritize: (a) statements marked FAIL in any run; (b) statements whose deciding answer passes with low confidence (term or check below about 0.5, or obligations/joined_by suggesting a compound); (c) removals that shorten the record without exposing a term a statement relies on.
6. Facts for definitions, measures and thresholds come from the repo: /Users/randlee/github/judge-jev-worktrees/docs/record-terms (read-only for you). Code under `plugins/` or `skills/` or `src/`, tests under `tests/`, ADRs in `docs/adr/`. Put the file:line in `evidence`.
7. Aim for about 6 to 10 tweaks per record that has failing or low-confidence statements, and 3 to 5 for records that already pass (mostly removals and shortenings). Each tweak must be independent of the others (applies to the current text alone).

## Output
Write a JSON array to the output path. Each element:
{"rid": "REQ-JEV-0209", "type": "define|cite|measure|threshold|split|move-rationale|reword|remove", "target": "s3" or "defs", "old": "...", "new": "...", "why": "one line", "evidence": "file:line or empty"}
Validate the file parses as JSON (python3 -c 'import json,sys;json.load(open(sys.argv[1]))' <path>). Reply with only the count of tweaks per record.
