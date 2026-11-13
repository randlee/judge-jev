import json, sys, lib
from concurrent.futures import ThreadPoolExecutor
orig = lib.load_records(lib.OPT/"orig-req"); greedy = lib.load_records(lib.WT/"docs/requirements")
ids = sorted(greedy)
def run(name, recs):
    return name, lib.judge_texts(lib.OPT/f"repos/{name}", recs, ids, name)
with ThreadPoolExecutor(2) as ex:
    out = dict(ex.map(lambda a: run(*a), [("base-orig", orig), ("base-greedy", greedy)]))
json.dump(out, open(lib.OPT/"baseline.json","w"), indent=1)
for i in ids:
    o, g = out["base-orig"][i], out["base-greedy"][i]
    f = lambda s: "ERR" if "error" in s else f"{s['fails']}/{s['n']} m={s['margin']:.3f}"
    print(i, "orig", f(o), "| greedy", f(g))
