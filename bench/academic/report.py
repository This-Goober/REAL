"""Score every frozen pilot case and save a compact, provenance-linked report."""
import argparse
import json
from pathlib import Path

from .common import read_jsonl, sha256, write_json
from .qvh import score


def report(root, run):
    manifest = json.loads((run / 'manifest.json').read_text())
    cases_file = root / 'qvh/inputs/cases.jsonl'
    if sha256(cases_file) != manifest['inputs_sha256']:
        raise ValueError('pilot inputs changed since inference')
    dataset = json.loads((root / 'qvh/manifest.json').read_text())
    references_file = root / 'qvh/references/answers.jsonl'
    if sha256(references_file) != dataset['references_sha256']:
        raise ValueError('evaluation references changed since selection')
    refs = read_jsonl(references_file)
    if set(manifest['qids']) != {r['qid'] for r in refs}:
        raise ValueError('scoring set differs from frozen inference set')
    result = {'dataset': 'QVHighlights', 'split': 'val', 'status': 'development component pilot',
              'n': len(refs), 'n_full_split': dataset['n_split'],
              'source_videos': len({r['vid'].rsplit('_', 2)[0] for r in refs}),
              'run_manifest_sha256': sha256(run / 'manifest.json'),
              'references_sha256': sha256(references_file), 'conditions': {}}
    for name in manifest['conditions']:
        predictions_file = run / (name + '.jsonl')
        predictions = read_jsonl(predictions_file)
        values = score(root, predictions, refs)
        values['predictions_sha256'] = sha256(predictions_file)
        values['per_case'] = [score(root, [p], [next(r for r in refs if r['qid'] == p['qid'])])
                              | {'qid': p['qid']} for p in predictions]
        calls = [json.loads(p.read_text()) for p in sorted(run.glob('*/' + name + '/run.json'))]
        costs = [c['total_cost_usd'] for c in calls if 'total_cost_usd' in c]
        values['model_calls'] = len(calls)
        values['reported_cost_usd'] = sum(costs) if costs else (0 if not calls else None)
        values['calls_without_cost'] = len(calls) - len(costs)
        values['models_reported'] = sorted({m for c in calls for m in c.get('modelUsage', {})})
        result['conditions'][name] = values
    write_json(run / 'scores.json', result)
    lines = ['# QVHighlights development pilot', '',
             f'{len(refs)} / {dataset["n_split"]} validation queries; {result["source_videos"]} source videos. '
             'Component evaluation, not full-pipeline editing or a leaderboard result.', '',
             '| Condition | R@1 IoU .5 | R@1 IoU .7 | mAP | Failed | Empty | Reported USD |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for name, r in result['conditions'].items():
        m = r['metrics']
        cost = f'{r["reported_cost_usd"]:.4f}' if r['reported_cost_usd'] is not None else 'unknown'
        lines.append(f'| {name} | {m["MR-full-R1@0.5"]:.2f} | {m["MR-full-R1@0.7"]:.2f} | '
                     f'{m["MR-full-mAP"]:.2f} | {r["failed"]} | {r["empty_predictions"]} | {cost} |')
    description = (
        'REAL temporal uses the blind catalogue plus an additional text-only event-selection call. '
        'Reported cost here is the grounding stage only; add the original catalogue cost for total inference cost. '
        'Ranked alternatives may overlap; proposals retain their model coordinates and confidence values.'
        if 'real-temporal' in manifest['conditions'] else
        'The lexical binder uses query-blind descriptions; direct vision uses the same model, '
        'sampled images and per-call cost allowance. Proposals are stably ranked by model confidence.')
    lines += ['', 'Metric units: percent. Every selected case remains in the denominator.', '',
              description + ' Both protocols sample one frame per two-second interval. '
              'The sample is too small to support superiority or generalization claims.', '',
              'See scores.json for per-case scores, model versions, costs and artifact hashes.']
    (run / 'summary.md').write_text('\n'.join(lines) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    r = report(a.root, a.run)
    print((a.run / 'summary.md').read_text())
