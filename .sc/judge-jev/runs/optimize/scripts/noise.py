import json, lib
from concurrent.futures import ThreadPoolExecutor
g = lib.load_records(lib.WT/"docs/requirements"); ids = sorted(g)
runs = list(ThreadPoolExecutor(2).map(lambda n: lib.judge_texts(lib.OPT/f"repos/noise{n}", g, ids, f"noise{n}"), [1,2]))
base = json.load(open("baseline.json"))["base-greedy"]
json.dump(runs, open("noise.json","w"), indent=1)
for i in ids:
    row=[base[i]]+runs
    print(i, " ".join(f"{s['fails']}/{s['n']}:{s['margin']:.3f}" if 'error' not in s else "ERR" for s in row))
    for s in row:
        for st in s.get('st',[]):
            if st['fired']: print("   ", st['i'], st['fired'], {k:v for k,v in st['a'].items() if v[0] in (lib.R1.get(k,set())|lib.R2.get(k,set()))}, st['text'][:90].replace("\n"," "))
