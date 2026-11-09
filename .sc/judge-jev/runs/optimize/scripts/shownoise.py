import json, lib
runs=json.load(open("noise.json")); base=json.load(open("baseline.json"))["base-greedy"]
for i in sorted(base):
    row=[base[i]]+[r[i] for r in runs]
    print(i, " ".join(f"{s['fails']}/{s['n']}:{s['margin']:.3f}" if 'error' not in s else "ERR" for s in row))
    for k,s in enumerate(row):
        for st in s.get('st',[]):
            if st['fired']: print("   run",k,"s",st['i'], st['fired'], {q:v for q,v in st['a'].items() if v[0] in (lib.R1.get(q,set())|lib.R2.get(q,set()))}, st['text'][:100].replace("\n"," "))
