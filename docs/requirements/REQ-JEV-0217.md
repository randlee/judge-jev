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

Definitions: A *record* is one REQ, NFR or ADR record in the repository. A *term* is a word or phrase that a record's statements use with a project-specific meaning. A record's *Definitions paragraph* is the paragraph under its Definitions heading. A *definitions file* is a Turtle file under `.sc/judge-jev/` that holds definitions of terms (ADR-JEV-0008). A *shared term* is a term used by more than one record. A term is *defined* where a sentence or `jj:Definition` states its meaning.

**MUST statements:**

- A shared term MUST have exactly one definition.
- The definition of a shared term MUST be in a definitions file.

### Rationale

When each record defines its terms in its own Definitions paragraph, a shared term is defined many times, the copies drift, and a reader of one record cannot find the definition another record relies on. Defining a shared term once, in a definitions file, gives it one meaning across the repository and one place to look it up. The cost is that authors must check the definitions file before writing a Definitions paragraph, and the file becomes a shared point of edit conflicts.

### Success Criteria

**Acceptance Criteria:**

- [ ] For each shared term, a search finds exactly one definition of it, in a definitions file, and none in any record's Definitions paragraph.

### Related Documents

**Architecture Decisions:**

- ADR-JEV-0009
- ADR-JEV-0008