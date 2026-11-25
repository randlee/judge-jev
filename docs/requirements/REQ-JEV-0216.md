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

Definitions: The judge-jev skill is the skill at `.claude/skills/judge-jev`. The definitions reference page is the file `references/definitions.md` in the judge-jev skill. A file describes how definitions work when it says where a term is defined, or how an agent looks a term up, adds a term or tests a term. A skill is a directory under `.claude/skills`; an agent is a file under `.claude/agents`; a reference is a file in a skill's `references` directory. A guidance file is any skill, agent or reference file other than the definitions reference page. A file links to the definitions reference page when it holds a Markdown link whose target is that page.

**MUST statements:**

- Every guidance file MUST link to the definitions reference page.

**MUST NOT statements:**

- A guidance file MUST NOT describe how definitions work.

### Rationale

The owner requires that the judge-jev record-author skill, the skills that evaluate results, and the jev-fix agents and skills have the solutions in an easily referenced single source of truth. Today the guidance on definitions is spread over three references of the judge-jev skill (fix-strategy, quality-workflow and jev-api), and an agent has no single place to look one up.

### Success Criteria

**Acceptance Criteria:**

- [ ] The file `references/definitions.md` exists in the judge-jev skill.
- [ ] No skill, agent or reference other than `references/definitions.md` describes how definitions work.
- [ ] Every skill, agent and reference other than `references/definitions.md` contains a link to `references/definitions.md`.

### Related Documents

**Architecture Decisions:**

- ADR-JEV-0009