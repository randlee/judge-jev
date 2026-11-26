#!/usr/bin/env python3
"""Generate docs/diagrams/trees/<tree id>.md from the shipped quality and diagnostic trees.

Reader: anyone who needs to see what a tree asks and how its answers become a verdict, without reading JSON.
Each page is a Mermaid flowchart made only from the tree file: every question and its choices, which choices
are acceptable, the ordered routing and verdict rules, the second wave, and the diagnostic ``d_*`` questions
(shown dashed: they never gate). A diagram therefore cannot disagree with its tree.

    gen_tree_diagrams.py           write the pages
    gen_tree_diagrams.py --check   exit 2 when a committed page differs from what the trees give (used by the tests)
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "plugins/sc-judge-jev/install/templates/skills/judge-jev/assets/questions"
OUT = ROOT / "docs/diagrams/trees"
TREES = ("quality-req", "quality-nfr", "quality-adr", "diag-req", "diag-nfr", "diag-adr")
SOURCE = "plugins/sc-judge-jev/install/templates/skills/judge-jev/assets/questions"


def _choices(value) -> list:
    return value if isinstance(value, list) else [value]


def _esc(text: str) -> str:
    return text.replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def _sid(*parts: str) -> str:
    return "_".join(p.replace("-", "_").replace(" ", "_") for p in parts)


def rejected(node: dict, nodes: dict) -> dict:
    """Question id -> choices that lead to verdict no (a next rule to a 'no' leaf, or a verdict rule giving no)."""
    out: dict = {}
    for rule in node.get("next") or []:
        target = nodes.get(rule["goto"], {})
        if target.get("verdict") == "no" and len(rule.get("when", {})) == 1:
            for q, c in rule["when"].items():
                out.setdefault(q, set()).update(_choices(c))
    for rule in node.get("verdict_rules") or []:
        if rule.get("verdict") == "no":
            for q, c in rule.get("any", {}).items():
                out.setdefault(q, set()).update(_choices(c))
    return out


def routed(node: dict, nodes: dict) -> dict:
    """Question id -> choices that lead to another wave."""
    out: dict = {}
    for rule in node.get("next") or []:
        if "questions" in nodes.get(rule["goto"], {}) and len(rule.get("when", {})) == 1:
            for q, c in rule["when"].items():
                out.setdefault(q, set()).update(_choices(c))
    return out


def _cond(rule: dict) -> str:
    parts = []
    for key, joiner in (("when", " and "), ("all", " and "), ("any", " or ")):
        if rule.get(key):
            parts.append(joiner.join(f"{q} = {' / '.join(_choices(c))}" for q, c in rule[key].items()))
    return " and ".join(parts) or "otherwise"


def render(tree: dict) -> str:
    nodes = tree["nodes"]
    lines = ["flowchart TD"]
    leaves = {name for name, n in nodes.items() if "questions" not in n}
    for name, node in nodes.items():
        if name in leaves:
            continue
        bad, onward = rejected(node, nodes), routed(node, nodes)
        scope = "once per MUST / MUST NOT statement" if node.get("per") == "statement" else "once per record"
        if node.get("only_matched"):
            scope += ", only the statements the rule matched"
        lines.append(f'    subgraph {_sid(name)}["{name}: {scope}"]')
        lines.append("        direction TB")
        for qid, q in node["questions"].items():
            rows = []
            for choice in q["criteria"]:
                if qid.startswith("d_"):
                    mark = "·"
                elif choice in bad.get(qid, ()):
                    mark = "✗"
                elif choice in onward.get(qid, ()):
                    mark = "→"
                else:
                    mark = "✓"
                rows.append(f"{mark} {_esc(choice)}")
            label = f"<b>{qid}</b>" + (" (diagnostic)" if qid.startswith("d_") else "") + "<br/>" + "<br/>".join(rows)
            lines.append(f'        {_sid(name, qid)}["{label}"]')
        lines.append("    end")
        rules = node.get("next") or node.get("verdict_rules") or []
        prev = _sid(name)
        for i, rule in enumerate(rules, 1):
            target = rule.get("goto") or ("verdict_" + rule["verdict"])
            dest = _sid(target) if target in nodes and target not in leaves else _sid("verdict", nodes.get(target, {}).get("verdict", rule.get("verdict", target)))
            if _cond(rule) == "otherwise":
                lines.append(f"    {prev} --> {dest}" if i == 1 else f"    {prev} -- no --> {dest}")
                break
            rid = _sid(name, "r", str(i))
            lines.append(f'    {rid}{{"{i}. {_esc(_cond(rule))}?"}}')
            lines.append(f"    {prev} --> {rid}" if i == 1 else f"    {prev} -- no --> {rid}")
            lines.append(f"    {rid} -- yes --> {dest}")
            prev = rid
        for qid in node["questions"]:
            if qid.startswith("d_"):
                lines.append(f"    class {_sid(name, qid)} diag")
    lines.append('    verdict_yes(["verdict yes"])')
    lines.append('    verdict_no(["verdict no"])')
    lines.append("    classDef diag stroke-dasharray: 4 3,color:#666")
    return "\n".join(lines)


def page(tree_id: str) -> str:
    tree = json.loads((QUESTIONS / f"{tree_id}.json").read_text(encoding="utf-8"))
    gating = [q for n in tree["nodes"].values() for q in n.get("questions", {}) if not q.startswith("d_")]
    diag = [q for n in tree["nodes"].values() for q in n.get("questions", {}) if q.startswith("d_")]
    return f"""<!-- Generated by scripts/gen_tree_diagrams.py from {SOURCE}/{tree_id}.json. Do not edit; rerun the script. -->
# Tree `{tree_id}` ({tree['kind'].upper()})

Reader: anyone judging or fixing a {tree['kind'].upper()} record who needs to know what Jev is asked and why a
verdict came out as it did. Source: [`{tree_id}.json`](../../../{SOURCE}/{tree_id}.json).

```mermaid
{render(tree)}
```

Marks: ✓ acceptable, ✗ gives verdict no, → asks the next wave, · diagnostic (never gates).
Rules are tried in order; the first that matches decides. In a per-statement wave a rule matches when any one
statement matches it.

- Gate questions: {', '.join(f'`{q}`' for q in gating)}.
- Diagnostic questions: {', '.join(f'`{q}`' for q in diag) or 'none'}. They explain a weak answer and never gate.
- The pass gate over three runs is in [../gate.md](../gate.md).
"""


def main(argv: list) -> int:
    check = "--check" in argv
    stale = []
    for tree_id in TREES:
        target = OUT / f"{tree_id}.md"
        text = page(tree_id)
        if check:
            if not target.exists() or target.read_text(encoding="utf-8") != text:
                stale.append(str(target.relative_to(ROOT)))
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    for s in stale:
        print(f"stale: {s} (run python3 scripts/gen_tree_diagrams.py)")
    return 2 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
