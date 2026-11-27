---
name: req-author
version: 0.11.0
description: Writes one REQ, NFR or ADR record that passes judge-jev, or repairs an existing one, from its source only: renders it with Raptor's template, judges it with Jev, and edits only the part Jev names. Returns pass or blocked with one question.
model: grok[effort=high]
is_background: true
force-default-model: true
---
