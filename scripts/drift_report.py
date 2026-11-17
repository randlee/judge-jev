#!/usr/bin/env python3
"""Render a judge-jev drift report: one HTML page, one XHTML panel per run and one JSON sidecar.

Each run is the JSON output of `jev_judge.py drift` (optionally with the same run's `--dry-run` output, for request
sizes). Panels render from site/examples/templates/drift-form.xhtml.j2 and the page from drift-report.html.j2, both
through `sc-compose render`; this script only prepares variables. With exactly two runs it adds a verdict cross-tab.

    python3 scripts/drift_report.py --run diff=result-diff.json:dry-diff.json --run full=result-full.json:dry-full.json \
        --title "..." --output site/examples/drift-example.html [--intro-html f] [--notes-html f] [--meta key=value]...
"""
import argparse
import datetime
import json
import pathlib
import shutil
import statistics
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "site" / "examples" / "templates"
VERDICTS = ("no-drift", "drift", "uncertain")
SCHEMA = "judge-jev/drift-report/1"


def render(template: pathlib.Path, variables: dict, output: pathlib.Path) -> str:
    binary = shutil.which("sc-compose")
    if binary is None:
        sys.exit("sc-compose is required on PATH")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(variables, f, ensure_ascii=False)
        var_file = f.name
    proc = subprocess.run([binary, "render", "--root", str(template.parent), "--strict", "--file", str(template),
                           "--var-file", var_file, "--output", str(output)], capture_output=True, text=True)
    pathlib.Path(var_file).unlink()
    if proc.returncode != 0:
        sys.exit(f"sc-compose render {template.name} failed:\n{proc.stderr[-3000:]}")
    return output.read_text(encoding="utf-8")


def answers_text(findings) -> str:
    return "; ".join(f"{f['question']}={f['choice']} @{f['confidence']}" for f in findings or []) or "(none below threshold)"


