#!/usr/bin/env python3
"""Turn one judge-jev quality tree file into the variables of templates/quality-panels/quality-tree-panel.xhtml.j2.

Everything shown on the panel comes from the tree file, except the short check titles, which come
from templates/quality-panels/labels.json (a check with no title shows its id). No model call, no judge-jev import.
"""
import hashlib, json, re, sys
from pathlib import Path

def _list(v): return v if isinstance(v, list) else [v]

def _asked(instructions: str) -> str:
    """The question itself: the instructions without the 'item.text is JSON ...' preamble."""
    for marker in ("as context. ", "as JSON. "):
        if marker in instructions:
            return instructions.split(marker, 1)[1].strip()
    return instructions.strip()

def _rules(node: dict) -> list:
    """Ordered (question -> choices, target) pairs; target is ('verdict', v) or ('node', id). Last entry is the default."""
    out = []
    for r in node.get("next", []):
        out.append(({q: _list(c) for q, c in r.get("when", {}).items()}, ("node", r["goto"])))
    for r in node.get("verdict_rules", []):
        if "all" in r:
            raise ValueError("verdict rule with 'all' is not drawn yet")
        for q, c in r.get("any", {}).items():          # any-of: one line per question, in file order
            out.append(({q: _list(c)}, ("verdict", r["verdict"])))
        if "any" not in r:
            out.append(({}, ("verdict", r["verdict"])))
    return out

def _resolve(nodes, target):
    kind, name = target
    if kind == "node" and "verdict" in nodes[name]:
        return ("verdict", nodes[name]["verdict"])
    return target

def build(tree: dict, labels: dict, source: str, sha: str) -> dict:
    nodes, lab = tree["nodes"], labels["checks"]
    order, calls, columns = [], [], []
    todo, seen = [tree["start"]], set()
    while todo:                                           # waves in the order they can be reached
        nid = todo.pop(0)
        if nid in seen or "questions" not in nodes[nid]: continue
        seen.add(nid); order.append(nid)
        todo += [t[1] for _, t in _rules(nodes[nid]) if t[0] == "node"]
    call_no = {nid: i + 1 for i, nid in enumerate(order)}
    for nid in order:
        node, rules = nodes[nid], _rules(nodes[nid])
        gate_qs = [q for when, _ in rules for q in when]
        gate_qs = list(dict.fromkeys(gate_qs))
        default = _resolve(nodes, rules[-1][1])
        checks = []
        for q in gate_qs:
            body, choices = node["questions"][q], []
            for name, meaning in body["criteria"].items():
                hit = next(((i, _resolve(nodes, t)) for i, (when, t) in enumerate(rules) if name in when.get(q, [])), None)
                if hit:
                    i, t = hit
                    outcome = "bad" if t == ("verdict", "no") else "ok" if t[0] == "verdict" else "nx"
                    leads = f"verdict {t[1]}" if t[0] == "verdict" else f"call {call_no[t[1]]}"
                    rule = f"{nid}.rule[{i + 1}]"
                else:
                    last = q == gate_qs[-1]
                    outcome, rule = "ok", ""
                    leads = (f"verdict {default[1]}" if default[0] == "verdict" else f"call {call_no[default[1]]}") if last else "next check"
                choices.append({"name": name, "meaning": meaning, "outcome": outcome, "leads": leads, "rule": rule})
            n = len(columns) + 1
            columns.append({"n": n, "id": q, "label": lab.get(q, q), "node": nid})
            checks.append({"n": n, "id": q, "label": lab.get(q, q), "asked": _asked(body["instructions"]), "choices": choices})
        diags = [{"id": q, "asked": _asked(b["instructions"]), "choices": list(b["criteria"])}
                 for q, b in node["questions"].items() if q not in gate_qs]
        per = node.get("per", "record")
        asked_of = "one request per MUST / MUST NOT statement" if per == "statement" else "one request for the whole record"
        feeders = [c["name"] for other in calls for ch in other["checks"] for c in ch["choices"] if c["leads"] == f"call {call_no[nid]}"]
        calls.append({"n": call_no[nid], "node": nid, "asked_of": asked_of, "only_after": " / ".join(feeders),
                      "checks": checks, "diagnostics": diags})
    col_ix = {c["id"]: i for i, c in enumerate(columns)}

    def walk(nid, prefix):
        rules, gate = _rules(nodes[nid]), [c["id"] for c in columns if c["node"] == nid]
        passed = {}                                        # question -> choices that did not fire an earlier rule
        for when, target in rules:
            cells = dict(prefix)
            for q in gate:
                allc = list(nodes[nid]["questions"][q]["criteria"])
                if q in when:
                    t = _resolve(nodes, target)
                    k = "bad" if t == ("verdict", "no") else "ok" if t[0] == "verdict" else "nx"
                    cells[q] = {"k": k, "choices": when[q]}
                elif q in passed:
                    cells[q] = {"k": "ok", "choices": passed[q]}
                elif not when:                              # default rule: every gate question passed
                    cells[q] = {"k": "ok", "choices": allc}
                else:
                    cells[q] = {"k": "na", "choices": [], "why": "not used"}
            for q, fired in when.items():
                keep = [c for c in passed.get(q, list(nodes[nid]["questions"][q]["criteria"])) if c not in fired]
                passed[q] = keep
            if not when:
                for q in gate: cells[q] = {"k": "ok", "choices": passed.get(q, list(nodes[nid]["questions"][q]["criteria"]))}
            t = _resolve(nodes, target)
            if t[0] == "verdict":
                yield cells, t[1], (next(iter(when)) if when else "")
            else:
                yield from walk(t[1], cells)

    paths = []
    for cells, verdict, stop in walk(tree["start"], {}):
        row = []
        for c in columns:
            cell = cells.get(c["id"], {"k": "na", "choices": [], "why": "not asked"})
            row.append({"q": c["id"], "k": cell["k"], "choices": cell["choices"],
                        "t": " / ".join(cell["choices"]) if cell["choices"] else cell["why"]})
        paths.append({"n": len(paths) + 1, "cells": row, "verdict": verdict, "stop": stop})
    per = nodes[tree["start"]].get("per", "record")
    return {"tree": {"id": tree["id"], "kind": tree["kind"], "kind_label": labels["kinds"].get(tree["kind"], tree["kind"].upper()),
                     "version": tree.get("version"), "source": source, "sha256": sha,
                     "unit": "MUST statement" if per == "statement" else "record", "per": per},
            "calls": calls, "columns": columns, "paths": paths,
            "counts": {"paths": len(paths), "yes": sum(p["verdict"] == "yes" for p in paths), "columns": len(columns)}}

def load(tree_path: Path, labels_path: Path, source: str = "") -> dict:
    raw = tree_path.read_bytes()
    return build(json.loads(raw), json.loads(labels_path.read_text()), source or tree_path.name, hashlib.sha256(raw).hexdigest())

if __name__ == "__main__":
    print(json.dumps(load(Path(sys.argv[1]), Path(sys.argv[2])), indent=1))
