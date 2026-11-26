#!/usr/bin/env python3
"""Render a decision-tree JSON file as Mermaid, Markdown, or D2 source.

Ordered when/all/any rule handling is adapted from the existing generator on
judge-jev's docs/mode-diagrams branch. Both outputs use the same graph. No model
is called. --result may name a report view with its actual path and waves.
"""
from __future__ import annotations
import argparse
import html
import json
from pathlib import Path
import textwrap


def _choices(value):
    return value if isinstance(value, list) else [value]


def _cond(rule):
    if 'condition' in rule:
        return rule['condition']
    parts = []
    for key, joiner in (('when', ' and '), ('all', ' and '), ('any', ' or ')):
        if rule.get(key):
            parts.append(joiner.join(f"{q} = {' / '.join(_choices(c))}" for q, c in rule[key].items()))
    return ' and '.join(parts) or 'otherwise'


def graph(tree, result=None):
    """Keep rule order, every branch, terminal, and question; never infer a path."""
    source = tree['nodes']
    if tree['start'] not in source:
        raise ValueError('tree start does not name a node')
    nodes, edges = {}, []
    result = result or {}
    path = result.get('path', [])
    waves = {w['node']: w for w in result.get('waves', [])}
    active_edges = set()
    for i, name in enumerate(path):
        wave = waves.get(name, {})
        rules = source.get(name, {}).get('next') or source.get(name, {}).get('verdict_rules') or []
        rank = wave.get('rule_position')
        if rank is None and wave.get('rule_rank') is not None:
            # judge-jev rank is global across the tree, not a per-node index.
            offset = sum(len(n.get('next') or n.get('verdict_rules') or [])
                         for k, n in source.items() if k in list(source)[:list(source).index(name)])
            rank = wave['rule_rank'] - offset
        if rank is None:
            continue
        prev = name
        for number, rule in enumerate(rules[:rank], 1):
            dest = rule.get('goto') or 'verdict_' + rule.get('verdict', '')
            if _cond(rule) == 'otherwise':
                active_edges.add((prev, dest))
            else:
                condition = f'{name}__r{number}'
                active_edges.add((prev, condition))
                if number == rank:
                    active_edges.add((condition, dest))
                prev = condition
    for name, node in source.items():
        if 'questions' not in node:
            verdict = node.get('verdict')
            nodes[name] = {'label': ('Verdict: ' + verdict) if verdict else node.get('error', name),
                           'role': 'pass' if verdict == 'yes' else 'error' if node.get('error') else 'review',
                           'active': name in path}
            continue
        title = node.get('title', name)
        per_statement = node.get('per') == 'statement' or '.s' in result.get('id', '')
        scope = 'per MUST / MUST NOT statement' if per_statement else 'per record'
        if node.get('only_matched'):
            scope += '; matched statements only'
        rows = [title, scope]
        for qid, question in node['questions'].items():
            choices = list(question.get('criteria', {}))
            if qid == 'which_part':
                rows.append('which_part: phrase / section or none')
            elif qid.startswith('d_'):
                rows.append(qid + ' (diagnostic)')
            else:
                rows.append(qid + ': ' + ' / '.join(choices))
        label = '\n'.join(textwrap.fill(row, width=46, break_long_words=False, break_on_hyphens=False) for row in rows)
        nodes[name] = {'label': label, 'role': 'wave', 'active': name in path}
        rules = node.get('next') or node.get('verdict_rules') or []
        prev = name
        for number, rule in enumerate(rules, 1):
            target = rule.get('goto') or 'verdict_' + rule.get('verdict', '')
            if 'goto' in rule and target not in source:
                raise ValueError(f'{name}: unknown target {target}')
            if 'verdict' in rule:
                nodes[target] = {'label': 'Verdict: ' + rule['verdict'],
                                 'role': 'pass' if rule['verdict'] == 'yes' else 'review',
                                 'active': result.get('verdict') == rule['verdict'] and name in path}
            condition = _cond(rule)
            if condition == 'otherwise':
                edges.append((prev, target, 'otherwise' if prev == name else 'no'))
                break
            rule_id = f'{name}__r{number}'
            label = '\n'.join(textwrap.fill(row, width=30, break_long_words=False, break_on_hyphens=False)
                              for row in f'{number}. {condition}'.splitlines())
            nodes[rule_id] = {'label': label, 'role': 'condition',
                              'active': (prev, rule_id) in active_edges}
            edges.append((prev, rule_id, '' if prev == name else 'no'))
            edges.append((rule_id, target, 'yes'))
            prev = rule_id
    return nodes, edges, active_edges


