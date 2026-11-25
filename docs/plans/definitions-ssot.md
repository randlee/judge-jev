# Definitions: one source of truth (owner, 2026-11-25)

## Owner statement (verbatim)

"both the judge-jev record-author skill AND skills related to evaluating results OR jev-fix related agents/skills MUST have the solutions in a easily referenced SSOT"

The subject is definitions: where a term is defined, how an agent looks one up, adds one and tests one.

## Problem

A beta tester reported "no definition" as a problem on 2026-11-25: a record used a term that neither it nor anything it links defines.

Today the guidance on definitions is spread over three references of the judge-jev skill (fix-strategy, quality-workflow and jev-api), and quality-workflow says the default fix is the record's own Definitions paragraph. A term used by several records is therefore defined in several paragraphs, which can disagree, and an agent has no single place to look one up.

## Decision

Definitions have one source of truth in two parts.

- (a) One reference page in the judge-jev skill, `references/definitions.md`, is the only place that describes how definitions work. Every other skill, agent and reference links to it.
- (b) One definitions file per repository holds each shared term once. A term used by more than one record is defined there, not in a record's Definitions paragraph.

## Alternatives considered

- Each record defines its terms in its own Definitions paragraph (the current default fix). Rejected: a shared term is defined many times, the copies drift, and a reader of one record cannot find the definition another record relies on.
- Each skill and agent keeps its own definitions guidance. Rejected: the copies already disagree (quality-workflow's default fix contradicts this decision), and an agent cannot tell which one is current.

## Consequences

- Positive: an agent looks a term up, adds it and tests it in one place, and a shared term has one meaning across the repository.
- Negative: authors must check the definitions file before writing a Definitions paragraph, and the file becomes a shared point of edit conflicts.
