"""MEDit-Bench Section 3.5 metrics, independently implemented from the paper.

Not author-provided scoring code. All three references are averaged, never
best-reference picked. Reordering affects narrative quality but not these metrics.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import re

from .common import read_jsonl, sha256, validate_spans, write_json


def timecode_seconds(value, fps):
    rate = Fraction(str(fps))
    if rate <= 0:
        raise ValueError('timecode rate must be positive')
    match = re.fullmatch(r'(\d+):([0-5]\d):([0-5]\d):(\d+)', value)
    if not match:
        raise ValueError('expected non-drop HH:MM:SS:FF timecode: ' + str(value))
    h, m, s, frame = map(int, match.groups())
    nominal = round(rate)
    if nominal <= 0 or frame >= nominal:
        raise ValueError('frame field exceeds declared timecode rate: ' + value)
    # Non-drop 29.97/59.94 labels count nominal 30/60 frames each labelled second.
    return float(Fraction(((h * 60 + m) * 60 + s) * nominal + frame, 1) / rate)


def union(spans):
    out = []
    for start, end in sorted(spans):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out


def iou(a, b):
    intersection = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    total = a[1] - a[0] + b[1] - b[0] - intersection
    return intersection / total if total else 0.0


def union_iou(pred, ref):
    a, b = union(pred), union(ref)
    intersection = sum(max(0, min(x[1], y[1]) - max(x[0], y[0])) for x in a for y in b)
    total = sum(e - s for s, e in a + b) - intersection
    return intersection / total if total else 0.0


def cut_f1(pred, ref, threshold):
    candidates = sorted(((-iou(a, b), i, j) for i, a in enumerate(pred)
                         for j, b in enumerate(ref) if iou(a, b) >= threshold))
    used_p, used_r = set(), set()
    for _, i, j in candidates:
        if i not in used_p and j not in used_r:
            used_p.add(i)
            used_r.add(j)
    return 2 * len(used_p) / (len(pred) + len(ref)) if pred or ref else 0.0


def pair_metrics(pred, ref):
    overlap = union_iou(pred, ref)
    result = {'mIoU': overlap}
    for threshold in (0.3, 0.5, 0.7):
        result[f'R@{threshold}'] = float(overlap >= threshold)
        result[f'F1@{threshold}'] = cut_f1(pred, ref, threshold)
    return result


def score(predictions, references, timebases):
    """timebases: vid -> {fps, duration, provenance}; optional editor_fps map.

    A file's timecode rate must be verified against the annotation/export basis,
    especially if the editor's sequence rate differs from the source media.
    """
    expected = {r['qid']: r for r in references}
    found = {r['qid']: r for r in predictions}
    if not expected or len(expected) != len(references) or len(found) != len(predictions) or expected.keys() != found.keys():
        raise ValueError('prediction/reference ids must be nonempty, unique and identical')
    per_case = []
    for qid, ref in expected.items():
        pred = found[qid]
        if pred['vid'] != ref['vid']:
            raise ValueError('prediction video mismatch')
        basis = timebases.get(ref['vid'])
        if not basis or not basis.get('provenance') or not basis.get('duration'):
            raise ValueError('verified timebase with duration and provenance required for ' + ref['vid'])
        duration = basis['duration']
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            raise ValueError('invalid source duration')
        cuts = validate_spans(pred['cuts'], duration)
        annotations = ref['references']
        if len(annotations) != 3 or {a['annotator_index'] for a in annotations} != {0, 1, 2}:
            raise ValueError('all three editor references required')
        metrics = []
        for annotation in annotations:
            fps = basis.get('editor_fps', {}).get(str(annotation['annotator_index']), basis.get('fps'))
            if fps is None:
                raise ValueError('missing timecode fps')
            reference_cuts = [[timecode_seconds(t, fps) for t in cut] for cut in annotation['timecodes']]
            validate_spans(reference_cuts, duration)
            metrics.append(pair_metrics(cuts, reference_cuts))
        per_case.append({'qid': qid, 'vid': ref['vid'], 'failed': bool(pred.get('error')),
                         'metrics': {k: sum(m[k] for m in metrics) / 3 for k in metrics[0]}})
    return {'n': len(per_case), 'references': 3 * len(per_case),
            'failed': sum(r['failed'] for r in per_case), 'units': 'fraction',
            'implementation': 'REAL reimplementation of MEDit-Bench arXiv:2607.25300v1 section 3.5',
            'aggregation': 'mean over three editor references, then mean over cases',
            'metrics': {k: sum(r['metrics'][k] for r in per_case) / len(per_case)
                        for k in per_case[0]['metrics']}, 'per_case': per_case}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for field in ('predictions', 'references', 'timebases', 'out'):
        p.add_argument('--' + field, type=Path, required=True)
    a = p.parse_args()
    result = score(read_jsonl(a.predictions), read_jsonl(a.references), json.loads(a.timebases.read_text()))
    result.update(predictions_sha256=sha256(a.predictions), references_sha256=sha256(a.references),
                  timebases_sha256=sha256(a.timebases))
    write_json(a.out, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'per_case'}, indent=2))


if __name__ == '__main__':
    main()