def run_model(label: str, result_path: str, dry_path: str) -> dict:
    data = json.loads(pathlib.Path(result_path).read_text(encoding="utf-8"))["data"]
    controls = data["controls"]
    rows, failed = [], []
    for expect, name in (("no-drift", "Identity: the original against itself"), ("drift", "Removed obligation: the original minus its first obligation")):
        group = [c for c in controls if c["expect"] == expect]
        missed = {}
        for c in group:
            if not c["ok"]:
                missed[c["got"] or "no answer"] = missed.get(c["got"] or "no answer", 0) + 1
        rows.append({"label": name, "expect": expect, "passed": f"{sum(c['ok'] for c in group)}/{len(group)}",
                     "missed": ", ".join(f"{k} x{v}" for k, v in sorted(missed.items())) or "none"})
    failed = [{"item": c["item"], "got": c["got"] or "no answer", "answers": answers_text(c["findings"])} for c in controls if not c["ok"]]
    sizes = []
    if dry_path:
        reqs = json.loads(pathlib.Path(dry_path).read_text(encoding="utf-8"))["data"]["requests"]
        b = sorted(len(json.dumps(r, ensure_ascii=False).encode("utf-8")) for r in reqs)
        sizes = [{"label": "requests", "value": str(len(b))}, {"label": "median", "value": str(int(statistics.median(b)))},
                 {"label": "largest", "value": str(b[-1])}, {"label": "total", "value": str(sum(b))}]
    counts = data["counts"]
    passed = data["controls_passed"]
    status = "PASS" if data["valid"] else "FAIL"
    summary = (f"Form {data.get('form', label)}: {data['compared']} changed records compared at threshold {data['threshold']}; "
               f"controls {passed}/{len(controls)} passed; run {'valid' if data['valid'] else 'invalid'}; "
               f"verdicts " + ", ".join(f"{v} {counts.get(v, 0)}" for v in VERDICTS) + ".")
    run_json = {"label": label, "form": data.get("form"), "valid": data["valid"], "threshold": data["threshold"],
                "compared": data["compared"], "counts": counts, "controls_passed": passed, "controls": len(controls),
                "deleted": data["deleted"], "added": data["added"], "unchanged": len(data["unchanged"]),
                "run_name": data["log"]["run"], "records": data["records"], "control_results": controls}
    panel = {"id": f"run-{label}", "label": f"Run: {label}", "status": status, "summary": summary,
             "copy_json": json.dumps({k: v for k, v in run_json.items() if k not in ("records", "control_results")}, sort_keys=True),
             "context_text": summary, "controls_rows": rows,
             "verdict_rows": [{"verdict": v, "count": str(counts.get(v, 0))} for v in VERDICTS],
             "size_rows": sizes or [{"label": "requests", "value": "not measured"}], "failed_controls": failed}
    return {"json": run_json, "panel": panel, "row": {"label": label, "iterations": str(len(controls)),
                                                      "pass": f"{passed}/{len(controls)}", "result": status}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="append", required=True, metavar="LABEL=RESULT[:DRY]")
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--source-label", default="")
    ap.add_argument("--output", required=True, help="the HTML page; the JSON sidecar and XHTML panels go beside it")
    ap.add_argument("--intro-html", default="", help="file holding the summary's opening HTML")
    ap.add_argument("--notes-html", default="", help="file holding the method, caveats and recommendation HTML")
    ap.add_argument("--meta", action="append", default=[], metavar="KEY=VALUE")
    args = ap.parse_args()
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    runs = []
    for spec in args.run:
        label, _, paths = spec.partition("=")
        result, _, dry = paths.partition(":")
        runs.append(run_model(label, result, dry))
    sections = [render(TEMPLATES / "drift-form.xhtml.j2", {"form": r["panel"]}, out.with_name(f"{out.stem}-{r['panel']['id']}.xhtml"))
                for r in runs]
    agreement = []
    if len(runs) == 2:
        a = {x["id"]: x["verdict"] for x in runs[0]["json"]["records"]}
        b = {x["id"]: x["verdict"] for x in runs[1]["json"]["records"]}
        for va in VERDICTS:
            agreement.append({"label": va, **{vb.replace("-", "_"): str(sum(1 for i in a if a[i] == va and b.get(i) == vb)) for vb in VERDICTS}})
    meta = [{"label": k, "value": v} for k, _, v in (m.partition("=") for m in args.meta)]
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sidecar = {"schema": SCHEMA, "title": args.title, "generated_at": generated, "metadata": {m["label"]: m["value"] for m in meta},
               "runs": [r["json"] for r in runs], "agreement": agreement}
    out.with_suffix(".json").write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    read = lambda p: pathlib.Path(p).read_text(encoding="utf-8") if p else ""
    shell = {"title": args.title, "subtitle": args.subtitle, "generated_at": generated, "source_label": args.source_label,
             "status": "INFO", "summary_intro_html": read(args.intro_html) or "<p></p>", "rows": [r["row"] for r in runs],
             "toc_rows": [{"id": r["panel"]["id"], "title": r["panel"]["label"], "status": r["panel"]["status"]} for r in runs],
             "sections": sections, "metadata_rows": meta, "agreement_rows": agreement,
             "agreement_intro_html": f"<p>Per-record verdicts of run <code>{runs[0]['json']['label']}</code> (rows) against run <code>{runs[-1]['json']['label']}</code> (columns).</p>" if agreement else "",
             "recommendations_html": read(args.notes_html),
             "footer_html": f"<p>Data: <a href=\"{out.with_suffix('.json').name}\">{out.with_suffix('.json').name}</a>. Rendered with sc-compose from <code>site/examples/templates/</code> by <code>scripts/drift_report.py</code>.</p>",
             "summary_copy_json": json.dumps({"runs": [r["row"] for r in runs]}, sort_keys=True), "summary_copy_context": "", "summary_trailer_html": ""}
    render(TEMPLATES / "drift-report.html.j2", shell, out)
    print(json.dumps({"html": str(out), "json": str(out.with_suffix(".json")), "panels": len(sections)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
