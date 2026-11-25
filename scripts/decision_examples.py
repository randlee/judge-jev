#!/usr/bin/env python3
"""Shared runner for the two repository decision-tree examples; offline replay by default."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from recording_paths import portable_recording

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/sc-judge-jev'
SKILL = PLUGIN / 'skills/walking-decidr-trees'
QUESTIONS = PLUGIN / 'install/templates/skills/judge-jev/assets/questions'
DEFAULT_RECORDS = ('REQ-JEV-0001', 'ADR-JEV-0001', 'NFR-JEV-0001')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def select_records(index, ids):
    """Read only the Raptor export; reject selected diagnostics before any call."""
    if not isinstance(index.get('requirements'), list) or not isinstance(index.get('decisions'), list):
        raise ValueError('expected a Raptor index with requirements and decisions arrays')
    records = {r['id']: r for table in ('requirements', 'decisions') for r in index[table]}
    issues = index.get('diagnostics', {}).get('issues', [])
    selected = []
    for rid in ids:
        if rid not in records:
            raise ValueError(f'{rid}: not present in the Raptor index')
        if any(issue.get('id') == rid for issue in issues):
            raise ValueError(f'{rid}: Raptor import diagnostic; no model request will be made')
        kind = {'REQ': 'req', 'ADR': 'adr', 'NFR': 'nfr'}.get(rid.split('-')[0])
        if not kind:
            raise ValueError(f'{rid}: expected a REQ, ADR, or NFR id')
        selected.append((kind, records[rid]))
    return selected


def items(kind, record):
    if kind == 'adr':
        return [{'id': record['id'], 'title': record['title'], 'text': json.dumps(record, ensure_ascii=False)}]
    output = []
    for number, statement in enumerate(record['requirement_statement']['statements'], 1):
        if statement['modal'] in ('Must', 'MustNot'):
            payload = {'statement': {'index': number, **statement}, 'record': record}
            output.append({'id': f"{record['id']}.s{number}", 'title': record['title'],
                           'text': json.dumps(payload, ensure_ascii=False)})
    if not output:
        raise ValueError(record['id'] + ': no MUST or MUST NOT statements')
    return output


def example_tree(kind, item, bar):
    shipped = load(QUESTIONS / f'quality-{kind}.json')
    wave = shipped['nodes'][shipped['start']]
    ids = ('context', 'alternatives', 'consequences') if kind == 'adr' else ('obligations', 'term', 'checkable')
    questions = {qid: wave['questions'][qid] for qid in ids}
    policy = [{'id': qid, 'pass': next(iter(q['criteria'])), 'choices': list(q['criteria'])}
              for qid, q in questions.items()]
    splitter = module('decidr_terms', SKILL / 'scripts/terms.py')
    terms = splitter.terms(item)
    noun = 'section' if kind == 'adr' else 'literal term'
    question = {'type': 'choice', 'instructions':
        f"The failed gate and its answer are in state.gate. Which {noun} of the "
        "item accounts for that answer or uncertainty? Use the whole record as context. "
        "Choose none if no listed part accounts for it; do not invent an explanation.",
        'criteria': {term: ('No listed part accounts for the answer or uncertainty.' if term == 'none'
                           else f'The {noun} `{term}` accounts for the answer or uncertainty.') for term in terms}}
    tree = {'id': f'decidr-{kind}', 'kind': kind, 'start': 'gates', 'bar': bar, 'nodes': {
        'gates': {'title': 'Stage 1: gates', 'questions': questions, 'policy': policy,
                  'next': [{'condition': 'ok is false', 'goto': 'error'},
                           {'condition': f'Any other choice or\nconfidence below {bar:g}', 'goto': 'which-part'},
                           {'goto': 'yes'}]},
        'which-part': {'title': 'Stage 2: which part?', 'questions': {'which_part': question},
                       'next': [{'condition': 'ok is false', 'goto': 'error'}, {'goto': 'review'}]},
        'yes': {'verdict': 'yes'}, 'review': {'verdict': 'review'},
        'error': {'error': 'Stop: print the error'}}}
    if kind != 'adr':
        for node_id in ('gates', 'which-part'):
            tree['nodes'][node_id]['per'] = 'statement'
    return tree, terms


PIPELINE = '''scripts=$1
job=$2
first_model=$3
second_model=$4
bar=$5
decidr send --project decidr-question-tree --model "$first_model" --agent-role skill-author < "$job/request.json" \\
  | tee "$job/gates.jsonl" \\
  | jq -c --slurpfile item "$job/item.json" --slurpfile terms "$job/terms.json" --slurpfile tree "$job/tree.json" --argjson bar "$bar" -f "$scripts/next.jq" \\
  | tee "$job/next.jsonl" \\
  | bash "$scripts/send-next.sh" "$second_model" --project decidr-question-tree --agent-role skill-author \\
  | tee "$job/stage2.jsonl" \\
  | jq -c -f "$scripts/verdict.jq" > "$job/verdict.jsonl"
'''


def pipeline_views(selected, output, bar, first_model, second_model):
    views, commands = [], []
    for kind, record in selected:
        for item in items(kind, record):
            job = output / item['id']
            job.mkdir()
            tree, terms = example_tree(kind, item, bar)
            request = {'state': {'item': item}, 'questions': tree['nodes']['gates']['questions']}
            for name, value in (('item', item), ('terms', terms), ('tree', tree), ('request', request)):
                write(job / f'{name}.json', value)
            command = ['bash', '-o', 'pipefail', '-c', PIPELINE, 'decidr-pipeline',
                       str(SKILL / 'scripts'), str(job), first_model, second_model, str(bar)]
            process = subprocess.run(command, capture_output=True, text=True)
            commands.append({'argv': command, 'exit_code': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr})
            boundaries = {}
            for name in ('gates', 'next', 'stage2', 'verdict'):
                text = (job / f'{name}.jsonl').read_text()
                boundaries[name] = json.loads(text) if text.strip() else None
            gate = boundaries['gates']
            verdict = (boundaries['verdict'] or {}).get('verdict', 'error')
            continued = bool(boundaries['next'] and 'questions' in boundaries['next'])
            waves = [{'node': 'gates', 'rule_position': 1 if not gate or gate.get('ok') is False else 2 if continued else 3}]
            path = ['gates']
            if continued:
                waves.append({'node': 'which-part', 'rule_position': 1 if verdict == 'error' else 2})
                path.append('which-part')
            path.append('error' if verdict == 'error' else verdict)
            rows = []
            for qid, answer in (gate or {}).get('value', {}).get('answers', {}).items():
                policy = next(p for p in tree['nodes']['gates']['policy'] if p['id'] == qid)
                rows.append({'wave': 'gates', 'item': item['id'], 'question': qid,
                             'choice': answer['choice'], 'confidence': answer['confidence'],
                             'criterion': tree['nodes']['gates']['questions'][qid]['criteria'].get(answer['choice'], ''),
                             'status': 'accepted' if answer['choice'] == policy['pass'] and answer['confidence'] >= bar else 'under bar'})
            if continued and boundaries['stage2'] and boundaries['stage2'].get('ok'):
                answer = boundaries['stage2']['value']['answers']['which_part']
                rows.append({'wave': 'which-part', 'item': item['id'], 'question': 'which_part',
                             'choice': answer['choice'], 'confidence': answer['confidence'], 'criterion': '', 'status': 'diagnostic'})
            payload = json.loads(item['text'])
            views.append({'id': item['id'], 'kind': kind, 'title': item['title'],
                          'text': payload['statement']['text'] if 'statement' in payload else record['decision']['text'],
                          'tree': tree, 'verdict': verdict, 'path': path, 'waves': waves, 'answers': rows,
                          'raw': {'request': request, 'boundaries': boundaries, 'command': commands[-1]}})
            print(item['id'] + ': ' + ' -> '.join(path), flush=True)
            if process.returncode:
                return views, commands, process.returncode
    return views, commands, 0


def quality_views(selected, index_path, judge, output, repo):
    command = ['uv', 'run', '--python', '3.11', '--script', str(judge), 'quality',
               '--index', str(index_path), '--repository-root', str(repo), '--run-name', 'quality-example-live']
    for kind, record in selected:
        command.extend(['--' + kind, record['id']])
    environment = dict(os.environ, SC_PROJECT='decidr-question-tree')
    process = subprocess.run(command, env=environment, capture_output=True, text=True, cwd=repo)
    (output / 'quality.stdout').write_text(process.stdout)
    (output / 'quality.stderr').write_text(process.stderr)
    envelope = json.loads(process.stdout)
    raw_command = {'argv': command, 'environment': {'SC_PROJECT': 'decidr-question-tree'},
                   'exit_code': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr}
    write(output / 'quality.json', envelope)
    views = []
    records = {r['id']: r for _, r in selected}
    if not envelope.get('success'):
        print(json.dumps(envelope.get('error')), file=sys.stderr)
        return views, [raw_command], process.returncode or 2
    for result in envelope['data']['results']:
        rid = result['record']['id']; kind = result['record']['kind']
        tree = quality_tree(result)
        rows = []
        waves = []
        for wave in result['waves']:
            reasons = wave['reason']
            sets = reasons if wave.get('per') == 'statement' else [{'answers': reasons}]
            per_choices = [{a['id']: a['choice'] for a in s['answers']} for s in sets]
            node = tree['nodes'][wave['node']]
            rules = node.get('next') or node.get('verdict_rules') or []
            rank = selected_rule(rules, per_choices)
            if rank is None:
                raise ValueError(f'{rid}: recorded answers match no rule')
            chosen = rules[rank - 1]
            if chosen.get('goto') != wave.get('next') or chosen.get('verdict') != wave.get('verdict'):
                raise ValueError(f'{rid}: tree rules disagree with the recorded branch')
            waves.append({**wave, 'rule_position': rank})
            for reason in sets:
                item_id = rid + ('.s' + str(reason['statement']['index']) if 'statement' in reason else '')
                for answer in reason['answers']:
                    rows.append({'wave': wave['node'], 'item': item_id, 'question': answer['id'],
                                 'choice': answer['choice'], 'confidence': answer['confidence'],
                                 'criterion': answer.get('criterion', ''),
                                 'status': 'diagnostic' if answer['id'].startswith('d_') else 'gate'})
        record = records[rid]
        statement = record['decision']['text'] if kind == 'adr' else '\n'.join(s['text'] for s in record['requirement_statement']['statements'])
        views.append({'id': rid, 'kind': kind, 'title': record['title'], 'text': statement, 'tree': tree,
                      'verdict': result['verdict'], 'path': result['path'], 'waves': waves, 'answers': rows, 'raw': result})
        print(rid + ': ' + ' -> '.join(result['path']) + ' = ' + result['verdict'], flush=True)
    return views, [raw_command], process.returncode


def quality_tree(result):
    """Use the tree named by quality, verifying its bytes before drawing it."""
    metadata = result['tree']
    source = Path(metadata['path'])
    if not source.is_file():
        source = QUESTIONS / (metadata['id'] + '.json')
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != metadata['sha256']:
        raise ValueError('quality tree bytes do not match the recorded digest')
    return load(source)


def selected_rule(rules, choices):
    """Use judge-jev's first-rule/any-statement semantics; no confidence override."""
    def matches(rule, choice):
        def got(q, values):
            return choice.get(q) in (values if isinstance(values, list) else [values])
        return (all(got(q, v) for q, v in rule.get('when', {}).items())
                and (not rule.get('any') or any(got(q, v) for q, v in rule['any'].items()))
                and all(got(q, v) for q, v in rule.get('all', {}).items()))
    return next((i for i, rule in enumerate(rules, 1) if any(matches(rule, c) for c in choices)), None)


