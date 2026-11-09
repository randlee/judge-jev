"""Harness: record sections, variant repos, live Jev judging, scoring."""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

SP = Path("/private/tmp/claude-501/-Users-randlee-github-atm-core/2165a35b-650f-4075-81e0-940d0574bbfc/scratchpad")
O = SP / "dogfood-0.3.0"
OPT = O / "optimize"
WT = Path("/Users/randlee/github/judge-jev-worktrees/docs/record-terms")
JJPY = SP / "jjpy"
RQPY = SP / "rq-venv/bin/python"
EXTRACT = Path.home() / "github/raptor-worktrees/integration/judge-jev/scripts/extract.py"
JUDGE = O / "skill/scripts/jev_judge.py"
FILES = ["raptor-integration.md", "record-validation.md", "prose-evaluation.md"]
R1 = {"obligations": {"2", "3", "4+"}, "joined_by": {"and-list", "alternatives", "obligation+rationale"}}
R2 = {"term": {"project term defined nowhere", "vague qualifier", "undefined acronym"}, "check": {"needs a measure", "none"}}
HDR = re.compile(r"^## ((?:REQ|NFR)-JEV-\d{4}):", re.M)


def split_sections(text):
    """Return list of (rid or None, chunk) covering text exactly."""
    out = []; pos = 0
    starts = [m for m in re.finditer(r"^## ", text, re.M)]
    bounds = [m.start() for m in starts] + [len(text)]
    if bounds[0] > 0: out.append((None, text[:bounds[0]]))
    for i, b in enumerate(bounds[:-1]):
        chunk = text[b:bounds[i + 1]]
        m = HDR.match(chunk)
        out.append((m.group(1) if m else None, chunk))
    assert "".join(c for _, c in out) == text
    return out


def load_records(req_dir):
    recs = {}
    for f in FILES:
        for rid, chunk in split_sections(Path(req_dir, f).read_text()):
            if rid: recs[rid] = chunk
    return recs


def write_docs(req_dir_src, req_dir_dst, overrides):
    os.makedirs(req_dir_dst, exist_ok=True)
    seen = set()
    for f in FILES:
        parts = split_sections(Path(req_dir_src, f).read_text())
        new = []
        for rid, chunk in parts:
            if rid and rid in overrides:
                c = overrides[rid]; seen.add(rid)
                if not c.endswith("\n"): c += "\n"
                new.append(c)
            else:
                new.append(chunk)
        Path(req_dir_dst, f).write_text("".join(new))
    assert seen == set(overrides), set(overrides) - seen


def make_repo(dest, overrides, src_req=None):
    """Scratch repo = worktree docs/.raptor with records in overrides replaced."""
    dest = Path(dest)
    if dest.exists():  # never delete a run: archive it under a stable suffix
        k = 1
        while Path(f"{dest}.prev{k}").exists(): k += 1
        dest.rename(f"{dest}.prev{k}")
    shutil.copytree(WT / "docs", dest / "docs")
    shutil.copytree(WT / ".raptor", dest / ".raptor")
    subprocess.run(["git", "init", "-q", str(dest)], check=True)
    (dest / ".sc/judge-jev").mkdir(parents=True)
    (dest / ".sc/judge-jev/settings.yaml").write_text("schema_version: 1\nallow_remote_judge: true\n")
    write_docs(src_req or WT / "docs/requirements", dest / "docs/requirements", overrides)
    idx = dest / "index.json"
    p = subprocess.run([str(RQPY), str(EXTRACT), "--project-root", str(dest), "--output", str(idx)],
                       cwd=dest, capture_output=True, text=True)
    (dest / "extract.stdout").write_text(p.stdout); (dest / "extract.stderr").write_text(p.stderr)
    if p.returncode != 0:
        raise RuntimeError(f"extract failed {dest}: {p.stderr}")
    return idx


