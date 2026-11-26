# Quality panels

sc-compose templates that draw judge-jev quality results as XHTML panels. Nothing here calls a model.

```bash
python scripts/render_quality_panels.py <out-dir>                      # three tree panels, the three example fixes, index.html
python scripts/render_quality_panels.py <out-dir> --changes my-fix.json
```

| Template | Draws | Variables come from |
| --- | --- | --- |
| `quality-tree-panel.xhtml.j2` | One quality tree: each check with the words Jev is sent, then every path through the tree | `scripts/quality_tree_vars.py`, which reads the tree file and `labels.json` |
| `record-change-panel.xhtml.j2` | What changed in one record and the fault behind each edit | One JSON file, fields below |
| `report-page.xhtml.j2` | A standalone page around rendered panels | `page` (`title`, `eyebrow`, `lede`, `foot`) and `groups` (`title`, `panels`: `anchor`, `nav`, `html`) |

`labels.json` holds the short title of each check ("Is every term defined?"). It is the only text on a tree panel
that is not in the tree file. `tests/sc-judge-jev/test_quality_panels.py` fails when a gate question has no title,
and when a rendered panel and its tree file disagree.

## A change file

`examples/` holds three, built by hand from real sc-agent fixes. No command writes this file yet.

| Field | Meaning |
| --- | --- |
| `record` | `id`, `kind` (`req`, `nfr`, `adr`), `kind_label`, `title`, `repo`, `from`, `to`, `evidence` (where the figures come from) |
| `result` | `before`, `after`, `summary`: the record's state before and after, in words |
| `edits[]` | One entry per edit: `where`, `check_id`, `check_label`, `fault`, `before`, `after`, `bar`, `meaning`, `note` |
| `edits[].named`, `named_by`, `named_share` | The part named as the fault, who named it, and its share of the answer; empty strings when nothing was named |
| `edits[].segments[]` | The edited text in order: `t` is `same`, `ins` or `del`, with `text` |
| `edits[].added[]` | Text added elsewhere in the record: `to` (the section) and `text` |
