"""QVHighlights pilot: blind visual catalogue -> REAL binder vs direct vision.

Uniform two-second windows are benchmark adapter proposals, not ground-truth
shots. This evaluates a REAL component, not the entire editing pipeline.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import sys

from .common import probe, read_jsonl, sha256, validate_spans, write_json, write_jsonl
from .model import infer

REPO = Path(__file__).resolve().parents[2]
DEFAULT_SKILLS = REPO / 'skills/batch-2/skills'


def load_binder(skills):
    scripts = Path(skills) / 'real-storyboarding/scripts'
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location('academic_real_bind', scripts / 'bind.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_sheets(video, duration, out):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    out.mkdir(parents=True, exist_ok=True)
    observed = probe(video)
    if abs(observed['duration'] - duration) > 2.1:
        raise ValueError(f'video/annotation duration mismatch: {observed["duration"]} vs {duration}')
    evidence = {'video_sha256': sha256(video), 'duration': duration, 'probe': observed,
                'sampling': 'one centre frame per 2-second window', 'window_s': 2}
    index_file = out / 'evidence.json'
    if index_file.exists():
        old = json.loads(index_file.read_text())
        if any(old[k] != v for k, v in evidence.items()):
            raise ValueError('stale frame evidence; use a new output directory')
        for item in old['sheets']:
            if sha256(out / item['file']) != item['sha256']:
                raise ValueError('contact sheet hash mismatch')
        return old
    windows, tiles = [], []
    # Use Pillow's bundled scalable font on macOS as well as Linux. The saved
    # sheets are shared byte-for-byte by all conditions, not recreated per model.
    font = ImageFont.load_default(size=17)
    for i in range(math.ceil(duration / 2)):
        start, end = 2 * i, min(duration, 2 * i + 2)
        time = min((start + end) / 2, observed['duration'] - 0.04)
        frame = out / f'frame-{i:03d}.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(time), '-i', str(video),
                        '-frames:v', '1', '-vf', 'scale=384:-2', '-q:v', '3', str(frame)],
                       check=True, capture_output=True, timeout=60)
        with Image.open(frame) as img:
            tile = Image.new('RGB', (384, 248), '#151515')
            tile.paste(ImageOps.contain(img.convert('RGB'), (384, 216)), (0, 32))
        aid = f'A{i:03d}'
        ImageDraw.Draw(tile).text((6, 5), f'{aid}  {start:g}-{end:g}s', fill='white', font=font)
        tiles.append(tile)
        windows.append({'id': aid, 'start': start, 'end': end, 'sample_s': time})
    sheets = []
    for offset in range(0, len(tiles), 16):
        chunk = tiles[offset:offset + 16]
        sheet = Image.new('RGB', (1536, 248 * math.ceil(len(chunk) / 4)), '#151515')
        for j, tile in enumerate(chunk):
            sheet.paste(tile, ((j % 4) * 384, (j // 4) * 248))
        dest = out / f'sheet-{offset // 16:02d}.jpg'
        sheet.save(dest, quality=85)
        sheets.append({'file': dest.name, 'sha256': sha256(dest)})
    evidence.update(windows=windows, sheets=sheets,
                    label_font={'family': font.getname(), 'size': 17,
                                'pillow_version': Image.__version__})
    write_json(index_file, evidence)
    return evidence


def catalog_prompt(windows):
    return ("Describe every numbered video window in these contact sheets, based only on visible evidence. "
            "Each window is represented by one sampled frame; do not invent motion or offscreen events. "
            "There is no editing query yet. Produce reusable catalogue descriptions. "
            "For each id provide role (short title), shows (literal visible content), "
            "and binds_to (a description of footage a creator could request). "
            "Be specific about subjects, actions actually visible, setting, and objects. "
            "Return {\"assets\":[{\"id\":\"A000\",\"role\":\"...\",\"shows\":\"...\","
            "\"binds_to\":\"...\"},...]}. Include every id exactly once: "
            + ', '.join(w['id'] for w in windows))


def catalogue_from(answer, windows, video):
    rows = answer['assets']
    ids = [r['id'] for r in rows]
    if len(set(ids)) != len(ids) or set(ids) != {w['id'] for w in windows}:
        raise ValueError('catalogue omitted or duplicated a window')
    by_id = {r['id']: r for r in rows}
    assets = []
    for w in windows:
        desc = by_id[w['id']]
        if not all(isinstance(desc.get(k), str) and desc[k].strip() for k in ('role', 'shows', 'binds_to')):
            raise ValueError('missing catalogue description')
        assets.append({**{k: desc[k] for k in ('role', 'shows', 'binds_to')},
                       'id': w['id'], 'f': str(video), 'k': 'video', 'dur': w['end'] - w['start'],
                       'exists': True, 'tags': [], 'use': '', 'beat': 'any',
                       'source_window': [w['start'], w['end']], 'sampled': 'single-frame',
                       'described_by': 'model'})
    return {'project': 'academic moment retrieval', 'assets': assets}


def binder_predict(query, catalogue, windows, binder):
    assets = binder.load_assets(catalogue)
    idf, _ = binder.build_idf(assets)
    comp = {'type': 'video', 'text': query, 'tags': []}
    scored = [binder.score_asset(comp, a, idf, 0) for a in assets]
    # The unchanged binder's acceptance rule decides usable windows. Adjacent
    # accepted windows become one proposal; rank by mean raw binder score.
    groups = []
    for window, (score, semantic, signals) in zip(windows, scored):
        if score < binder.MIN_BIND or semantic < binder.MIN_SEMANTIC:
            continue
        if groups and groups[-1]['end'] == window['start']:
            groups[-1]['end'] = window['end']
            groups[-1]['scores'].append(score)
        else:
            groups.append({'start': window['start'], 'end': window['end'], 'scores': [score]})
    proposals = [[g['start'], g['end'], sum(g['scores']) / len(g['scores'])] for g in groups]
    proposals.sort(key=lambda w: (-w[2], w[0], w[1]))
    return proposals[:10], [{'id': w['id'], 'score': s, 'semantic': sem, 'signals': sig}
                           for w, (s, sem, sig) in zip(windows, scored)]


def direct_prompt(case):
    return (f'Find all moments matching this request in the supplied sampled video: {case["query"]}\n'
            f'The video lasts {case["duration"]} seconds. Each labelled tile samples the centre of a '
            'two-second interval. Return up to ten complete contiguous matching intervals, '
            'including their full visible extent, ranked by descending confidence. '
            'Use the supplied interval boundaries. Return only '
            '{"windows":[[start_seconds,end_seconds,confidence],...]}. '
            'Confidence must be in [0,1]. If nothing matches, return an empty list.')


def direct_prediction(answer, case, windows):
    prediction = validate_spans(answer['windows'], case['duration'], scored=True)
    if len(prediction) > 10 or any(not 0 <= w[2] <= 1 for w in prediction):
        raise ValueError('invalid number of proposals or confidence')
    boundaries = {w['start'] for w in windows} | {case['duration']}
    if any(w[0] not in boundaries or w[1] not in boundaries for w in prediction):
        raise ValueError('direct proposal is not on the declared 2s grid')
    # Ranking is deterministic serialization of the model's confidence values.
    # Keep coordinates, values and tied order unchanged; never use labels here.
    return sorted(prediction, key=lambda w: -w[2])


def run(root, out, skills, model, max_cost, infer_fn=None):
    call_model = infer_fn or infer
    cases_file = root / 'qvh/inputs/cases.jsonl'
    cases = read_jsonl(cases_file)
    # The inference runner never opens qvh/references or the upstream annotations.
    allowed = {'qid', 'vid', 'query', 'duration'}
    if not cases or any(set(c) != allowed for c in cases):
        raise ValueError('input cases must contain exactly the answer-free fields')
    out.mkdir(parents=True, exist_ok=True)
    sources = [Path(__file__), Path(__file__).with_name('model.py'),
               Path(__file__).with_name('common.py'), Path(skills) / 'real-storyboarding/scripts/bind.py',
               Path(skills) / 'real-storyboarding/scripts/real_core.py']
    manifest = {'dataset': 'QVHighlights', 'split': 'val', 'scope': 'component pilot',
                'inputs_sha256': sha256(cases_file), 'qids': [c['qid'] for c in cases],
                'model': model, 'max_cost_per_call_usd': max_cost,
                'conditions': ['real-binder', 'direct-vision', 'random-window', 'full-video'],
                'source_hashes': {str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p): sha256(p)
                                  for p in sources},
                'protocol': '2s proposals, 1 centre frame/window, visual only; one model call/condition/case',
                'baseline_control': 'same model, sampled images and per-call cost cap; prompts differ by condition'}
    mf = out / 'manifest.json'
    if mf.exists() and json.loads(mf.read_text()) != manifest:
        raise ValueError('run configuration changed; use a new output directory')
    write_json(mf, manifest)
    binder = load_binder(skills)
    results = {name: [] for name in manifest['conditions']}
    for case in cases:
        public = {k: case[k] for k in ('qid', 'vid')}
        case_dir = out / str(case['qid'])
        case_dir.mkdir(exist_ok=True)
        evidence, images = None, None
        error = None
        try:
            video = root / 'qvh/media' / (case['vid'] + '.mp4')
            provenance = json.loads(video.with_suffix('.source.json').read_text())
            if sha256(video) != provenance['sha256']:
                raise ValueError('media hash mismatch')
            evidence = make_sheets(video, case['duration'], case_dir / 'evidence')
            images = [case_dir / 'evidence' / s['file'] for s in evidence['sheets']]
        except Exception as exc:
            error = f'{type(exc).__name__}: {exc}'
        for name in ('real-binder', 'direct-vision'):
            row = {**public, 'pred_relevant_windows': []}
            try:
                if error:
                    raise RuntimeError(error)
                if name == 'real-binder':
                    answer = call_model(catalog_prompt(evidence['windows']), images, case_dir / name,
                                   model, max_cost)
                    cat = catalogue_from(answer, evidence['windows'], video)
                    from real_core import validate_document
                    validate_document(cat, 'asset-catalog')
                    write_json(case_dir / 'asset-catalog.json', cat)
                    prediction, details = binder_predict(case['query'], cat, evidence['windows'], binder)
                    write_json(case_dir / 'binding-evidence.json', details)
                else:
                    answer = call_model(direct_prompt(case), images, case_dir / name, model, max_cost)
                    prediction = direct_prediction(answer, case, evidence['windows'])
                row['pred_relevant_windows'] = prediction
            except Exception as exc:
                row['error'] = f'{type(exc).__name__}: {exc}'
            results[name].append(row)
            write_jsonl(out / (name + '.jsonl'), results[name])
            print(case['qid'], name, 'FAILED: ' + row['error'] if row.get('error') else
                  f'{len(row["pred_relevant_windows"])} proposals', flush=True)
        rng = random.Random(hashlib.sha256(f'random-v1:{case["qid"]}'.encode()).digest())
        grid = list(range(0, math.ceil(case['duration']), 2)) + [case['duration']]
        start, end = sorted(rng.sample(grid, 2))
        results['random-window'].append({**public, 'pred_relevant_windows': [[start, end, 1.0]]})
        results['full-video'].append({**public, 'pred_relevant_windows': [[0, case['duration'], 1.0]]})
        for name in ('random-window', 'full-video'):
            write_jsonl(out / (name + '.jsonl'), results[name])
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--skills', type=Path, default=DEFAULT_SKILLS)
    p.add_argument('--model', default='claude-sonnet-5-5')
    p.add_argument('--max-cost-per-call', type=float, default=1.0)
    a = p.parse_args()
    run(a.root.resolve(), a.out.resolve(), a.skills.resolve(), a.model, a.max_cost_per_call)


if __name__ == '__main__':
    main()
