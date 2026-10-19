"""Freeze and run the four-condition QVHighlights comparison with one budget.

`prepare` performs no model calls. `execute` requires an explicit model revision
and spending allowance. Scoring is a separate command and refuses incomplete runs.
"""
import argparse
from contextlib import contextmanager
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

from .budget import Budget, needs_review
from .common import finite, probe, read_jsonl, sha256, write_json
from . import pilot, temporal, refine

REPO = Path(__file__).resolve().parents[2]
SKILLS = pilot.DEFAULT_SKILLS


def code_files():
    names = ['suite.py', 'budget.py', 'pilot.py', 'temporal.py', 'refine.py', 'model.py',
             'common.py', 'compare.py', 'qvh.py', 'sources.lock.json', 'requirements.txt']
    paths = [Path(__file__).with_name(name) for name in names]
    paths += [SKILLS / 'real-storyboarding/scripts' / name
              for name in ['ground.py', 'bind.py', 'real_core.py']]
    paths.append(SKILLS / 'real-storyboarding/references/schemas/asset-catalog.schema.json')
    return {str(p.relative_to(REPO)): p for p in paths}


def environment():
    packages = {}
    for name in ['Pillow', 'numpy', 'scipy', 'scikit-learn']:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    versions = {name: subprocess.check_output([name, '-version'], text=True).splitlines()[0]
                for name in ['ffmpeg', 'ffprobe']}
    return dict(python=platform.python_version(), platform=platform.platform(),
                packages=packages, tools=versions)


@contextmanager
def run_lock(out):
    # A per-call budget lock cannot protect prediction/manifest writes between
    # calls. Execution and scoring each own this lock for their whole operation.
    lock = Path(out) / 'suite.lock'
    try:
        handle = lock.open('x')
    except FileExistsError as exc:
        raise ValueError('suite lock exists; inspect the owning process before resuming') from exc
    try:
        with handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def prepare(root, selection, out):
    root, selection, out = Path(root).resolve(), Path(selection).resolve(), Path(out).resolve()
    cases_file = root / 'qvh/inputs/cases.jsonl'
    cases = read_jsonl(cases_file)
    frozen = json.loads(selection.read_text())
    if (not cases or any(set(c) != {'qid', 'vid', 'query', 'duration'} for c in cases)
            or len(cases) != len({c['qid'] for c in cases})):
        raise ValueError('unique answer-free inputs required')
    if sha256(cases_file) != frozen['inputs_sha256'] or [c['qid'] for c in cases] != frozen['qids']:
        raise ValueError('inputs differ from frozen selection')
    media = {}
    for case in cases:
        if case['vid'] in media:
            continue
        video = root / 'qvh/media' / (case['vid'] + '.mp4')
        try:
            provenance = video.with_suffix('.source.json')
            record = json.loads(provenance.read_text())
            if sha256(video) != record['sha256']:
                raise ValueError('media hash mismatch')
            measured = probe(video)
            if abs(measured['duration'] - case['duration']) > 2.1:
                raise ValueError('video duration differs from declared input')
            media[case['vid']] = dict(available=True, sha256=record['sha256'],
                                     provenance_sha256=sha256(provenance), probe=measured)
        except (OSError, ValueError, StopIteration, subprocess.CalledProcessError) as exc:
            media[case['vid']] = dict(available=False, error=f'{type(exc).__name__}: {exc}')
    sources = code_files()
    plan = dict(version=2, root=str(root), selection=str(selection), environment=environment(),
                selection_sha256=sha256(selection), inputs_sha256=sha256(cases_file),
                qids=[c['qid'] for c in cases], source_hashes={k: sha256(p) for k, p in sources.items()},
                media=media, maximum_new_calls=4 * len(cases),
                primary_comparison='real-temporal minus direct-refined, MR-full-mAP',
                secondary_comparisons=['direct-vision', 'real-binder'],
                protocol='same sampled images and exact model revision; two calls per primary condition; '
                         'all selected cases retained; no automatic retries; full stage costs')
    out.mkdir(parents=True, exist_ok=False)
    for relative, path in sources.items():
        dest = out / 'code' / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    shutil.copyfile(cases_file, out / 'cases.jsonl')
    write_json(out / 'plan.json', plan)
    return plan


def verify(out):
    out = Path(out).resolve()
    plan = json.loads((out / 'plan.json').read_text())
    if plan.get('environment') != environment():
        raise ValueError('runtime environment changed after freeze; prepare a new plan before inference')
    if sha256(plan['selection']) != plan['selection_sha256']:
        raise ValueError('frozen selection changed')
    root = Path(plan['root'])
    if (sha256(root / 'qvh/inputs/cases.jsonl') != plan['inputs_sha256']
            or sha256(out / 'cases.jsonl') != plan['inputs_sha256']):
        raise ValueError('frozen inputs changed')
    for relative, expected in plan['source_hashes'].items():
        if sha256(REPO / relative) != expected or sha256(out / 'code' / relative) != expected:
            raise ValueError('source changed after freeze: ' + relative)
    for vid, record in plan['media'].items():
        path = root / 'qvh/media' / (vid + '.mp4')
        if record['available']:
            if (sha256(path) != record['sha256']
                    or sha256(path.with_suffix('.source.json')) != record['provenance_sha256']):
                raise ValueError('media changed after freeze: ' + vid)
        elif path.exists():
            raise ValueError('previously unavailable media appeared; prepare a new plan before inference')
    return plan


