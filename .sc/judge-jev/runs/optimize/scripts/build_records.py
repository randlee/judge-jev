"""One file per record under records/: original, final, diffs, scores, kept tweaks with measured effect."""
import json, difflib, re
from pathlib import Path
import lib

OPT = lib.OPT; out = OPT / "records"; out.mkdir(exist_ok=True)
S = {n: json.load(open(OPT / f)) for n, f in [("orig", "state-orig.json"), ("greedy", "state0.json"), ("final", "state-final3.json")]}
FIN = {n: [json.load(open(OPT / f"fin2-{n}-{k}.json")) for k in range(6)] for n in S}
dec = json.load(open(OPT / "final-decision.json")); i4 = json.load(open(OPT / "iter4/kept.json"))
cands = {}
for it in (1, 2, 3):
    for nm in ("eval.json", "evalx.json"):
        f = OPT / f"iter{it}" / nm
        if f.exists():
            for rid, cs in json.load(open(f))["cands"].items():
                for c in cs: cands.setdefault(rid, []).append((it, c))
tw = [json.loads(l) for l in open(OPT / "tweaks-index.jsonl")]

def diff(a, b, x, y):
    return "".join(difflib.unified_diff(a.splitlines(True), b.splitlines(True), x, y))
def norm(s): return re.sub(r"\s+", " ", s).strip()
def score(n, rid):
    f = [r[rid]["fails"] for r in FIN[n]]; m = sum(r[rid]["margin"] for r in FIN[n]) / 6
    return f, m

