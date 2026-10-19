"""Re-score saved pilot predictions and freeze the next 100 public input IDs.

No model calls. Source answers remain under the ignored data root.
  python -m bench.academic.recheck_submission --root bench/work/academic --out OUT
"""
import argparse
import json
from pathlib import Path

from .common import read_jsonl, write_json, write_jsonl, sha256
from .data import prepare_qvh
from .qvh import score

REPO = Path(__file__).resolve().parents[2]
E09 = REPO / 'experiments/E09-temporal-grounding/results'
E08 = REPO / 'experiments/E08-academic-benchmarks/results'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    refs = read_jsonl(a.root / 'sources/qvh/data/highlight_val_release.jsonl')
    sample = read_jsonl(a.root / 'sources/qvh/standalone_eval/sample_val_preds.jsonl')
    full = score(a.root, sample, refs)
    expected = json.loads((a.root / 'sources/qvh/standalone_eval/sample_val_preds_metrics_raw.json').read_text())['brief']
    for key, value in full['metrics'].items():
        if value != expected[key]:
            raise ValueError(f'upstream parity failed: {key}: {value} != {expected[key]}')
    write_json(a.out / 'official-parity.json', full)
    all_cases = []
    results = {'date': '2026-10-18', 'status': 'replay only; no new inference', 'sets': {}}
    for split in ('development', 'fresh'):
        cases = read_jsonl(E09 / split / 'cases.jsonl')
        all_cases.extend(cases)
        ids = {c['qid'] for c in cases}
        selected_refs = [r for r in refs if r['qid'] in ids]
        # E08 preserves the final replay-clean original baseline predictions.
        baseline = E09 / 'fresh-baselines' if split == 'fresh' else E08
        if not baseline.exists():
            raise FileNotFoundError(baseline)
        values = {}
        for name, path in [('real-temporal', E09 / split / 'real-temporal.jsonl'),
                           ('direct-vision', baseline / 'direct-vision.jsonl'),
                           ('real-binder', baseline / 'real-binder.jsonl')]:
            preds = read_jsonl(path)
            values[name] = score(a.root, preds, selected_refs)
            values[name]['prediction_sha256'] = sha256(path)
            values[name]['path'] = str(path.relative_to(REPO))
        values['official-sample-supervised-context'] = score(a.root, [r for r in sample if r['qid'] in ids], selected_refs)
        results['sets'][split] = {'qids': sorted(ids), 'conditions': values}
    write_json(a.out / 'pilot-recheck.json', results)
    write_jsonl(a.out / 'consumed-cases.jsonl', all_cases)
    # Only public input fields are copied into the research artifact.
    prepare_qvh(a.root, limit=100, seed='real-academic-confirmatory-v1',
                exclude_inputs=a.out / 'consumed-cases.jsonl')
    cases = read_jsonl(a.root / 'qvh/inputs/cases.jsonl')
    write_jsonl(a.out / 'next100-cases.jsonl', cases)
    write_json(a.out / 'next100-manifest.json', json.loads((a.root / 'qvh/manifest.json').read_text()))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
