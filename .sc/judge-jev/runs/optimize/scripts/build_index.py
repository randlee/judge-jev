"""Build runs-index.jsonl: one row per (run, record) for every Jev run kept under repos/."""
import json, re
from pathlib import Path
import lib

OPT = lib.OPT; FINAL = json.load(open(OPT / "state-final3.json"))

def in_final(c):
    t = FINAL[c["rid"]]
    new_ok = (not c["new"]) or re.search(lib.loose_re(c["new"]), t) is not None
    old_gone = bool(c["new"]) and c["old"] in c["new"] or re.search(lib.loose_re(c["old"]), t) is None
    return bool(new_ok and old_gone)

cmap = {}   # (path, rid) -> (iteration, stage, tweak)
tweaks = []
def reg(it, c, k, paths):
    tid = f"i{it}-{c['rid']}-{c.get('src','?')}-{c['type']}-{c.get('target','?')}-{k}"
    tw = {"tweak_id": tid, "iteration": it, "record": c["rid"], "src": c.get("src"), "type": c["type"],
          "target": c.get("target"), "old": c["old"], "new": c["new"], "why": c.get("why"),
          "passed_iteration": c.get("kept", c.get("pass")), "in_final_text": in_final(c)}
    tweaks.append(tw)
    for stage, p in paths:
        cmap[(p, c["rid"])] = (it, stage, tw)

for it in (1, 2, 3):
    for name in ("eval.json", "evalx.json"):
        f = OPT / f"iter{it}" / name
        if not f.exists(): continue
        for rid, cs in json.load(open(f))["cands"].items():
            for k, c in enumerate(cs):
                ps = []
                for stage, v in (c.get("runs") or {}).items():
                    for p in (v if isinstance(v, list) else [v]): ps.append((stage, p))
                reg(it, c, f"{name[:-5]}{k}", ps)
e4 = json.load(open(OPT / "iter4/eval.json")); cf = json.load(open(OPT / "iter4/confirm.json"))
for rid, cs in e4["cands"].items():
    for k, c in enumerate(cs):
        ps = [("i4-eval", p) for p in c.get("paths", [])]
        conf = next((x for x in cf.get(rid, {}).get("cands", []) if x["old"] == c["old"] and x["new"] == c["new"]), None)
        if conf: ps += [("i4-confirm", p) for p in conf.get("paths", conf.get("confirm_paths", []))]
        reg(4, c, f"eval{k}", ps)

def label(tag):
    m = re.match(r"i(\d)", tag)
    it = int(m.group(1)) if m else 0
    if re.match(r"fin\d*-", tag): return it, "final-triplet"
    if tag.startswith("pair"): return it, "paired-selection"
    for pat, st in [("base-", "baseline"), ("noise", "noise"), ("ref", "reference"), ("-ctl-", "control"),
                    ("-comb-", "combination"), ("-greedy", "combination-greedy"), ("-backoff-", "backoff"),
                    ("-final-", "combination-final"), ("pair", "paired-selection"), ("fin", "final-triplet"),
                    ("-ref-", "reference")]:
        if pat in tag: return it, st
    return it, "candidate-slot"

rows = []; req_total = 0; req_by_stage = {}
for d in sorted((OPT / "repos").iterdir()):
    for j in sorted(d.glob("*.json")):
        if j.name == "index.json": continue
        tag = j.stem; path = f"repos/{d.name}/{tag}"
        log = d / "runs" / tag / "logs" / "judge-jev.log.jsonl"
        nreq = sum(1 for l in log.open() if '"action":"request"' in l.replace(" ", "")) if log.exists() else 0
        req_total += nreq
        exitf = d / f"{tag}.exit"
        try: data = json.loads(j.read_text())
        except Exception: data = None
        res = lib.results_by_id(data)
        it, st = label(tag); req_by_stage[st] = req_by_stage.get(st, 0) + nreq
        base = {"run": path, "exit": exitf.read_text().strip() if exitf.exists() else None,
                "stderr": f"repos/{d.name}/{tag}.stderr.txt", "run_dir": f"repos/{d.name}/runs/{tag}", "jev_requests": nreq}
        if not res:
            rows.append({**base, "record": None, "iteration": it, "stage": st, "error": "no parseable results"}); continue
        for rid, r in res.items():
            s = lib.score_result(r)
            row = {**base, "record": rid, "iteration": it, "stage": st, "fails": s["fails"], "margin": round(s["margin"], 4),
                   "verdict": s["verdict"], "fired": [f"s{x['i']}:{'+'.join(x['fired'])}" for x in s["st"] if x["fired"]]}
            m = cmap.get((path, rid)) or cmap.get((path.replace("-retry", ""), rid))
            if m:
                row.update(iteration=m[0], stage=m[1], tweak_id=m[2]["tweak_id"], tweak_old=m[2]["old"], tweak_new=m[2]["new"],
                           kept=m[2]["in_final_text"])
            rows.append(row)

with open(OPT / "runs-index.jsonl", "w") as f:
    for r in rows: f.write(json.dumps(r) + "\n")
with open(OPT / "tweaks-index.jsonl", "w") as f:
    for t in tweaks: f.write(json.dumps(t) + "\n")
json.dump({"jev_requests_total": req_total, "by_stage": req_by_stage, "run_files": len({r["run"] for r in rows}),
           "rows": len(rows), "tweaks": len(tweaks), "tweaks_in_final": sum(t["in_final_text"] for t in tweaks)},
          open(OPT / "runs-summary.json", "w"), indent=1)
print(open(OPT / "runs-summary.json").read())