def execute(out, model, total_cap, per_call_cap=1.0):
    with run_lock(out):
        return _execute(out, model, total_cap, per_call_cap)


def _execute(out, model, total_cap, per_call_cap):
    out = Path(out).resolve()
    plan = verify(out)
    if not model or not finite(per_call_cap) or per_call_cap <= 0:
        raise ValueError('explicit model revision and finite positive per-call cap required')
    config = dict(model=model, total_allowance_usd=total_cap, per_call_allowance_usd=per_call_cap,
                  plan_sha256=sha256(out / 'plan.json'))
    config_file = out / 'execution.json'
    if config_file.exists() and json.loads(config_file.read_text()) != config:
        raise ValueError('execution settings changed; review the existing run before proceeding')
    budget = Budget(out, total_cap, model)
    write_json(config_file, config)
    root = Path(plan['root'])
    state = dict(status='running', new_inference_authorized_by_cli=True)
    write_json(out / 'state.json', state)
    try:
        baseline = pilot.run(root, out / 'baseline', SKILLS, model, per_call_cap, infer_fn=budget)
        grounded = temporal.run(root, out / 'baseline', out / 'temporal', model, per_call_cap, infer_fn=budget)
        refined = refine.run(root / 'qvh/inputs/cases.jsonl', out / 'baseline', out / 'refined',
                             model, per_call_cap, infer_fn=budget)
        all_rows = [*baseline.values(), grounded, refined]
        state['stopped_rows'] = sum('BudgetStopped' in r.get('error', '') for rows in all_rows for r in rows)
        state['status'] = 'budget_or_model_review_required' if state['stopped_rows'] else 'complete'
        verify(out)
    except Exception as exc:
        state.update(status='incomplete', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        state['budget'] = budget.status()
        if needs_review(state['budget']):
            state['status'] = 'budget_or_model_review_required'
        write_json(out / 'state.json', state)
    return state


def score_run(out):
    with run_lock(out):
        return _score_run(out)


def _score_run(out):
    # Only this separate scoring entry point reads evaluation answers.
    from .compare import compare
    from .qvh import score
    out = Path(out).resolve()
    plan = verify(out)
    state = json.loads((out / 'state.json').read_text())
    if state['status'] != 'complete':
        raise ValueError('incomplete inference cannot be reported as the planned comparison')
    config = json.loads((out / 'execution.json').read_text())
    if config['plan_sha256'] != sha256(out / 'plan.json'):
        raise ValueError('execution plan changed')
    budget = Budget(out, config['total_allowance_usd'], config['model']).status()
    if needs_review(budget):
        raise ValueError('call cost or model records require review before scoring')
    root = Path(plan['root'])
    refs_file = root / 'qvh/references/answers.jsonl'
    selection = json.loads(Path(plan['selection']).read_text())
    if sha256(refs_file) != selection['references_sha256']:
        raise ValueError('scoring references differ from frozen selection')
    refs = read_jsonl(refs_file)
    paths = {'real-binder': out / 'baseline/real-binder.jsonl',
             'direct-vision': out / 'baseline/direct-vision.jsonl',
             'real-temporal': out / 'temporal/real-temporal.jsonl',
             'direct-refined': out / 'refined/direct-refined.jsonl'}
    predictions = {name: read_jsonl(path) for name, path in paths.items()}
    costs = {}
    stages = {'real-binder': [('baseline', 'real-binder')],
              'direct-vision': [('baseline', 'direct-vision')],
              'real-temporal': [('baseline', 'real-binder'), ('temporal', 'real-temporal')],
              'direct-refined': [('baseline', 'direct-vision'), ('refined', 'direct-refined')]}
    for condition, folders in stages.items():
        records = [json.loads(path.read_text()) for folder, name in folders
                   for path in sorted((out / folder).glob('*/' + name + '/run.json'))]
        costs[condition] = refine.cost_summary(records)
    result = dict(primary=compare(root, predictions['real-temporal'], predictions['direct-refined'], refs),
                  conditions={name: score(root, rows, refs) for name, rows in predictions.items()},
                  costs=costs, actual_spending=budget,
                  predictions_sha256={name: sha256(path) for name, path in paths.items()},
                  references_sha256=sha256(refs_file), execution_sha256=sha256(out / 'execution.json'))
    write_json(out / 'comparison.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--root', type=Path, required=True)
    prep.add_argument('--selection', type=Path, required=True)
    prep.add_argument('--out', type=Path, required=True)
    run = sub.add_parser('execute')
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--model', required=True)
    run.add_argument('--total-cap', type=float, required=True)
    run.add_argument('--per-call-cap', type=float, default=1.0)
    scoring = sub.add_parser('score')
    scoring.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.root, args.selection, args.out)
        print(f"Prepared {len(result['qids'])} cases; no model calls.")
    elif args.command == 'execute':
        print(json.dumps(execute(args.out, args.model, args.total_cap, args.per_call_cap), indent=2))
    else:
        result = score_run(args.out)
        print(json.dumps(result['primary']['intervals'], indent=2))


if __name__ == '__main__':
    main()
