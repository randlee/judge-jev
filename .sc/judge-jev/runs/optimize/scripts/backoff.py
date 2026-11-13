"""usage: backoff.py <iter> <prev_state> <cur_state> <runs> <rid,...>
For each rid: variants = cur minus one used tweak (rebuilt from prev). Measure each <runs> times.
Best variant with zero failing runs (highest margin) replaces cur; else rid reverts to prev. Writes iter<N>/backoff.json and updates cur_state in place."""
import json, sys, lib
from concurrent.futures import ThreadPoolExecutor
it, pp, cp, runs, rids = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5].split(",")
prev = json.load(open(pp)); cur = json.load(open(cp)); D = lib.OPT/f"iter{it}"
used = json.load(open(D/"combine.json"))["used"]
def build(rid, tw):
    t = prev[rid]
    for c in tw:
        n = lib.apply_tweak(t, c["old"], c["new"])
        if n is not None: t = n
    return t
var = {rid: [(j, build(rid, [c for i, c in enumerate(used[rid]) if i != j])) for j in range(len(used[rid]))] for rid in rids}
slots = [{rid: v[j] for rid, v in var.items() if j < len(v)} for j in range(max(len(v) for v in var.values()))]
jobs = [(j, k) for j in range(len(slots)) for k in range(runs)]
def one(a):
    j, k = a; ov = {rid: t for rid, (_, t) in slots[j].items()}
    return j, k, lib.judge_texts(lib.OPT/f"repos/i{it}-backoff-{j}-{k}", ov, sorted(ov), f"i{it}-backoff-{j}-{k}")
res = {}
with ThreadPoolExecutor(4) as ex:
    for j, k, r in ex.map(one, jobs):
        for rid in slots[j]: res.setdefault(rid, {}).setdefault(j, []).append(r[rid])
out = {}
for rid in rids:
    rows = []
    for j, ms in sorted(res[rid].items()):
        fr = sum(m.get("fails", 9) > 0 for m in ms); mg = sum(m.get("margin", 0) for m in ms) / len(ms)
        rows.append({"dropped_tweak": {k: v for k, v in used[rid][j].items() if k != "text"}, "failing_runs": fr, "runs": len(ms), "margin": mg, "fails": [m.get("fails") for m in ms]})
        print(rid, "minus", j, used[rid][j]["old"][:60].replace("\n", " "), "fails", [m.get("fails") for m in ms], f"m={mg:.3f}")
    ok = [r for r in rows if r["failing_runs"] == 0]
    if ok:
        best = max(ok, key=lambda r: r["margin"]); j = rows.index(best)
        cur[rid] = var[rid][j][1]; used[rid] = [c for i, c in enumerate(used[rid]) if i != j]; out[rid] = {"choice": "dropped one tweak", "rows": rows, "dropped": j}
    else:
        cur[rid] = prev[rid]; used[rid] = []; out[rid] = {"choice": "reverted to previous state", "rows": rows}
    print(rid, "->", out[rid]["choice"])
c = json.load(open(D/"combine.json")); c["used"] = used; c.setdefault("backoff", {}).update(out)
json.dump(c, open(D/"combine.json", "w"), indent=1); json.dump(cur, open(cp, "w"), indent=1)
