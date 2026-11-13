"""Evaluate candidate tweaks for one iteration.
usage: eval_iter.py <iter> <state.json> <refmeas.json,...>   (ref measurements of the state, comma-separated)
Candidates: mechanical removal of each Definitions sentence + iter<N>/props/*.json.
Stage M1: each candidate alone (one slot per candidate index, all records in parallel).
Stage M2: re-measure M1 survivors. Writes iter<N>/eval.json."""
import json, sys, glob, hashlib, lib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
it = sys.argv[1]; state = json.load(open(sys.argv[2])); refs = [json.load(open(p)) for p in sys.argv[3].split(",")]
ONLY = os.environ.get("ONLY"); TAG = os.environ.get("TAG", "")
if ONLY: state = {k: v for k, v in state.items() if k in ONLY.split(",")}
D = lib.OPT/f"iter{it}"; D.mkdir(exist_ok=True)
orig = lib.load_records(lib.OPT/"orig-req")
AUTHOR_REJECT = json.load(open(D/"author_reject.json")) if (D/"author_reject.json").exists() else {}
ADD = {"define", "cite", "measure", "threshold", "split", "move-rationale", "reword"}

def ref(rid):
    f = [r[rid]["fails"] for r in refs if "error" not in r[rid]]
    m = [r[rid]["margin"] for r in refs if "error" not in r[rid]]
    return min(f), sum(f)/len(f), sum(m)/len(m)

cands = {rid: [] for rid in state}; seen = {rid: {hashlib.sha1(state[rid].encode()).hexdigest()} for rid in state}
rejects = []
def add(rid, c, text):
    h = hashlib.sha1(text.encode()).hexdigest()
    if h in seen[rid]: rejects.append({**c, "reject": "duplicate or no-op"}); return
    if not lib.quotes_ok(orig[rid], text): rejects.append({**c, "reject": "touches a Rand quote"}); return
    g = lib.obligation_guard(state[rid], text)
    if g: rejects.append({**c, "reject": "obligation guard: " + g}); return
    seen[rid].add(h); c["text"] = text; cands[rid].append(c)
for rid, s in state.items():
    m, sents = lib.def_sentences(s)
    for k, sent in enumerate(sents):
        add(rid, {"rid": rid, "type": "remove", "src": "mechanical", "target": "defs", "old": sent, "new": "", "why": f"drop definition sentence {k}"}, lib.without_sentence(s, k))
for p in sorted(glob.glob(str(D/"props/*.json"))):
    src = Path(p).stem
    try: props = json.load(open(p))
    except Exception as e: rejects.append({"src": src, "reject": f"bad json {e}"}); continue
    for c in props:
        rid = c.get("rid")
        if ONLY and rid not in ONLY.split(","): continue
        if rid not in state: rejects.append({**c, "src": src, "reject": "unknown rid"}); continue
        t = lib.apply_tweak(state[rid], c.get("old", ""), c.get("new", ""))
        c = {**c, "src": src}
        _n = lambda z: " ".join((z or "").split())
        if any(_n(x) in _n(c.get("old")) and _n(x) not in _n(c.get("new")) for x in AUTHOR_REJECT.get(rid, [])):
            rejects.append({**c, "reject": "author: drops a defined meaning"}); continue
        if t is None: rejects.append({**c, "reject": "old not found exactly once"}); continue
        add(rid, c, t)

def run_slots(tag, slotmap):
    """slotmap: list of {rid: cand}; returns list of {rid: score}"""
    def one(j):
        ov = {rid: c["text"] for rid, c in slotmap[j].items()}
        return lib.judge_texts(lib.OPT/f"repos/i{it}{TAG}-{tag}-{j}", ov, sorted(ov), f"i{it}{TAG}-{tag}-{j}")
    with ThreadPoolExecutor(4) as ex: return list(ex.map(one, range(len(slotmap))))

def slots_of(cl):
    n = max((len(v) for v in cl.values()), default=0)
    return [{rid: v[j] for rid, v in cl.items() if j < len(v)} for j in range(n)]

def passes(c, s, stage):
    if "error" in s: return False
    fmin, fmean, mm = ref(c["rid"])
    if lib.is_removal(c): return s["fails"] <= fmin
    return s["fails"] < fmean and s["fails"] <= fmin if fmean > 0 else False

print("candidates", sum(len(v) for v in cands.values()), "rejected", len(rejects), flush=True)
sl = slots_of(cands); res = run_slots("m1", sl)
for j, slot in enumerate(sl):
    for rid, c in slot.items(): c["m1"] = {k: v for k, v in res[j][rid].items()}; c.setdefault("runs", {})["m1"] = f"repos/i{it}{TAG}-m1-{j}/i{it}{TAG}-m1-{j}"
surv = {rid: [c for c in v if passes(c, c["m1"], 1)] for rid, v in cands.items()}
print("M1 survivors", sum(len(v) for v in surv.values()), flush=True)
sl2 = slots_of(surv); res2 = run_slots("m2", sl2)
for j, slot in enumerate(sl2):
    for rid, c in slot.items(): c["m2"] = res2[j][rid]; c["kept"] = passes(c, c["m2"], 2); c.setdefault("runs", {})["m2"] = f"repos/i{it}{TAG}-m2-{j}/i{it}{TAG}-m2-{j}"
for rid in cands:
    fmin, fmean, mm = ref(rid)
    for c in cands[rid]:
        c["ref"] = {"fails_min": fmin, "fails_mean": fmean, "margin_mean": mm}
        c.setdefault("kept", False)
json.dump({"cands": cands, "rejects": rejects}, open(D/f"eval{TAG}.json", "w"), indent=1)
for rid in sorted(cands):
    fmin, fmean, mm = ref(rid)
    k = [c for c in cands[rid] if c["kept"]]
    print(rid, f"ref f={fmean:.2f} m={mm:.3f}", "cands", len(cands[rid]), "kept", len(k))
    for c in k:
        f = lambda s: f"{s['fails']}:{s['margin']:.3f}"
        print("   ", c["type"], c["src"], f(c["m1"]), f(c["m2"]), (c.get("why") or "")[:90])
