"""Replay frozen responses after an output-decoding fix, with no model calls.

Original attempts remain immutable. This does not change prompts, proposals,
confidence values, catalogue descriptions, or the REAL binder implementation.
Ranked outputs are stably sorted by their unmodified model confidence values.
"""
import argparse
import json
from pathlib import Path
import shutil

from .common import read_jsonl, sha256, write_json, write_jsonl
from .model import decode_response
from .pilot import REPO, DEFAULT_SKILLS, binder_predict, catalogue_from, direct_prediction, load_binder


def replay(root, source, out, skills=DEFAULT_SKILLS):
    if out.exists():
        raise ValueError('replay output must be new; original attempts are never overwritten')
    manifest = json.loads((source / 'manifest.json').read_text())
    cases_file = root / 'qvh/inputs/cases.jsonl'
    if sha256(cases_file) != manifest['inputs_sha256']:
        raise ValueError('inference inputs changed')
    for name in ('bind.py', 'real_core.py'):
        path = Path(skills) / 'real-storyboarding/scripts' / name
        key = str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)
        if sha256(path) != manifest['source_hashes'][key]:
            raise ValueError('replay requires the original binder implementation')
    manifest['replayed_from'] = {'path': str(source), 'manifest_sha256': sha256(source / 'manifest.json'),
                                'reason': 'decode intact JSON and stably rank by unmodified model confidence; no coordinate or confidence edits',
                                'new_model_calls': 0}
    manifest['replay_source_hashes'] = {p.name: sha256(p) for p in Path(__file__).parent.glob('*.py')}
    write_json(out / 'manifest.json', manifest)
    binder = load_binder(skills)
    results = {'real-binder': [], 'direct-vision': []}
    for case in read_jsonl(cases_file):
        old = source / str(case['qid'])
        evidence = json.loads((old / 'evidence/evidence.json').read_text())
        for item in evidence['sheets']:
            if sha256(old / 'evidence' / item['file']) != item['sha256']:
                raise ValueError('frozen evidence changed')
        for condition in results:
            original = old / condition
            dest = out / str(case['qid']) / condition
            dest.mkdir(parents=True)
            record = json.loads((original / 'run.json').read_text())
            raw = original / 'response.json'
            record['replayed_from_response_sha256'] = sha256(raw)
            record['replayed_from_response'] = str(raw)
            row = {'qid': case['qid'], 'vid': case['vid'], 'pred_relevant_windows': []}
            try:
                answer, response, extraction = decode_response(raw.read_text())
                request = json.loads((original / 'request.json').read_text())
                for image in request['images']:
                    if sha256(image['file']) != image['sha256']:
                        raise ValueError('model input image changed')
                if condition == 'real-binder':
                    cat = catalogue_from(answer, evidence['windows'], root / 'qvh/media' / (case['vid'] + '.mp4'))
                    from real_core import validate_document
                    validate_document(cat, 'asset-catalog')
                    prediction, details = binder_predict(case['query'], cat, evidence['windows'], binder)
                    write_json(dest / 'asset-catalog.json', cat)
                    write_json(dest / 'binding-evidence.json', details)
                else:
                    prediction = direct_prediction(answer, case, evidence['windows'])
                row['pred_relevant_windows'] = prediction
                record.update(ok=True, json_extraction=extraction)
                record.pop('error', None)
                write_json(dest / 'answer.json', answer)
            except Exception as exc:
                row['error'] = f'{type(exc).__name__}: {exc}'
                record.update(ok=False, error=row['error'])
            write_json(dest / 'run.json', record)
            results[condition].append(row)
    for name, rows in results.items():
        write_jsonl(out / (name + '.jsonl'), rows)
    for name in ('random-window', 'full-video'):
        shutil.copyfile(source / (name + '.jsonl'), out / (name + '.jsonl'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'source', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    replay(a.root.resolve(), a.source.resolve(), a.out.resolve())
