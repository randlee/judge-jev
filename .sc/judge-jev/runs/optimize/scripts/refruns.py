"""usage: refruns.py <state.json> <prefix> <start> <count> : measure the whole state count times -> <prefix>-<k>.json"""
import json, sys, lib
from concurrent.futures import ThreadPoolExecutor
st = json.load(open(sys.argv[1])); pre = sys.argv[2]; a = int(sys.argv[3]); n = int(sys.argv[4]); ids = sorted(st)
def one(k):
    m = lib.judge_texts(lib.OPT/f"repos/{pre}-{k}", st, ids, f"{pre}-{k}"); json.dump(m, open(lib.OPT/f"{pre}-{k}.json", "w"))
with ThreadPoolExecutor(4) as ex: list(ex.map(one, range(a, a + n)))
