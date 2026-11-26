#!/usr/bin/env python3
"""Render judge-jev quality panels with sc-compose: one panel per quality tree, one per fixed record, and a page.

usage: render_quality_panels.py <out-dir> [--changes <file.json> ...]

Tree panels need no input: they are drawn from the shipped tree files. A change panel is drawn from one JSON
file; templates/quality-panels/examples/ holds three, and README.md beside the templates gives the fields.
Nothing here calls a model.
"""
import argparse, json, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quality_tree_vars

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates/quality-panels"
QUESTIONS = ROOT / "plugins/sc-judge-jev/install/templates/skills/judge-jev/assets/questions"
KINDS = ("req", "nfr", "adr")


def sc_compose_available() -> bool:
    if shutil.which("sc-compose"):
        return True
    try:
        import sc_compose  # noqa: F401
    except ImportError:
        return False
    return True


def render(template: str, variables: dict, output: Path) -> str:
    """One sc-compose render: the CLI when it is on PATH (as the other report scripts use), else the wheel."""
    var_file = output.with_name(output.name + ".vars.json")
    var_file.write_text(json.dumps(variables, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    source = TEMPLATES / template
    if shutil.which("sc-compose"):
        done = subprocess.run(["sc-compose", "render", "--file", str(source), "--var-file", str(var_file), "--output", str(output)],
                              capture_output=True, text=True, cwd=ROOT)
        if done.returncode:
            raise ValueError("sc-compose render failed: " + done.stdout + done.stderr)
    else:
        import sc_compose
        composed = sc_compose.compose_file(sc_compose.ComposeRequest(str(TEMPLATES), sc_compose.ComposeMode.file(str(source)), vars_input=variables))
        output.write_text(composed.rendered_text, encoding="utf-8")
    ET.parse(output)                                      # every panel and the page must be well-formed XHTML
    return output.read_text(encoding="utf-8")


def tree_panel(kind: str, out: Path, questions: Path = QUESTIONS) -> Path:
    variables = quality_tree_vars.load(questions / f"quality-{kind}.json", TEMPLATES / "labels.json", f"assets/questions/quality-{kind}.json")
    target = out / f"tree-{kind}.panel.xhtml"
    render("quality-tree-panel.xhtml.j2", variables, target)
    return target


def change_panel(source: Path, out: Path) -> Path:
    variables = json.loads(source.read_text(encoding="utf-8"))
    target = out / f"fix-{variables['record']['id']}.panel.xhtml"
    render("record-change-panel.xhtml.j2", variables, target)
    return target


def page(out: Path, changes: list) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    trees, fixes = [], []
    for kind in KINDS:
        made = tree_panel(kind, out)
        trees.append({"anchor": f"tree-{kind}", "nav": f"{kind.upper()} tree", "html": made.read_text(encoding="utf-8")})
    for source in changes:
        made = change_panel(source, out)
        record = json.loads(source.read_text(encoding="utf-8"))["record"]
        fixes.append({"anchor": f"fix-{record['kind']}", "nav": f"{record['id']} fixed", "html": made.read_text(encoding="utf-8")})
    groups = [{"title": "What is asked", "panels": trees}]
    if fixes:
        groups.append({"title": "Records that were fixed", "panels": fixes})
    target = out / "index.html"
    render("report-page.xhtml.j2", {
        "page": {"title": "judge-jev quality: the trees" + (" and the fixes" if fixes else ""), "eyebrow": "judge-jev · quality mode",
                 "lede": "What judge-jev asks about a REQ, an NFR and an ADR, drawn from the tree files it runs"
                         + (", and real records that failed and were fixed." if fixes else "."),
                 "foot": "Rendered by sc-compose from templates/quality-panels. Tree panels read the tree files; fix panels read one JSON file each."},
        "groups": groups}, target)
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--changes", type=Path, nargs="*", default=sorted((TEMPLATES / "examples").glob("*.json")))
    args = parser.parse_args(argv)
    print(page(args.out, args.changes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
