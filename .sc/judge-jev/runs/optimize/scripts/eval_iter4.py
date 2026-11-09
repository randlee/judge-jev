"""Iteration 4: targeted candidates on the final text, 12 interleaved runs each with a 12-run control.
usage: eval_iter4.py <state.json> <rids> <runs>"""
import json, sys, glob, hashlib, lib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
st = json.load(open(sys.argv[1])); rids = sys.argv[2].split(","); N = int(sys.argv[3])
D = lib.OPT/"iter4"; orig = lib.load_records(lib.OPT/"orig-req")
cands = {r: [] for r in rids}; rejects = []; seen = {r: {st[r]} for r in rids}
extra = []  # earlier measured tweaks re-tried on the final text
for it in (1, 3):
    for r, v in json.load(open(lib.OPT/f"iter{it}/eval.json"))["cands"].items():
        if r in rids:
            for c in v:
                if c.get("src") != "mechanical" and c.get("target") in ({"REQ-JEV-0210": "s2", "REQ-JEV-0208": "s3"}[r],):
                    extra.append({k: c[k] for k in ("rid", "type", "target", "old", "new", "why", "src") if k in c} | {"src": f"iter{it}-{c['src']}"})
props = extra + [c | {"src": Path(p).stem} for p in sorted(glob.glob(str(D/"props/*.json"))) for c in json.load(open(p))]
for c in props:
    r = c.get("rid")
    if r not in rids: continue
    t = lib.apply_tweak(st[r], c.get("old", ""), c.get("new", ""))
    if t is None: rejects.append(c | {"reject": "old not found exactly once"}); continue
    if t in seen[r]: rejects.append(c | {"reject": "duplicate or no-op"}); continue
    if not lib.quotes_ok(orig[r], t): rejects.append(c | {"reject": "touches a Rand quote"}); continue
    g = lib.obligation_guard_section(st[r], t)
    if g: rejects.append(c | {"reject": "obligation guard: " + g}); continue
    import re as _re
    if r == "REQ-JEV-0208" and not _re.search(r"(without\s+calling\s+Jev|MUST\s+NOT\s+call\s+Jev|no\s+call\s+to\s+Jev|zero\s+calls\s+to\s+Jev)", lib.statements_block(t)):
        rejects.append(c | {"reject": "author: drops the no-Jev-call obligation"}); continue
    if r == "REQ-JEV-0210" and _re.search(r"refuse\s+more\s+than\s+one", t):
        rejects.append(c | {"reject": "author: adds an obligation (refuse more than one flag) with no code evidence"}); continue
    seen[r].add(t); c["text"] = t; cands[r].append(c)
nslot = max(len(v) for v in cands.values())
slots = [{r: v[j]["text"] for r, v in cands.items() if j < len(v)} for j in range(nslot)] + [{r: st[r] for r in rids}]  # last = control
def one(a):
    j, k = a; name = "ctl" if j == nslot else f"c{j}"
    return j, k, f"repos/i4-{name}-{k}/i4-{name}-{k}", lib.judge_texts(lib.OPT/f"repos/i4-{name}-{k}", slots[j], sorted(slots[j]), f"i4-{name}-{k}")
jobs = [(j, k) for k in range(N) for j in range(nslot + 1)]
res = {}
with ThreadPoolExecutor(6) as ex:
    for j, k, path, m in ex.map(one, jobs):
        for r in slots[j]: res.setdefault((r, j), []).append((path, m[r]))
ctl = {}
for r in rids:
    ms = [m for _, m in res[(r, nslot)]]
    ctl[r] = {"fail_runs": sum(1 for m in ms if m.get("fails")), "runs": len(ms), "margin": sum(m.get("margin", 0) for m in ms) / len(ms), "paths": [p for p, _ in res[(r, nslot)]]}
    print(r, "CONTROL", ctl[r]["fail_runs"], "/", ctl[r]["runs"], f"m={ctl[r]['margin']:.3f}")
    for j, c in enumerate(cands[r]):
        ms = [m for _, m in res[(r, j)]]
        c["fail_runs"] = sum(1 for m in ms if m.get("fails")); c["runs"] = len(ms); c["margin"] = sum(m.get("margin", 0) for m in ms) / len(ms)
        c["paths"] = [p for p, _ in res[(r, j)]]; c["fails"] = [m.get("fails") for m in ms]
        c["pass"] = c["fail_runs"] == 0 and ctl[r]["fail_runs"] >= 2 and c["margin"] >= ctl[r]["margin"] - 0.02
        print("   ", c["src"], c["type"], c["fail_runs"], "/", c["runs"], f"m={c['margin']:.3f}", "PASS" if c["pass"] else "", (c.get("why") or "")[:80])
json.dump({"control": ctl, "cands": cands, "rejects": rejects}, open(D/"eval.json", "w"), indent=1)
