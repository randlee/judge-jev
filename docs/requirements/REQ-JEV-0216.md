# Requirement: One definitions reference page

**Status:** Approved  
**Version:** 0.1.0  
**Created:** 2026-11-25  
**Last Updated:** 2026-11-25  
**Owner:** Rand Lee  

---

## REQ-JEV-0216: One definitions reference page

**Status:** Approved  

### Requirement Statement

Definitions: The judge-jev skill is the skill named `judge-jev` that the sc-judge-jev plugin installs. The definitions reference page is the file `references/definitions.md` in the judge-jev skill. A file describes how definitions work when it says where a term is defined, or how an agent looks a term up, adds a term or tests a term. A guidance file is a skill, agent or reference file that the sc-judge-jev plugin installs, in any harness, other than the definitions reference page. A file links to the definitions reference page when it holds a Markdown link whose target is that page.

**MUST statements:**

- A guidance file that tells an agent to look up, add or test a term MUST link to the definitions reference page.

**MUST NOT statements:**

- A guidance file MUST NOT describe how definitions work.

### Rationale

The owner requires that the judge-jev record-author skill, the skills that evaluate results, and the jev-fix agents and skills have the solutions in an easily referenced single source of truth. Today the guidance on definitions is spread over three references of the judge-jev skill (fix-strategy, quality-workflow and jev-api), and an agent has no single place to look one up.

### Success Criteria

**Acceptance Criteria:**

- [ ] The file `references/definitions.md` exists in the judge-jev skill.
- [ ] No guidance file describes how definitions work.
- [ ] Every guidance file that tells an agent to look up, add or test a term contains a link to `references/definitions.md`.

### Related Documents

**Architecture Decisions:**

- ADR-JEV-0009