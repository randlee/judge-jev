"""usage: paired.py <stateA> <stateB> <prefix> <n> : n paired runs, A and B launched together -> <prefix>-A-k / -B-k"""
import json, sys, lib
from concurrent.futures import ThreadPoolExecutor
A = json.load(open(sys.argv[1])); B = json.load(open(sys.argv[2])); pre = sys.argv[3]; n = int(sys.argv[4])
ids = sorted(A)
def one(a):
    side, k = a; st = A if side == "A" else B
    m = lib.judge_texts(lib.OPT/f"repos/{pre}-{side}-{k}", st, ids, f"{pre}-{side}-{k}")
    json.dump(m, open(lib.OPT/f"{pre}-{side}-{k}.json", "w")); return side, k, m
jobs = [(s, k) for k in range(n) for s in "AB"]
with ThreadPoolExecutor(4) as ex: R = list(ex.map(one, jobs))
for rid in ids:
    fa = [m[rid].get("fails") for s, k, m in R if s == "A"]; fb = [m[rid].get("fails") for s, k, m in R if s == "B"]
    ma = sum(m[rid].get("margin", 0) for s, k, m in R if s == "A") / n; mb = sum(m[rid].get("margin", 0) for s, k, m in R if s == "B") / n
    ra = sum(1 for x in fa if x); rb = sum(1 for x in fb if x)
    print(rid, "A", fa, f"{ma:.3f}", "B", fb, f"{mb:.3f}", "B WORSE" if rb > ra else ("B better" if rb < ra else ""), "(same text)" if A[rid] == B[rid] else "")
