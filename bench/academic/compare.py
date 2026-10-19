"""Paired QVHighlights comparison with original-source-video bootstrap intervals.

Scoring only: no model calls. All query IDs must match, including failed cases.
Official unrounded per-query AP is aggregated before rounding; uncertainty is
computed over source videos, not independent queries from the same footage.
"""
import argparse
import json
from pathlib import Path
import re

import numpy as np

from .common import read_jsonl, sha256, write_json
from .qvh import official, score

METRICS = ('MR-full-mAP', 'MR-full-R1@0.5', 'MR-full-R1@0.7')


def source_id(vid):
    parts = vid.rsplit('_', 2)
    if len(parts) != 3 or not all(re.fullmatch(r'\d+(?:\.\d+)?', p) for p in parts[1:]):
        raise ValueError('expected QVHighlights source_start_end video ID: ' + vid)
    return parts[0]


def per_query(root, predictions, references):
    # The existing scorer enforces exact ID coverage, source identity, valid
    # spans and ranking. Empty/failed predictions remain zero-credit cases.
    aggregate = score(root, predictions, references)
    evaluator = official(root)
    predicted = {p['qid']: p for p in predictions}
    thresholds = [float(f'{t:.2f}') for t in np.linspace(.5, .95, 10)]
    rows, ap_values = [], []
    for ref in references:
        pred = predicted[ref['qid']]
        windows = pred['pred_relevant_windows'][:10]
        if pred.get('error') and windows:
            raise ValueError('failed cases must have explicit empty predictions')
        if windows:
            gt = [{'video-id': ref['qid'], 't-start': w[0], 't-end': w[1]}
                  for w in ref['relevant_windows']]
            proposals = [{'video-id': ref['qid'], 't-start': w[0], 't-end': w[1], 'score': w[2]}
                         for w in windows]
            _, ap = evaluator.compute_average_precision_detection_wrapper(
                [ref['qid'], gt, proposals], tiou_thresholds=thresholds)
            iou = evaluator.compute_temporal_iou_batch_cross(
                np.asarray([windows[0][:2]], dtype=float),
                np.asarray(ref['relevant_windows'], dtype=float))[0].max()
            values = [float(np.mean(ap) * 100), float(iou >= .5) * 100, float(iou >= .7) * 100]
        else:
            ap, values = np.zeros(10), [0., 0., 0.]
        ap_values.append(ap)
        rows.append(dict(qid=ref['qid'], vid=ref['vid'], source=source_id(ref['vid']),
                         failed=bool(pred.get('error')), values=dict(zip(METRICS, values))))
    array = np.asarray([[r['values'][key] for key in METRICS] for r in rows])
    check = dict(zip(METRICS, array.mean(axis=0)))
    check.update({'MR-full-mAP@0.5': np.mean(ap_values, axis=0)[0] * 100,
                  'MR-full-mAP@0.75': np.mean(ap_values, axis=0)[5] * 100})
    for key, value in check.items():
        if float(f'{value:.2f}') != aggregate['metrics'][key]:
            raise AssertionError('per-query aggregation differs from official scorer: ' + key)
    return aggregate, rows


def paired_bootstrap(left, right, sources, draws=10000, seed=20261018):
    left, right = np.asarray(left, dtype=float), np.asarray(right, dtype=float)
    if (left.ndim != 2 or left.shape != right.shape or left.shape[0] != len(sources)
            or not np.isfinite(left).all() or not np.isfinite(right).all()):
        raise ValueError('finite paired query-by-metric arrays and sources required')
    names = sorted(set(sources))
    if len(names) < 2 or draws < 2:
        raise ValueError('at least two independent source videos and two draws required')
    # Resampling an original source includes all its queries, with multiplicity.
    # Retain the benchmark's query-weighted estimand, not a mean of source means.
    groups = [np.flatnonzero(np.asarray(sources) == name) for name in names]
    sizes = np.asarray([len(g) for g in groups])
    totals = np.asarray([np.stack([left[g].sum(0), right[g].sum(0)]) for g in groups])
    rng = np.random.default_rng(seed)
    sampled = []
    for offset in range(0, draws, 1000):
        indices = rng.integers(0, len(groups), size=(min(1000, draws - offset), len(groups)))
        values = totals[indices].sum(axis=1) / sizes[indices].sum(axis=1)[:, None, None]
        sampled.append(np.concatenate([values[:, 0], values[:, 1], values[:, 0] - values[:, 1]], axis=1))
    estimates = np.concatenate(sampled)
    bounds = np.percentile(estimates, [2.5, 97.5], axis=0)
    means = np.concatenate([left.mean(0), right.mean(0), (left - right).mean(0)])
    count = left.shape[1]
    return {name: [dict(mean=float(means[k * count + j]),
                       ci95=[float(v) for v in bounds[:, k * count + j]])
                   for j in range(count)] for k, name in enumerate(('left', 'right', 'left_minus_right'))}


def compare(root, left, right, references, draws=10000, seed=20261018):
    left_score, lrows = per_query(root, left, references)
    right_score, rrows = per_query(root, right, references)
    sources = [r['source'] for r in lrows]
    values = lambda rows: [[r['values'][key] for key in METRICS] for r in rows]
    result = paired_bootstrap(values(lrows), values(rrows), sources, draws, seed)
    result = {side: dict(zip(METRICS, stats)) for side, stats in result.items()}
    return dict(n_queries=len(references), n_source_videos=len(set(sources)),
                units='percent; differences are percentage points',
                primary_endpoint='MR-full-mAP',
                inference='descriptive paired percentile intervals; no equivalence margin specified',
                bootstrap=dict(unit='original source video', draws=draws, seed=seed,
                               estimand='query-weighted mean', paired=True),
                intervals=result, official_scores={'left': left_score, 'right': right_score},
                per_query={'left': lrows, 'right': rrows})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--left', type=Path, required=True)
    p.add_argument('--right', type=Path, required=True)
    p.add_argument('--references', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--draws', type=int, default=10000)
    p.add_argument('--seed', type=int, default=20261018)
    a = p.parse_args()
    result = compare(a.root, read_jsonl(a.left), read_jsonl(a.right), read_jsonl(a.references), a.draws, a.seed)
    result['files'] = {name: dict(path=str(path), sha256=sha256(path))
                       for name, path in [('left', a.left), ('right', a.right), ('references', a.references)]}
    result['sources'] = {name: sha256(Path(__file__).with_name(name))
                         for name in ['compare.py', 'qvh.py', 'common.py', 'sources.lock.json']}
    write_json(a.out, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('per_query', 'files', 'sources')}, indent=2))


if __name__ == '__main__':
    main()
