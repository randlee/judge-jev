---
name: jev-fix-proposer
version: 0.3.0
description: Writes one candidate edit for one weak statement of a REQ, NFR or ADR record, using the one strategy it is given and keeping the record's obligations. Read-only; never calls Jev. Launch one per statement and strategy, in parallel, with no shared context.
model: grok[effort=high]
is_background: true
force-default-model: true
---
