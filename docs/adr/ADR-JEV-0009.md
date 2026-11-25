# Decision: Definitions have one source of truth

**Status:** Approved  
**Version:** 0.1.0  
**Created:** 2026-11-25  
**Last Updated:** 2026-11-25  
**Owner:** Rand Lee  
**Decision Date:** 2026-11-25  

---

## ADR-JEV-0009: Definitions have one source of truth

**Status:** Approved  

### Related Documents

ADR-JEV-0008 (Definitions are graph nodes targeted at records) names a definitions file `.sc/judge-jev/definitions.ttl`.

**Architecture Decisions:**

- ADR-JEV-0008

### Context

A beta tester reported "no definition" as a problem on 2026-11-25: a record used a term that neither it nor anything it links defines.

Today the guidance on definitions is spread over three references of the judge-jev skill (fix-strategy, quality-workflow and jev-api), and quality-workflow says the default fix is the record's own Definitions paragraph. A term used by several records is therefore defined in several paragraphs, which can disagree, and an agent has no single place to look one up.

### Decision

Definitions have one source of truth in two parts.

- (a) One reference page in the judge-jev skill, `references/definitions.md`, is the only place that describes how definitions work. Every other skill, agent and reference links to it.
- (b) One definitions file per repository holds each shared term once. A term used by more than one record is defined there, not in a record's Definitions paragraph.

### Rationale

The owner requires that the judge-jev record-author skill, the skills that evaluate results, and the jev-fix agents and skills have the solutions in an easily referenced single source of truth. One reference page and one definitions file give an agent one place to look a term up, add it and test it.

### Consequences

**Positive:**

- An agent looks a term up, adds it and tests it in one place.
- A shared term has one meaning across the repository.

**Negative:**

- Authors must check the definitions file before writing a Definitions paragraph.
- The definitions file becomes a shared point of edit conflicts.

### Alternatives Considered

#### Alternative 1: Each record defines its terms in its own Definitions paragraph

**Description:**

The current default fix.

**Cons:**

- A shared term is defined many times and the copies drift.
- A reader of one record cannot find the definition another record relies on.

**Why Rejected:**

A shared term is defined many times, the copies drift, and a reader of one record cannot find the definition another record relies on.

#### Alternative 2: Each skill and agent keeps its own definitions guidance

**Description:**

Every skill and agent describes definitions itself.

**Cons:**

- The copies already disagree.

**Why Rejected:**

The copies already disagree (quality-workflow's default fix contradicts this decision), and an agent cannot tell which one is current.