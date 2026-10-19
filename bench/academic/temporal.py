"""Evaluate REAL temporal grounding on cached, query-blind catalogues.

Only public queries, catalogue descriptions, and observation times enter model
inference. References are read exclusively by the separate scoring command.
"""
import argparse
import importlib.util
import json
import shutil
from pathlib import Path

from .common import read_jsonl, sha256, write_json, write_jsonl
from .model import infer, decode_response
from .pilot import DEFAULT_SKILLS

REPO = Path(__file__).resolve().parents[2]


def load_ground(skills=DEFAULT_SKILLS):
    path = Path(skills) / 'real-storyboarding/scripts/ground.py'
    spec = importlib.util.spec_from_file_location('real_ground', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inputs(case, catalogue):
    # Convert adapter windows back into observations of ONE original source file.
    # Crucially, none of these text fields are query-conditioned or oracle tags.
    observations = [dict(id=a['id'], start=a['source_window'][0], end=a['source_window'][1],
                         description=a['role'] + '. ' + a['shows']) for a in catalogue['assets']]
    cat = {'assets': [dict(id='source', k='video', f=case['vid'] + '.mp4', dur=case['duration'],
                           sampling='one centre frame per 2-second interval; descriptions are visual-only',
                           observations=observations)]}
    nb = {'cells': [{'groups': [{'components': [dict(id='request', type='video', text=case['query'])]}]}]}
    return nb, cat


def run(root, cached, out, model='claude-sonnet-5-5', max_cost=1.0, replay_source=None, infer_fn=None):
    call_model = infer_fn or infer
    cases_file = root / 'qvh/inputs/cases.jsonl'
    cases = read_jsonl(cases_file)
    if not cases or any(set(c) != {'qid', 'vid', 'query', 'duration'} for c in cases):
        raise ValueError('only answer-free case fields may enter inference')
    ground = load_ground()
    source_paths = [Path(__file__), Path(__file__).with_name('model.py'),
                    DEFAULT_SKILLS / 'real-storyboarding/scripts/ground.py']
    manifest = dict(dataset='QVHighlights', split='val', scope='temporal component development',
                    qids=[c['qid'] for c in cases], inputs_sha256=sha256(cases_file),
                    conditions=['real-temporal'], model=model, max_cost_per_call_usd=max_cost,
                    protocol='blind visual catalogue plus one text-only event grounding call; 2s grid',
                    source_hashes={str(p.relative_to(REPO)):sha256(p) for p in source_paths},
                    catalogue_hashes={str(c['qid']):(
                        sha256(cached / str(c['qid']) / 'asset-catalog.json')
                        if (cached / str(c['qid']) / 'asset-catalog.json').exists() else None) for c in cases},
                    cached_run_manifest_sha256=sha256(cached/'manifest.json'))
    if replay_source:
        original = json.loads((replay_source / 'manifest.json').read_text())
        for key in ('qids', 'inputs_sha256', 'catalogue_hashes', 'model'):
            if original[key] != manifest[key]:
                raise ValueError('replay input mismatch: ' + key)
        manifest['replayed_from'] = dict(path=str(replay_source), manifest_sha256=sha256(replay_source/'manifest.json'),
                                         reason='validate ranked alternatives and stably order by unmodified confidence', new_model_calls=0)
    out.mkdir(parents=True, exist_ok=True)
    mf = out / 'manifest.json'
    if mf.exists() and json.loads(mf.read_text()) != manifest:
        raise ValueError('configuration changed; use a new output directory')
    write_json(mf, manifest)
    predictions = []
    for c in cases:
        row = dict(qid=c['qid'], vid=c['vid'], pred_relevant_windows=[])
        case_dir = out / str(c['qid'])
        try:
            cat = json.loads((cached / str(c['qid']) / 'asset-catalog.json').read_text())
            nb, source = inputs(c, cat)
            request = ground.prepare(nb, source)
            write_json(case_dir / 'source-catalogue.json', source)
            write_json(case_dir / 'temporal-request.json', request)
            if replay_source:
                original_request = json.loads((replay_source / str(c['qid']) / 'temporal-request.json').read_text())
                if original_request != request:
                    raise ValueError('replay observation request changed')
                original = replay_source / str(c['qid']) / 'real-temporal'
                raw = original / 'response.json'
                answer, response, extraction = decode_response(raw.read_text())
                dest = case_dir / 'real-temporal'
                shutil.copytree(original, dest, dirs_exist_ok=True)
                record = json.loads((dest / 'run.json').read_text())
                record.update(replayed_from_response_sha256=sha256(raw), new_model_calls=0)
                write_json(dest / 'run.json', record)
            else:
                answer = call_model(ground.prompt(request), [], case_dir / 'real-temporal', model, max_cost)
            resolved = ground.resolve(request, answer)
            write_json(case_dir / 'groundings.json', resolved)
            events = resolved['bindings']['request']
            row['pred_relevant_windows'] = [[e['source_in'], e['source_out'], e['confidence']] for e in events]
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
        predictions.append(row)
        write_jsonl(out / 'real-temporal.jsonl', predictions)
        print(c['qid'], row.get('error', row['pred_relevant_windows']), flush=True)
    return predictions


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--cached-catalogues', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--model', default='claude-sonnet-5-5')
    p.add_argument('--replay-source', type=Path)
    p.add_argument('--max-cost-per-call', type=float, default=1.0)
    a = p.parse_args()
    run(a.root, a.cached_catalogues, a.out, a.model, a.max_cost_per_call, a.replay_source)
