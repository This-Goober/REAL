"""Strict QVHighlights prediction validation and the pinned official MR evaluator."""
import argparse
import importlib
import json
from pathlib import Path
import sys

from .common import read_jsonl, sha256, validate_spans, write_json


def official(root):
    source = Path(root) / 'sources/qvh'
    lock = json.loads(Path(__file__).with_name('sources.lock.json').read_text())
    for item in lock['files']:
        if 'standalone_eval/' in item['path']:
            if sha256(Path(root) / item['path']) != item['sha256']:
                raise ValueError('upstream evaluator hash mismatch: ' + item['path'])
    sys.path.insert(0, str(source.resolve()))
    return importlib.import_module('standalone_eval.eval')


def score(root, predictions, references):
    expected = {r['qid']: r for r in references}
    if len(expected) != len(references) or not expected:
        raise ValueError('reference ids must be nonempty and unique')
    found = [r['qid'] for r in predictions]
    if len(set(found)) != len(found) or set(found) != set(expected):
        raise ValueError('prediction ids must match reference ids exactly; missing failures must be explicit empty predictions')
    normalized, failed, empty, out_of_bounds = [], 0, 0, 0
    for r in predictions:
        ref = expected[r['qid']]
        if r.get('vid') != ref['vid']:
            raise ValueError('prediction video does not match query')
        # The authors' sample includes proposals past annotated duration. Keep
        # them unchanged for native metric parity; report rather than clip them.
        windows = validate_spans(r['pred_relevant_windows'], scored=True)
        out_of_bounds += sum(w[1] > ref['duration'] for w in windows)
        if any(a[2] < b[2] for a, b in zip(windows, windows[1:])):
            raise ValueError('predictions must be confidence ranked')
        failed += bool(r.get('error'))
        empty += not windows
        # Upstream R@1 indexes the first prediction; AP otherwise omits empty
        # predictions from its denominator. A zero-length sentinel scores zero
        # at every positive threshold and keeps failed cases in the denominator.
        normalized.append({**r, 'pred_relevant_windows': windows or [[0, 0, -1e12]]})
    evaluator = official(root)
    ap = evaluator.compute_mr_ap(normalized, references, num_workers=0)
    r1 = evaluator.compute_mr_r1(normalized, references)
    return {'n': len(expected), 'failed': failed, 'empty_predictions': empty,
            'out_of_bounds_proposals': out_of_bounds,
            'units': 'percent', 'evaluator': 'unmodified pinned Moment-DETR MR functions; serial execution',
            'metrics': {'MR-full-mAP': ap['average'], 'MR-full-mAP@0.5': ap['0.5'],
                        'MR-full-mAP@0.75': ap['0.75'], 'MR-full-R1@0.5': r1['0.5'],
                        'MR-full-R1@0.7': r1['0.7']}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--predictions', type=Path, required=True)
    p.add_argument('--references', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = score(a.root, read_jsonl(a.predictions), read_jsonl(a.references))
    result.update(predictions_sha256=sha256(a.predictions), references_sha256=sha256(a.references))
    write_json(a.out, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