def render(tree, fmt='mmd', result=None):
    nodes, edges, active_edges = graph(tree, result)
    ids = {key: 'n' + str(i) for i, key in enumerate(nodes)}
    if fmt in ('mmd', 'md'):
        lines = ['flowchart TD']
        for key, node in nodes.items():
            label = html.escape(node['label'], quote=True).replace('\n', '<br/>')
            opener, closer = ('{', '}') if node['role'] == 'condition' else ('[', ']')
            lines.append(f'  {ids[key]}{opener}"{label}"{closer}')
            if node['active']:
                lines.append(f'  class {ids[key]} visited')
        for a, b, label in edges:
            annotation = f'|"{html.escape(label, quote=True)}"|' if label else ''
            lines.append(f'  {ids[a]} -->{annotation} {ids[b]}')
        lines.append('  classDef visited fill:#e7f4ef,stroke:#23755c,stroke-width:2px')
        for number, (a, b, _) in enumerate(edges):
            if (a, b) in active_edges:
                lines.append(f'  linkStyle {number} stroke:#23755c,stroke-width:3px')
        body = '\n'.join(lines) + '\n'
        return '# ' + tree.get('id', 'Decision tree') + '\n\n```mermaid\n' + body + '```\n' if fmt == 'md' else body
    if fmt != 'd2':
        raise ValueError('format must be mmd, md, or d2')
    lines = [
        '# Decision tree and observed path. Level: workflow.',
        '# Render: d2 --layout elk tree.d2 tree.svg',
        'vars: {d2-config: {layout-engine: elk}}',
        'direction: down',
        'classes: {',
        '  wave: {style: {fill: "#f0f4fa"; stroke: "#bac7d8"; font-color: "#233147"}}',
        '  condition: {shape: diamond; style: {fill: "#f9fafc"; stroke: "#c6ced9"; font-color: "#39475d"}}',
        '  pass: {style: {fill: "#edf7f2"; stroke: "#a5cbbb"; font-color: "#285c49"}}',
        '  review: {style: {fill: "#fff6e7"; stroke: "#d7bd91"; font-color: "#765721"}}',
        '  error: {style: {fill: "#fcf0f0"; stroke: "#d7b0b0"; font-color: "#803c3c"}}',
        '  visited: {style: {stroke: "#23755c"; stroke-width: 3}}',
        '}',
    ]
    for key, node in nodes.items():
        classes = '[' + '; '.join([node['role']] + (['visited'] if node['active'] else [])) + ']'
        lines.append(f'{ids[key]}: {json.dumps(node["label"], ensure_ascii=False)} {{class: {classes}}}')
    for a, b, label in edges:
        attributes = ['style.stroke: "#b3becb"']
        if label:
            attributes.append('target-arrowhead.label: ' + json.dumps(label))
        if (a, b) in active_edges:
            attributes[0] = 'style.stroke: "#23755c"'
            attributes.append('style.stroke-width: 3')
        attrs = ' {' + '; '.join(attributes) + '}' if attributes else ''
        lines.append(f'{ids[a]} -> {ids[b]}:{attrs}' if attrs else f'{ids[a]} -> {ids[b]}')
    lines.extend(['legend: {', '  label: ""', '  near: top-center', '  grid-rows: 1',
                  '  style: {stroke-width: 0; fill: transparent}',
                  '  seen: "Observed path" {class: visited}',
                  '  unseen: "Other branch" {class: wave}', '}'])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--result', type=Path)
    parser.add_argument('--format', choices=('mmd', 'md', 'd2'), default='mmd')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    tree = json.loads(args.tree.read_text())
    result = json.loads(args.result.read_text()) if args.result else None
    text = render(tree, args.format, result)
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
