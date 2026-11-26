# judge-jev publishes its evidence — integration reports, browsable without a clone

**Released:** November 25, 2026

judge-jev answers one question per requirement record: does this place actually
implement it, and if not, why not. Until now the evidence for that answer only
existed as files in the repository.

## What is new

The repository now publishes a static site. Every integration run already
committed under `site/reports/` is browsable as HTML, newest first, with no
clone and no build step on your side.

- **Reports** — one page per run, each self-contained HTML
- **Diagrams** — architecture and flow, rendered as HTML
- **Announcements** — this page and whatever follows it

## Why it matters

A verdict is only useful if you can find it. A failing run is the interesting
one, and the interesting ones are exactly the ones nobody re-runs to read.

## How it is built

The site commits only sources: the report HTML, the announcement markdown, the
diagrams. Every index page is generated at deploy time by `scripts/build-site.py`,
so the published site cannot disagree with the committed records — and there are
no bot commits to keep in sync.
