# Requirement: One definitions file per repository

**Status:** Approved  
**Version:** 0.1.0  
**Created:** 2026-11-25  
**Last Updated:** 2026-11-25  
**Owner:** Rand Lee  

---

## REQ-JEV-0217: One definitions file per repository

**Status:** Approved  

### Requirement Statement

Definitions: A *record* is one REQ, NFR or ADR record in the repository. A *term* is a word or phrase that a record's statements use with a project-specific meaning. A record's *Definitions paragraph* is the paragraph under its Definitions heading. A *definitions file* is any Turtle file under `.sc/judge-jev/` that holds definitions of terms (ADR-JEV-0008), and *the definitions file* is the one such file in a repository; a *shared term* is a term used by more than one record.

**MUST statements:**

- A repository MUST hold exactly one definitions file.
- A shared term MUST be defined nowhere but the definitions file.

### Rationale

When each record defines its terms in its own Definitions paragraph, a shared term is defined many times, the copies drift, and a reader of one record cannot find the definition another record relies on. One file gives a shared term one meaning across the repository and one place to look it up. The cost is that authors must check the definitions file before writing a Definitions paragraph, and the file becomes a shared point of edit conflicts.

### Success Criteria

**Acceptance Criteria:**

- [ ] A search of the repository finds exactly one definitions file.
- [ ] For each term that appears in the Definitions paragraph of more than one record, a check finds that term defined once in the definitions file and in no record's Definitions paragraph.

### Related Documents

**Architecture Decisions:**

- ADR-JEV-0009
- ADR-JEV-0008

**External References:**

- [Definitions: one source of truth](../plans/definitions-ssot.md) Decision (b)