summary = {}
for rid in sorted(S["orig"]):
    o, g, fz = S["orig"][rid], S["greedy"][rid], S["final"][rid]
    L = [f"# {rid}\n", "Scores: 6 interleaved Jev runs (fin2-*), same time window. fails = failing statements per run; margin = mean answer margin.\n",
         "| text | failing statements per run | failing runs | mean margin |", "|---|---|---|---|"]
    sc = {}
    for n in ("orig", "greedy", "final"):
        f, m = score(n, rid); sc[n] = (sum(1 for x in f if x), round(m, 3), sum(f))
        L.append(f"| {n} | {f} | {sc[n][0]}/6 | {m:.3f} |")
    f3 = {n: [json.load(open(OPT / f"fin3-{n}-{k}.json"))[rid] for k in range(3)] for n in ("greedy", "final")}
    L.append(""); L.append("Re-check after the NFR-JEV-0001 punctuation fix (fin3-*, 3 interleaved runs): " + "; ".join(
        f"{n} fails {[x['fails'] for x in v]} margin {sum(x['margin'] for x in v)/3:.3f}" for n, v in f3.items()) + ".")
    d = dec.get(rid, {})
    L += ["", f"Selection: {d.get('choice', '?')} (paired runs: fixes-only {d.get('fail_runs_fixes')} failing runs, margin {d.get('margin_fixes')}; "
          f"pruned {d.get('fail_runs_pruned')} failing runs, margin {d.get('margin_pruned')})."]
    if rid in i4:
        k = i4[rid]
        cf = json.load(open(OPT / "iter4/confirm.json"))[rid]["control"]; ev = json.load(open(OPT / "iter4/eval.json"))["control"][rid]
        e = f"eval {k['fail_runs']}/{k['runs']} failing runs, margin {k['margin']:.3f} (control {ev['fail_runs']}/12, {ev['margin']:.3f}); " if "runs" in k else "eval: not run (author-rejected, then readmitted); "
        L.append(f"Iteration 4 change adopted: {k['src']} {k['type']} {k['target']}: {e}confirmation {k['confirm_fail_runs']}/12, "
                 f"margin {k['confirm_margin']:.3f} (control {cf['fail_runs']}/12, {cf['margin']:.3f}). See iter4/eval.json, iter4/confirm.json.")
    # kept tweaks: in final text, dedupe by (old,new)
    # pipeline lineage: which iterations' combined tweaks can be in this record's final text
    used = {it: {(c["old"], c["new"]) for c in json.load(open(OPT / f"iter{it}/combine.json"))["used"].get(rid, [])} for it in (1, 2, 3)}
    if d.get("choice") == "fixes-only":
        lineage = {(1, o_, n_) for o_, n_ in used[1] if not lib.is_removal({"old": o_, "new": n_, "type": "x"})}
    else:
        lineage = {(1, *x) for x in used[1]} | {(2, *x) for x in used[2]}
        if rid in json.load(open(OPT / "iter3/paired-decision.json"))["kept_from_iter3"]: lineage |= {(3, *x) for x in used[3]}
    if rid in i4: lineage.add((4, i4[rid]["old"], i4[rid]["new"]))
    seen = {}
    for t in tw:
        if t["record"] == rid and t["in_final_text"] and (t["iteration"], t["old"], t["new"]) in lineage:
            seen.setdefault((norm(t["old"]), norm(t["new"])), []).append(t)
    L += ["", "## Kept tweaks (text present in the final record) and measured effect", ""]
    if not seen: L.append("None: the final text equals the greedy text." if norm(g) == norm(fz) else "None matched individually.")
    for (old, new), ts in seen.items():
        L.append(f"- {ts[0]['type']} {ts[0]['target']} (proposed by {', '.join(sorted({f'i{t['iteration']}:{t['src']}' for t in ts}))})")
        L.append(f"  - old: `{old[:400]}`"); L.append(f"  - new: `{new[:400] or '(removed)'}`")
        for t in ts:
            c = next((c for it, c in cands.get(rid, []) if it == t["iteration"] and c["old"] == t["old"] and c["new"] == t["new"]), None)
            if c is None: c = i4.get(rid) if t["iteration"] == 4 else None
            if not c: continue
            ms = [f"{s}: fails {c[s]['fails']}, margin {c[s]['margin']:.3f}" for s in sorted(c) if re.fullmatch(r"m\d+", s) and isinstance(c[s], dict) and "fails" in c[s]]
            ref = c.get("ref") or {}
            if ms: L.append(f"  - i{t['iteration']} {t['src']}: " + "; ".join(ms) + (f" (reference margin {ref.get('margin_mean', 0):.3f}, reference fails mean {ref.get('fails_mean', 0):.2f})" if ref else ""))
            elif "fail_runs" in c: L.append(f"  - i4 {t['src']}: {c['fail_runs']}/{c['runs']} failing runs, margin {c['margin']:.3f}; confirmation {c.get('confirm_fail_runs')}/12, margin {c.get('confirm_margin', 0):.3f}")
    gd = [norm(x) for x in lib.def_sentences(g)[1]]; fd = [norm(x) for x in lib.def_sentences(fz)[1]]
    pruned = [x for x in gd if x not in fd]; added = [x for x in fd if x not in gd]
    L += ["", "## Definitions pruned (greedy -> final)", ""] + ([f"- {x}" for x in pruned] or ["None."])
    L += ["", "## Definitions added or reworded (greedy -> final)", ""] + ([f"- {x}" for x in added] or ["None."])
    L += ["", "## Diff: original (origin/docs/record-fixes) -> final", "", "```diff", diff(o, fz, "original", "final"), "```",
          "", "## Diff: greedy (previous commit) -> final", "", "```diff", diff(g, fz, "greedy", "final") or "(no change)", "```",
          "", "## Original text", "", "````markdown", o.rstrip(), "````", "", "## Final text", "", "````markdown", fz.rstrip(), "````", ""]
    (out / f"{rid}.md").write_text("\n".join(L))
    summary[rid] = {"orig": sc["orig"], "greedy": sc["greedy"], "final": sc["final"], "choice": d.get("choice"),
                    "kept_tweaks": len(seen), "defs_pruned": pruned, "changed_vs_greedy": norm(g) != norm(fz)}
json.dump(summary, open(OPT / "records-summary.json", "w"), indent=1)
for rid, s in summary.items(): print(rid, s["orig"], s["greedy"], s["final"], s["choice"], s["kept_tweaks"], len(s["defs_pruned"]), s["changed_vs_greedy"])
