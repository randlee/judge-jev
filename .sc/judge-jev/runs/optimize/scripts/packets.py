"""Write per-group proposer packets: python3 packets.py <iter> <state.json> <measurements.json...>"""
import json, sys, lib
from pathlib import Path
it = sys.argv[1]; state = json.load(open(sys.argv[2])); meas = [json.load(open(p)) for p in sys.argv[3:]]
orig = lib.load_records(lib.OPT/"orig-req")
GROUPS = {"A": ["NFR-JEV-0001"] + [f"REQ-JEV-000{i}" for i in range(1, 9)] + ["REQ-JEV-0101"],
          "B": [f"REQ-JEV-020{i}" for i in range(1, 9)],
          "C": ["REQ-JEV-0209"] + [f"REQ-JEV-02{i}" for i in range(10, 16)]}
out = lib.OPT/f"iter{it}/packets"; out.mkdir(parents=True, exist_ok=True)
for g, ids in GROUPS.items():
    lines = [f"# Packet group {g} (iteration {it})\n"]
    for rid in ids:
        lines.append(f"\n\n======== {rid} ========\n\n## CURRENT TEXT (tweak this; `old` must be a substring of it, whitespace-insensitive)\n\n```markdown\n{state[rid]}\n```\n")
        lines.append(f"\n## ORIGINAL TEXT before any Definitions paragraph (origin/docs/record-fixes), for reference only\n\n```markdown\n{orig[rid]}\n```\n")
        lines.append("\n## Jev answers on CURRENT TEXT, per statement, across repeated runs (choice @ confidence). FAIL marks a run where a verdict rule fired.\n")
        sts = {}
        for m in meas:
            s = m[rid]
            if "error" in s: continue
            for st in s["st"]:
                sts.setdefault(st["i"], {"text": st["text"], "runs": []})["runs"].append(st)
        for i in sorted(sts):
            lines.append(f"\n- s{i}: {sts[i]['text']!r}")
            for st in sts[i]["runs"]:
                a = "; ".join(f"{q}={c}@{p:.2f}" for q, (c, p) in st["a"].items())
                lines.append(f"\n    - {'FAIL '+'+'.join(st['fired']) if st['fired'] else 'pass'}: {a}")
        lines.append("\n")
    (out/f"group-{g}.md").write_text("".join(lines))
    print(g, len("".join(lines)))
