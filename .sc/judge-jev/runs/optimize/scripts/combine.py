"""Combine kept tweaks per record and resolve interactions.
usage: combine.py <iter> <state.json> <refmeas,...>  -> state<iter>.json, meas<iter>-{0,1}.json, iter<N>/combine.json"""
import json, sys, lib
from concurrent.futures import ThreadPoolExecutor
it = sys.argv[1]; state = json.load(open(sys.argv[2])); refs = [json.load(open(p)) for p in sys.argv[3].split(",")]
D = lib.OPT/f"iter{it}"; ev = json.load(open(D/"eval.json"))["cands"]
def ref(rid):
    f = [r[rid]["fails"] for r in refs if "error" not in r[rid]]
    m = [r[rid]["margin"] for r in refs if "error" not in r[rid]]
    return min(f), sum(f)/len(f), sum(m)/len(m)
def order(c):
    add = not lib.is_removal(c)
    runs = [c[k] for k in c if _re.fullmatch(r"m\d+", k) and "error" not in c[k]] if "_re" in globals() else [c["m1"], c["m2"]]
    return (0 if add else 1, c.get("fail_rate", 0), -sum(r["margin"] for r in runs) / len(runs))
kept = {rid: sorted([c for c in v if c["kept"]], key=order) for rid, v in ev.items()}
import re as _re
failing = {rid: sorted({st["i"] for r in refs if "error" not in r[rid] for st in r[rid]["st"] if st["fired"]}) for rid in state}
def targets_failing(c):
    fs = failing[c["rid"]]
    t = str(c.get("target", "")); w = c.get("why") or ""
    ids = {int(x) for x in _re.findall(r"\bs(\d+)\b", t + " " + (w if t == "defs" else ""))}
    return bool(ids & set(fs))
for rid, ks in kept.items():
    for c in ks:
        if not lib.is_removal(c) and not targets_failing(c): c["kept"] = False; c["drop_reason"] = "targets no failing statement (same-side move only)"
    kept[rid] = [c for c in ks if c["kept"]]
for rid, ks in kept.items():  # at most one additive tweak per target statement: the best measured
    seen_t = set(); out = []
    for c in ks:
        if not lib.is_removal(c):
            if c.get("target") in seen_t: continue
            seen_t.add(c.get("target"))
        out.append(c)
    kept[rid] = out
log = {}
def build(rid, tweaks):
    t = state[rid]; used = []
    for c in tweaks:
        n = lib.apply_tweak(t, c["old"], c["new"])
        if n is None or n == t: continue
        t = n; used.append(c)
    return t, used
def measure(texts, tag, n=2):
    ids = sorted(texts)
    if not ids: return [{} for _ in range(n)]
    with ThreadPoolExecutor(n) as ex:
        return list(ex.map(lambda k: lib.judge_texts(lib.OPT/f"repos/i{it}-{tag}-{k}", texts, ids, f"i{it}-{tag}-{k}"), range(n)))
def ok(rid, scores, used):
    fmin, fmean, _ = ref(rid)
    if any("error" in s for s in scores): return False
    f = [s["fails"] for s in scores]
    if any(x > fmin for x in f): return False
    if any(not lib.is_removal(c) for c in used) and fmean > 0 and not (sum(f)/len(f) < fmean): return False
    return True
cand = {}; usedmap = {}
for rid, ks in kept.items():
    if ks: cand[rid], usedmap[rid] = build(rid, ks)
ms = measure(cand, "comb")
final = dict(state); finalused = {rid: [] for rid in state}; bad = []
for rid in cand:
    if ok(rid, [m[rid] for m in ms], usedmap[rid]):
        final[rid] = cand[rid]; finalused[rid] = usedmap[rid]; log[rid] = "combined ok"
    else: bad.append(rid); log[rid] = "combined failed: " + str([m[rid].get("fails") for m in ms])
# greedy resolution for records whose combination failed: add tweaks one at a time
prefix = {rid: [] for rid in bad}
step = 0
while True:
    texts = {}; trial = {}
    for rid in bad:
        rest = [c for c in kept[rid] if c not in prefix[rid] and not c.get("_dropped")]
        if not rest: continue
        trial[rid] = rest[0]; t, u = build(rid, prefix[rid] + [rest[0]]); texts[rid] = t
    if not texts: break
    m = measure(texts, f"greedy{step}")
    for rid, c in trial.items():
        if ok(rid, [x[rid] for x in m], prefix[rid] + [c]): prefix[rid].append(c)
        else: c["_dropped"] = True
    step += 1
for rid in bad:
    if prefix[rid]:
        final[rid], finalused[rid] = build(rid, prefix[rid]); log[rid] += f" -> greedy kept {len(finalused[rid])}/{len(kept[rid])}"
# final double measurement of the whole new state (all records)
fm = measure(final, "final")
for k, m in enumerate(fm): json.dump(m, open(lib.OPT/f"meas{it}-{k}.json", "w"))
json.dump(final, open(lib.OPT/f"state{it}.json", "w"), indent=1)
json.dump({"failing": failing, "dropped_additive": {r: [{k: v for k, v in c.items() if k != "text"} for c in ev[r] if c.get("drop_reason")] for r in ev}, "log": log, "used": {r: [{k: v for k, v in c.items() if k != "text"} for c in u] for r, u in finalused.items()}}, open(D/"combine.json", "w"), indent=1)
for rid in sorted(state):
    fmin, fmean, mm = ref(rid)
    print(rid, f"ref f={fmean:.2f} m={mm:.3f}", "final", [ (m[rid].get('fails'), round(m[rid].get('margin',0),3)) for m in fm], len(finalused[rid]), "tweaks", log.get(rid, ""))
