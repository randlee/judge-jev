---
name: jev-fix-proposer
version: 0.1.0
description: Proposes candidate edits for one failing REQ, NFR or ADR record from Jev's failing answers, each naming the answer it targets and keeping the record's obligations. Read-only; never calls Jev. Run several in parallel with no shared context.
model: grok[effort=high]
is_background: true
force-default-model: true
---
