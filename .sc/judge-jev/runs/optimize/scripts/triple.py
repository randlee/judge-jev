"""usage: triple.py <prefix> <n> name=state.json ... : runs every state together n times -> <prefix>-<name>-k.json"""
import json, sys, lib
from concurrent.futures import ThreadPoolExecutor
pre, n = sys.argv[1], int(sys.argv[2]); S = dict(a.split("=") for a in sys.argv[3:]); S = {k: json.load(open(v)) for k, v in S.items()}
ids = sorted(next(iter(S.values())))
def one(a):
    name, k = a
    m = lib.judge_texts(lib.OPT/f"repos/{pre}-{name}-{k}", S[name], ids, f"{pre}-{name}-{k}")
    json.dump(m, open(lib.OPT/f"{pre}-{name}-{k}.json", "w"))
with ThreadPoolExecutor(6) as ex: list(ex.map(one, [(nm, k) for k in range(n) for nm in S]))
