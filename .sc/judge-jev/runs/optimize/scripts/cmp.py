import json, sys
def load(pre, n): return [json.load(open(f"{pre}-{k}.json")) for k in range(n)]
A = load(sys.argv[1], int(sys.argv[2])); B = load(sys.argv[3], int(sys.argv[4]))
for rid in sorted(A[0]):
    fa = [r[rid]["fails"] for r in A]; fb = [r[rid]["fails"] for r in B]
    ma = sum(r[rid]["margin"] for r in A)/len(A); mb = sum(r[rid]["margin"] for r in B)/len(B)
    ra = sum(x > 0 for x in fa)/len(fa); rb = sum(x > 0 for x in fb)/len(fb)
    flag = "WORSE" if rb > ra else ("better" if rb < ra else "")
    print(f"{rid} {sys.argv[1]} {fa} m={ma:.3f} | {sys.argv[3]} {fb} m={mb:.3f} {flag}")
