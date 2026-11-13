import json, lib
from concurrent.futures import ThreadPoolExecutor
st = json.load(open("state-final.json")); e = json.load(open("iter4/eval.json")); N = 12
pick = {"REQ-JEV-0210": [0, 12, 7], "REQ-JEV-0208": [1, 0]}
C = {r: [e["cands"][r][j] for j in js] for r, js in pick.items()}
for r in e["rejects"]:
    if r["rid"] == "REQ-JEV-0208" and r["src"] == "sonnet-G" and any(x in r["new"] for x in ("with no Jev call", "zero Jev calls", "makes no Jev call")):
        t = lib.apply_tweak(st["REQ-JEV-0208"], r["old"], r["new"]); C["REQ-JEV-0208"].append(r | {"text": t, "readmitted": "keeps the no-call meaning; earlier regex too narrow"})
n = max(len(v) for v in C.values())
slots = [{r: v[j]["text"] for r, v in C.items() if j < len(v)} for j in range(n)] + [{r: st[r] for r in C}]
def one(a):
    j, k = a; name = "ctl" if j == n else f"c{j}"
    return j, k, f"repos/i4conf-{name}-{k}/i4conf-{name}-{k}", lib.judge_texts(lib.OPT/f"repos/i4conf-{name}-{k}", slots[j], sorted(slots[j]), f"i4conf-{name}-{k}")
res = {}
with ThreadPoolExecutor(6) as ex:
    for j, k, p, m in ex.map(one, [(j, k) for k in range(N) for j in range(n + 1)]):
        for r in slots[j]: res.setdefault((r, j), []).append((p, m[r]))
out = {}
for r in C:
    ctl = [m for _, m in res[(r, n)]]
    cf = sum(1 for m in ctl if m.get("fails")); cm = sum(m["margin"] for m in ctl) / N
    print(r, "CONTROL", cf, f"m={cm:.3f}"); out[r] = {"control": {"fail_runs": cf, "margin": cm, "paths": [p for p, _ in res[(r, n)]]}, "cands": []}
    for j, c in enumerate(C[r]):
        ms = [m for _, m in res[(r, j)]]; f = sum(1 for m in ms if m.get("fails")); mg = sum(m["margin"] for m in ms) / N
        prev = c.get("fail_runs")
        print("   ", j, c["src"], c["type"], f, f"m={mg:.3f}", "(iter4 first round:", prev, ")", c["new"][:70].replace("\n", " "))
        out[r]["cands"].append({k: v for k, v in c.items() if k not in ("paths",)} | {"confirm_fail_runs": f, "confirm_margin": mg, "confirm_paths": [p for p, _ in res[(r, j)]], "confirm_fails": [m.get("fails") for m in ms]})
json.dump(out, open("iter4/confirm.json", "w"), indent=1)