def judge(dest, ids, tag):
    dest = Path(dest); idx = dest / "index.json"
    args = []
    for i in ids: args += ["--" + i.split("-")[0].lower(), i]
    cmd = [str(JJPY), str(JUDGE), "quality", *args, "--index", str(idx), "--run-dir", str(dest / "runs" / tag),
           "--run-name", "opt-" + tag, "--repository-root", str(dest)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run(cmd, cwd=dest, capture_output=True, text=True, env=env)
    (dest / f"{tag}.json").write_text(p.stdout); (dest / f"{tag}.stderr.txt").write_text(p.stderr)
    (dest / f"{tag}.exit").write_text(str(p.returncode))
    try:
        d = json.loads(p.stdout)
    except Exception:
        return None, p.returncode, p.stderr
    return d, p.returncode, p.stderr


def margin(qid, choice, conf):
    bad = R1.get(qid) or R2.get(qid) or set()
    return 1 - conf if choice in bad else conf


def score_result(r):
    """r: one entry of data.results. Returns dict with fails, margin, statements."""
    sts = []
    for w in r.get("waves", []):
        for item in w.get("reason", []):
            s = item["statement"]; a = {x["id"]: (x["choice"], x["confidence"]) for x in item["answers"]}
            fired = []
            if all(a[k][0] in v for k, v in R1.items()): fired.append("R1")
            if any(a[k][0] in v for k, v in R2.items()): fired.append("R2")
            m = sum(margin(k, *a[k]) for k in a) / len(a)
            sts.append({"i": s["index"], "text": s["text"], "a": a, "fired": fired, "m": m})
    return {"fails": sum(1 for s in sts if s["fired"]), "margin": (sum(s["m"] for s in sts) / len(sts)) if sts else 0,
            "n": len(sts), "verdict": r.get("verdict"), "st": sts}


def results_by_id(d):
    out = {}
    if not d: return out
    for r in d.get("data", {}).get("results", []):
        out[r["record"]["id"]] = r
    return out


def judge_texts(dest, overrides, ids, tag, src_req=None, retry=True):
    """Build a repo with overrides, judge ids; rerun once on failure. Returns {id: score or error}."""
    make_repo(dest, overrides, src_req)
    d, rc, err = judge(dest, ids, tag)
    res = results_by_id(d)
    missing = [i for i in ids if i not in res or res[i].get("verdict") not in ("yes", "no")]
    if missing and retry:
        d2, rc2, err2 = judge(dest, missing, tag + "-retry")
        res.update(results_by_id(d2))
        err = err + "\n--retry--\n" + err2
    out = {}
    for i in ids:
        if i in res and res[i].get("verdict") in ("yes", "no"):
            out[i] = score_result(res[i])
        else:
            out[i] = {"error": (json.dumps(res.get(i))[:2000] if i in res else "") + "\nSTDERR:\n" + err[-3000:]}
    return out


DEF_RE = re.compile(r"(Definitions: )(.*?)(\n\n)", re.S)
SENT_SPLIT = re.compile(r"(?<=\.)\s+(?=[A-Za-z`])")


def def_sentences(section):
    m = DEF_RE.search(section)
    if not m: return None, []
    body = m.group(2)
    return m, [s for s in SENT_SPLIT.split(body.replace("\n", " ")) if s]


def without_sentence(section, k):
    m, sents = def_sentences(section)
    keep = [s for j, s in enumerate(sents) if j != k]
    if not keep:
        return section[:m.start()] + section[m.end():]  # drop whole paragraph incl. blank line
    import textwrap
    para = textwrap.fill("Definitions: " + " ".join(keep), 76, break_on_hyphens=False, break_long_words=False)
    return section[:m.start()] + para + "\n\n" + section[m.end():]


import textwrap as _tw


def loose_re(old):
    toks = old.split()
    return re.compile(r"\s+".join(re.escape(t) for t in toks)) if toks else None


def apply_tweak(section, old, new):
    """Whitespace-insensitive single replacement; returns new section or None."""
    rx = loose_re(old)
    if rx is None: return None
    ms = list(rx.finditer(section))
    if len(ms) != 1: return None
    m = ms[0]
    s = section[:m.start()] + new + section[m.end():]
    s = re.sub(r"Definitions: *\n\n", "", s)          # an emptied Definitions paragraph
    s = re.sub(r"Definitions:\s+(?=\S)", "Definitions: ", s)
    return reflow(s)


def _fill(text, first, rest):
    return _tw.fill(" ".join(text.split()), 76, initial_indent=first, subsequent_indent=rest,
                    break_on_hyphens=False, break_long_words=False)


def reflow(section):
    """Refill the Definitions paragraph, and any bullet or paragraph with a line over 80 chars,
    inside Requirement Statement and Rationale (never a paragraph quoting Rand)."""
    out = []
    in_body = False
    blocks = re.split(r"(\n\s*\n)", section)
    for b in blocks:
        if b.strip() == "" : out.append(b); continue
        if b.lstrip().startswith("### "):
            in_body = b.strip().startswith("### Requirement Statement") or b.strip().startswith("### Rationale")
            # heading block may also hold content after the heading line
        if not in_body or "Rand" in b or b.lstrip().startswith("#") or b.lstrip().startswith("**"):
            # keep headings/labels; but a block could be "**MUST statements:**\n- ..." list
            if b.lstrip().startswith("**") and "\n- " in b and in_body:
                head, rest = b.split("\n", 1)
                out.append(head + "\n" + _reflow_list(rest)); continue
            out.append(b); continue
        if b.startswith("Definitions:"):
            out.append(_fill(b, "", "")); continue
        if b.lstrip().startswith("- "):
            out.append(_reflow_list(b)); continue
        if any(len(l) > 80 for l in b.split("\n")):
            out.append(_fill(b, "", "")); continue
        out.append(b)
    return "".join(out)


def _reflow_list(b):
    items = re.split(r"\n(?=- )", b)
    res = []
    for it in items:
        if any(len(l) > 80 for l in it.split("\n")):
            res.append(_fill(it[2:], "- ", "  "))
        else:
            res.append(it)
    return "\n".join(res)


def rand_quotes(section):
    return [" ".join(q.split()) for q in re.findall(r'"([^"]{12,})"', section)]


def quotes_ok(orig_section, new_section):
    n = " ".join(new_section.split())
    return all(q in n for q in rand_quotes(orig_section))


def statements_block(section):
    m = re.search(r"\*\*MUST statements:\*\*(.*?)(?=\n### )", section, re.S)
    return m.group(1) if m else ""


def obligation_tokens(section):
    b = statements_block(section)
    toks = set(re.findall(r"`[^`]+`", b)) | set(re.findall(r"\b(?:REQ|NFR|ADR)-JEV-\d{4}\b", b)) \
        | set(re.findall(r"(?<![\w.-])\d+(?:\.\d+)?(?![\w.-])", b))
    return toks, len(re.findall(r"\bMUST\b", b))


def obligation_guard(before, after):
    """None if every code span, number and record id of the statements survives and no MUST is dropped."""
    tb, nb = obligation_tokens(before); ta, na = obligation_tokens(after)
    lost = tb - ta
    if lost: return f"statement tokens lost: {sorted(lost)}"
    if na < nb: return f"MUST count fell {nb}->{na}"
    return None


def merge_definitions(section):
    paras = re.findall(r"Definitions: .*?(?=\n\n)", section, re.S)
    if len(paras) <= 1: return section
    sents = []
    for p in paras:
        for s in SENT_SPLIT.split(" ".join(p[len("Definitions: "):].split())):
            if s and s not in sents: sents.append(s)
    first = section.index(paras[0])
    for p in paras: section = section.replace(p + "\n\n", "", 1)
    return section[:first] + "Definitions: " + " ".join(sents) + "\n\n" + section[first:]


_apply_raw = apply_tweak
def apply_tweak(section, old, new):
    s = _apply_raw(section, old, new)
    if s is None: return None
    m = re.search(r"### Requirement Statement.*?(?=\n### )", s, re.S)  # tidy only the statement block
    if m:
        blk = m.group(0)
        blk = re.sub(r"[ ]+([,.;:)])", r"\1", blk)
        blk = re.sub(r",([.;:])", r"\1", blk)
        blk = re.sub(r"(?<=\S) {2,}(?=\S)", " ", blk)
        blk = re.sub(r"\(\s*\)", "", blk)
        s = s[:m.start()] + blk + s[m.end():]
    return reflow(merge_definitions(s))


def is_removal(c):
    return c.get("type") == "remove" or (c.get("type") == "reword" and "shortening" in (c.get("why") or "")
                                         and len(" ".join((c.get("new") or "").split())) < len(" ".join((c.get("old") or "").split())))


def obligation_guard_section(before, after):
    def blk(s):
        m = re.search(r"### Requirement Statement(.*?)(?=\n### )", s, re.S); return m.group(1) if m else ""
    tok = lambda b: set(re.findall(r"`[^`]+`", b)) | set(re.findall(r"\b(?:REQ|NFR|ADR)-JEV-\d{4}\b", b)) | set(re.findall(r"(?<![\w.-])\d+(?:\.\d+)?(?![\w.-])", b))
    lost = tok(blk(before)) - tok(blk(after))
    if lost: return f"section tokens lost: {sorted(lost)}"
    if len(re.findall(r"\bMUST\b", statements_block(after))) < len(re.findall(r"\bMUST\b", statements_block(before))): return "MUST count fell"
    return None
