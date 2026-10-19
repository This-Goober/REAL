"""Two-call direct-vision comparator; reuse the frozen first direct call.

No references enter inference. Both calls see identical sampled images. A failed
first call stays failed; a failed refinement is not replaced with its first answer.
This controls call allowance, not realized token consumption or cost.
"""
import argparse
import json
from pathlib import Path

from .common import finite, read_jsonl, sha256, write_json, write_jsonl
from .model import infer
from .pilot import direct_prediction, direct_prompt


def refinement_prompt(case, first):
    return (direct_prompt(case) + '\nAn independent first pass proposed: '
            + json.dumps({'windows': first}, separators=(',', ':'))
            + '\nRe-examine the same images and the request. Check whether each interval '
            'covers the complete visible event, whether another event was missed, and '
            'whether the confidence ranking reflects relevance. Keep a proposal if it '
            'is already supported; otherwise revise or remove it. Return your final '
            'ranked windows in the same JSON format. No further evidence is available.')


def cost_summary(records):
    costs = [r['total_cost_usd'] for r in records if 'total_cost_usd' in r]
    return {'model_calls': len(records), 'reported_cost_usd': sum(costs),
            'calls_without_cost': len(records) - len(costs),
            'cost_complete': len(records) == len(costs),
            'wall_s_sum': sum(r.get('wall_s', 0) for r in records),
            'usage_by_call': [r.get('usage') for r in records],
            'models_reported': sorted({m for r in records for m in r.get('modelUsage', {})})}


def run(cases_file, cached, out, model, max_cost=1.0, infer_fn=None):
    call_model = infer_fn or infer
    cases_file, cached, out = map(Path, (cases_file, cached, out))
    if not finite(max_cost) or max_cost <= 0:
        raise ValueError('a finite positive per-call allowance is required')
    cases = read_jsonl(cases_file)
    if (not cases or any(set(c) != {'qid', 'vid', 'query', 'duration'} for c in cases)
            or len({c['qid'] for c in cases}) != len(cases)):
        raise ValueError('nonempty unique answer-free cases required')
    original = json.loads((cached / 'manifest.json').read_text())
    if (original['inputs_sha256'] != sha256(cases_file)
            or original['qids'] != [c['qid'] for c in cases]):
        raise ValueError('first-call inputs differ from frozen cases')
    if original['max_cost_per_call_usd'] != max_cost:
        raise ValueError('both calls must have the same per-call allowance')
    first_rows = read_jsonl(cached / 'direct-vision.jsonl')
    if (len(first_rows) != len(cases)
            or {r['qid'] for r in first_rows} != {c['qid'] for c in cases}):
        raise ValueError('first-call rows must include every case exactly once')
    first = {r['qid']: r for r in first_rows}
    # Freeze cached dependencies before any inference; do not depend on mtimes.
    files = [cached / 'manifest.json', cached / 'direct-vision.jsonl']
    for c in cases:
        base = cached / str(c['qid'])
        files.extend(p for folder in ('direct-vision', 'evidence')
                     for p in (base / folder).glob('*') if p.is_file())
        record = base / 'direct-vision/run.json'
        if record.exists():
            old = json.loads(record.read_text())
            # A model alias can change; request the actual pinned revision.
            if ((old.get('ok') or old.get('modelUsage'))
                    and set(old.get('modelUsage', {})) != {model}):
                raise ValueError('first-call reported revision differs from requested model')
    cached_hashes = {str(p.relative_to(cached)): sha256(p) for p in sorted(set(files))}
    sources = [Path(__file__), Path(__file__).with_name('pilot.py'),
               Path(__file__).with_name('model.py'), Path(__file__).with_name('common.py')]
    manifest = dict(dataset='QVHighlights', split='val',
                    conditions=['direct-refined'], qids=[c['qid'] for c in cases],
                    inputs_sha256=sha256(cases_file), model=model,
                    max_cost_per_call_usd=max_cost,
                    protocol='two direct calls; same images, grid and per-call cap; no retries or fallback',
                    source_hashes={p.name: sha256(p) for p in sources},
                    cached_hashes=cached_hashes, cached_path=str(cached.resolve()))
    out.mkdir(parents=True, exist_ok=True)
    mf = out / 'manifest.json'
    if mf.exists() and json.loads(mf.read_text()) != manifest:
        raise ValueError('run configuration changed; use a new output directory')
    write_json(mf, manifest)
    rows, records = [], []
    for c in cases:
        row = dict(qid=c['qid'], vid=c['vid'], pred_relevant_windows=[])
        base = cached / str(c['qid'])
        second = out / str(c['qid']) / 'direct-refined'
        old_record = base / 'direct-vision/run.json'
        if old_record.exists():
            records.append(json.loads(old_record.read_text()))
        try:
            prior = first[c['qid']]
            if prior['vid'] != c['vid']:
                raise ValueError('first-call video mismatch')
            if prior.get('error'):
                raise RuntimeError('first call failed: ' + prior['error'])
            if not old_record.exists() or not json.loads(old_record.read_text()).get('ok'):
                raise ValueError('first-call success record missing')
            evidence = json.loads((base / 'evidence/evidence.json').read_text())
            images = [base / 'evidence' / s['file'] for s in evidence['sheets']]
            for path, sheet in zip(images, evidence['sheets']):
                if sha256(path) != sheet['sha256']:
                    raise ValueError('contact sheet hash mismatch')
            answer = json.loads((base / 'direct-vision/answer.json').read_text())
            prediction = direct_prediction(answer, c, evidence['windows'])
            if prediction != prior['pred_relevant_windows']:
                raise ValueError('first-call saved answer differs from prediction')
            request = json.loads((base / 'direct-vision/request.json').read_text())
            if (request['prompt'] != direct_prompt(c)
                    or [s['sha256'] for s in request['images']] != [sha256(p) for p in images]):
                raise ValueError('first-call evidence or prompt differs')
            refined = call_model(refinement_prompt(c, prediction), images, second, model, max_cost)
            reported = json.loads((second / 'run.json').read_text())
            if set(reported.get('modelUsage', {})) != {model}:
                raise ValueError('refinement did not use the pinned model revision')
            row['pred_relevant_windows'] = direct_prediction(refined, c, evidence['windows'])
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
        if (second / 'run.json').exists():
            records.append(json.loads((second / 'run.json').read_text()))
        rows.append(row)
        write_jsonl(out / 'direct-refined.jsonl', rows)
        write_json(out / 'costs.json', cost_summary(records))
        print(c['qid'], row.get('error', 'refinement recorded'), flush=True)
    if any(sha256(cached / name) != digest for name, digest in cached_hashes.items()):
        raise ValueError('cached first-call evidence changed during execution')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--cached-direct', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--model', required=True, help='Exact model revision reported by first calls')
    parser.add_argument('--max-cost-per-call', type=float, default=1.0)
    args = parser.parse_args()
    run(args.cases, args.cached_direct, args.out, args.model, args.max_cost_per_call)


if __name__ == '__main__':
    main()
