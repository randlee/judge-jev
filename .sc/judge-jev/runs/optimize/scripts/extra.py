"""Extra measurements: usage extra.py <iter> <state.json> <refprefix> <nref> <nextra>
Writes <refprefix>-{3..} reference runs of state, and m3..m(2+nextra) for kept additive tweaks.
Additive kept only if its failing-run rate over all its runs <= half the reference failing-run rate."""
import json, sys, lib
from concurrent.futures import ThreadPoolExecutor
it, sp, rp, nref, nx = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
state = json.load(open(sp)); D = lib.OPT/f"iter{it}"; E = json.load(open(D/"eval.json")); cands = E["cands"]
ids = sorted(state)
def refrun(k):
    m = lib.judge_texts(lib.OPT/f"repos/{rp}-{k}", state, ids, f"{rp}-{k}")
    json.dump(m, open(lib.OPT/f"{rp}-{k}.json", "w")); return m
add = {rid: [c for c in v if c["kept"] and not lib.is_removal(c)] for rid, v in cands.items()}
slots = [{rid: v[j] for rid, v in add.items() if j < len(v)} for j in range(max(len(v) for v in add.values()))]
def tw(args):
    j, k = args; ov = {rid: c["text"] for rid, c in slots[j].items()}
    return j, k, lib.judge_texts(lib.OPT/f"repos/i{it}-m{k}-{j}", ov, sorted(ov), f"i{it}-m{k}-{j}")
jobs = [(j, k) for j in range(len(slots)) for k in range(3, 3 + nx)]
with ThreadPoolExecutor(4) as ex:
    import glob as _g
    have = len(_g.glob(str(lib.OPT/f"{rp}-*.json")))
    refs = list(ex.map(refrun, range(have, have + nref)))
    for j, k, res in ex.map(tw, jobs):
        for rid, c in slots[j].items(): c[f"m{k}"] = res[rid]; c.setdefault("runs", {})[f"m{k}"] = f"repos/i{it}-m{k}-{j}/i{it}-m{k}-{j}"
import glob as _g
allref = [json.load(open(p)) for p in sorted(_g.glob(str(lib.OPT/f"{rp}-*.json")))]
for rid, v in add.items():
    rr = [r[rid]["fails"] > 0 for r in allref if "error" not in r[rid]]
    rate = sum(rr) / len(rr)
    for c in v:
        runs = [c[f"m{k}"] for k in range(1, 3 + nx) if f"m{k}" in c]
        tr = [s["fails"] > 0 for s in runs if "error" not in s]
        c["ref_fail_rate"] = rate; c["fail_rate"] = sum(tr) / len(tr)
        c["kept"] = c["fail_rate"] <= rate / 2 and len(tr) >= 2 + nx
        print(rid, c["src"], c["type"], c.get("target"), f"ref {rate:.2f} tweak {c['fail_rate']:.2f}", "KEPT" if c["kept"] else "drop", (c.get("why") or "")[:70])
json.dump(E, open(D/"eval.json", "w"), indent=1)