def main(example):
    example_dir = ROOT / 'site' / 'examples' / example
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new output directory')
    parser.add_argument('--live', action='store_true', help='send records to the provider; default replays recorded.json')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--index', type=Path, help='existing Raptor export')
    source.add_argument('--raptor', type=Path, help='Raptor checkout with .venv/bin/python and scripts/extract.py')
    parser.add_argument('--judge', type=Path, help='installed judge-jev scripts/jev_judge.py (quality example only)')
    parser.add_argument('--record', action='append', help='repeat to select records; defaults to one REQ, ADR, NFR')
    parser.add_argument('--replay', type=Path, help='alternative recorded run.json, no decision calls')
    parser.add_argument('--first-model', default='jev')
    parser.add_argument('--second-model', default='jev')
    parser.add_argument('--bar', type=float, default=0.8)
    args = parser.parse_args()
    if args.live and args.replay:
        parser.error('--live and --replay are mutually exclusive')
    if not 0 <= args.bar <= 1:
        parser.error('--bar must be between 0 and 1')
    required = ['d2', 'sc-compose'] + (['decidr', 'jq', 'bash'] if args.live and example == 'decidr-pipeline' else ['uv'] if args.live else [])
    for cli in required:
        if not shutil.which(cli):
            parser.error(cli + ' is missing from PATH; see the example README')
    if args.live and not (args.index or args.raptor):
        parser.error('--live requires --index or --raptor')
    if args.live and example == 'judge-jev-quality' and not args.judge:
        parser.error('quality --live requires --judge pointing to an installed copy')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    if args.live:
        import_run = None
        index_path = args.index.resolve() if args.index else output / 'index.json'
        if args.raptor:
            raptor = args.raptor.resolve()
            command = [str(raptor / '.venv/bin/python'), str(raptor / 'scripts/extract.py'),
                       '--project-root', str(ROOT), '--output', str(index_path)]
            imported = subprocess.run(command, capture_output=True, text=True)
            import_run = {'argv': command, 'exit_code': imported.returncode, 'stdout': imported.stdout, 'stderr': imported.stderr}
            if imported.returncode not in (0, 1) or not index_path.exists():
                raise ValueError('Raptor could not produce an index: ' + imported.stderr)
        index = load(index_path)
        selected = select_records(index, args.record or DEFAULT_RECORDS)
        run = {'example': example, 'mode': 'live', 'captured_at': datetime.now(timezone.utc).isoformat(),
               'revision': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
               'index_sha256': hashlib.sha256(index_path.read_bytes()).hexdigest(),
               'diagnostics': index.get('diagnostics', {}).get('issues', []), 'import': import_run,
               'bar': args.bar if example == 'decidr-pipeline' else None}
        if example == 'decidr-pipeline':
            views, commands, code = pipeline_views(selected, output, args.bar, args.first_model, args.second_model)
        else:
            views, commands, code = quality_views(selected, index_path, args.judge.resolve(), output, ROOT)
        run.update(views=views, commands=commands, exit_code=code)
    else:
        run = load(args.replay or example_dir / 'recorded.json')
        if run['example'] != example:
            raise ValueError('recording belongs to a different example')
        code = run['exit_code']
    locations = [(output, '{run}')]
    if args.index:
        locations.append((args.index.resolve(), '{index}'))
    if args.raptor:
        locations.append((args.raptor.resolve(), '{raptor}'))
    if args.judge:
        locations.append((args.judge.resolve().parents[4], '{installed-judge}'))
    run = portable_recording(run, locations=locations)
    write(output / 'run.json', run)
    from render_decision_report import render_report
    render_report(run, output, replay=not args.live)
    print(json.dumps({'report': str(output / 'report.html'), 'markdown': str(output / 'report.md'), 'exit_code': code}))
    return code
