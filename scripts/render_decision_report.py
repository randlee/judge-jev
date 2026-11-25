#!/usr/bin/env python3
"""Build matching sc-compose XHTML and Markdown reports from recorded decision results."""
from __future__ import annotations
import argparse
import base64
import json
from pathlib import Path
import shlex
import subprocess
import xml.etree.ElementTree as ET
from gen_tree_diagrams import render

ROOT = Path(__file__).resolve().parents[1]


def render_report(run, output, *, replay=True):
    output = Path(output)
    diagrams = output / 'diagrams'
    diagrams.mkdir(exist_ok=True)
    views = []
    markdown = [f"# {run['example']} — decision report", '',
                'Recorded live responses; rendering this report does not send model requests.' if replay else 'Results from this live example run.',
                '', f"Source revision: `{run['revision']}`. Captured: {run['captured_at']}.",
                '', 'The highlighted path is reconstructed from recorded branches and answers.', '']
    diagnostics = run.get('diagnostics', [])
    if diagnostics:
        markdown.extend(['## Raptor import diagnostics', '',
                         'These records were not selected for the live examples:', ''])
        markdown.extend(f"- `{d.get('id')}`: {d.get('rule')} at {d.get('file')}:{d.get('line')} — {d.get('message')}" for d in diagnostics)
        markdown.append('')
    markdown.extend(['## Commands', ''])
    for command in run.get('commands', []):
        markdown.extend(['```bash', shlex.join(command['argv']), '```',
                         f"Exit status: {command['exit_code']}.", ''])
    for view in run['views']:
        d2 = diagrams / (view['id'] + '.d2')
        svg = diagrams / (view['id'] + '.svg')
        mmd = render(view['tree'], 'mmd', view)
        (diagrams / (view['id'] + '.mmd')).write_text(mmd, encoding='utf-8')
        (diagrams / (view['id'] + '.tree.json')).write_text(json.dumps(view['tree'], indent=2) + '\n')
        d2.write_text(render(view['tree'], 'd2', view), encoding='utf-8')
        for command in (['d2', 'fmt', str(d2)], ['d2', 'validate', str(d2)],
                        ['d2', '--layout', 'elk', str(d2), str(svg)]):
            checked = subprocess.run(command, capture_output=True, text=True)
            if checked.returncode:
                raise ValueError('D2 failed: ' + checked.stderr)
        svg_data = 'data:image/svg+xml;base64,' + base64.b64encode(svg.read_bytes()).decode('ascii')
        rows = [{**a, 'confidence_label': f"{a['confidence']:.0%}", 'confidence_width': round(a['confidence'] * 100, 2)}
                for a in view['answers']]
        views.append({**view, 'svg_data': svg_data, 'path_label': ' → '.join(view['path']),
                      'answers': rows, 'raw_json': json.dumps(view['raw'], indent=2, ensure_ascii=False)})
        markdown.extend([f"## {view['id']} — {view['title']}", '', view['text'], '',
                         f"**Verdict:** {view['verdict']}. **Path:** {' → '.join(view['path'])}.", '',
                         '```mermaid', mmd.rstrip(), '```', '',
                         '| Wave / item | Question | Choice | Confidence | Role |', '|---|---|---|---:|---|'])
        for answer in rows:
            escape = lambda value: str(value).replace('|', '&#124;').replace('\n', ' ')
            markdown.append('| ' + ' | '.join(escape(value) for value in (
                answer['wave'] + ' / ' + answer['item'], answer['question'], answer['choice'],
                answer['confidence_label'], answer['status'])) + ' |')
        markdown.append('')
    counts = {verdict: sum(v['verdict'] == verdict for v in views) for verdict in ('yes', 'no', 'review', 'error')}
    title = 'One wave at a time.' if run['example'] == 'decidr-pipeline' else 'The quality tree, observed.'
    context = {'report': {'title': title, 'example': run['example'], 'captured_at': run['captured_at'],
                          'revision': run['revision'], 'mode': 'Recorded live results · offline replay' if replay else 'Live run',
                          'summary': ' · '.join(f'{number} {verdict}' for verdict, number in counts.items() if number),
                          'item_count': len(views), 'diagnostic_count': len(diagnostics),
                          'policy': (f"Accepted gate choice and confidence ≥ {run['bar']:g}. Otherwise, ask which part and return review."
                                     if run.get('bar') is not None else
                                     'Shipped quality trees select branches from choices. Diagnostic questions and confidence do not change their verdicts.'),
                          'diagnostics': diagnostics}, 'views': views}
    variables = output / 'report-data.json'
    variables.write_text(json.dumps(context, ensure_ascii=False) + '\n', encoding='utf-8')
    command = ['sc-compose', 'render', '--file', str(ROOT / 'templates/decision-report/report.xhtml.j2'),
               '--var-file', str(variables), '--output', str(output / 'report.html'), '--check-render']
    composed = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
    if composed.returncode:
        raise ValueError('sc-compose render failed: ' + composed.stdout + composed.stderr)
    # Check the same XHTML well-formedness contract as sc-compose's XHTML examples.
    ET.parse(output / 'report.html')
    (output / 'report.md').write_text('\n'.join(markdown), encoding='utf-8')
    return output / 'report.html'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    print(render_report(json.loads(args.recording.read_text()), args.output))
