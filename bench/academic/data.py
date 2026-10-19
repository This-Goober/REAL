"""Fetch pinned annotations/evaluator and create answer-free evaluation inputs."""
import argparse
import hashlib
import json
from pathlib import Path

from .common import download, read_jsonl, sha256, write_json, write_jsonl

LOCK = Path(__file__).with_name('sources.lock.json')
SEED = 'real-academic-pilot-v1'


def fetch(root):
    lock = json.loads(LOCK.read_text())
    for item in lock['files']:
        digest = download(item['url'], root / item['path'], item['sha256'])
        print(item['path'], digest, flush=True)
    write_json(root / 'sources.lock.json', lock)


def prepare_qvh(root, limit=5, seed=SEED, exclude_inputs=None):
    source = root / 'sources/qvh/data/highlight_val_release.jsonl'
    rows = read_jsonl(source)
    if len({r['qid'] for r in rows}) != len(rows):
        raise ValueError('duplicate query ids in source')
    # Select using identity only, before inspecting videos, answers, or results.
    rows = sorted(rows, key=lambda r: hashlib.sha256(f'{seed}:{r["qid"]}'.encode()).hexdigest())
    if limit < 0:
        raise ValueError('limit must be >= 0 (zero means the full validation split)')
    excluded = {r['vid'].rsplit('_', 2)[0] for r in read_jsonl(exclude_inputs)} if exclude_inputs else set()
    eligible = [r for r in rows if r['vid'].rsplit('_', 2)[0] not in excluded]
    selected = eligible[:limit] if limit else eligible
    inputs = [{k: r[k] for k in ('qid', 'vid', 'query', 'duration')} for r in selected]
    write_jsonl(root / 'qvh/inputs/cases.jsonl', inputs)
    write_jsonl(root / 'qvh/references/answers.jsonl', selected)
    write_json(root / 'qvh/manifest.json', {
        'dataset': 'QVHighlights', 'split': 'val', 'seed': seed,
        'selection': 'sha256(seed:qid), ascending after excluding listed source videos; no replacement for unavailable videos',
        'excluded_source_videos': sorted(excluded),
        'n_selected': len(selected), 'n_split': len(rows), 'qids': [r['qid'] for r in inputs],
        'source_sha256': sha256(source), 'inputs_sha256': sha256(root / 'qvh/inputs/cases.jsonl'),
        'references_sha256': sha256(root / 'qvh/references/answers.jsonl'),
        'status': 'source-disjoint validation subset' if excluded else ('development pilot' if limit else 'full validation; not held-out test')})
    return inputs


def prepare_medit(root):
    import pyarrow.parquet as pq
    source = root / 'sources/medit/train.parquet'
    rows = pq.read_table(source).to_pylist()
    groups = {}
    for r in rows:
        # The HF split happens to be called train; these are evaluation references.
        key = (r['video_id'], r['message'])
        groups.setdefault(key, []).append(r)
    inputs, refs, timebases = [], [], {}
    for (vid, message), annotations in sorted(groups.items()):
        qid = hashlib.sha256(json.dumps([vid, message]).encode()).hexdigest()[:16]
        if len(annotations) != 3 or {r['annotator_index'] for r in annotations} != {0, 1, 2}:
            raise ValueError('expected three distinct editors for ' + qid)
        public = {'qid': qid, 'vid': vid, 'query': message}
        inputs.append(public)
        refs.append({**public, 'references': [
            {'annotator_index': r['annotator_index'], 'timecodes': r['segments']}
            for r in sorted(annotations, key=lambda x: x['annotator_index'])]})
        basis = timebases.setdefault(vid, {'fps': None, 'duration': None, 'provenance': '',
                                          'observed_max_frame_field_by_editor': {}})
        for annotation in annotations:
            editor = str(annotation['annotator_index'])
            maximum = max(int(t.rsplit(':', 1)[1]) for span in annotation['segments'] for t in span)
            old = basis['observed_max_frame_field_by_editor'].get(editor, 0)
            basis['observed_max_frame_field_by_editor'][editor] = max(old, maximum)
    write_jsonl(root / 'medit/inputs/cases.jsonl', inputs)
    write_jsonl(root / 'medit/references/answers.jsonl', refs)
    write_json(root / 'medit/timebases.template.json', timebases)
    write_json(root / 'medit/manifest.json', {
        'dataset': 'MEDit-Bench', 'hf_split_name': 'train', 'usage': 'evaluation only',
        'videos': len({r['vid'] for r in inputs}), 'cases': len(inputs), 'references': len(rows),
        'cuts': sum(len(r['segments']) for r in rows),
        'videos_with_frame_field_above_29': sum(
            max(t['observed_max_frame_field_by_editor'].values()) >= 30 for t in timebases.values()),
        'source_sha256': sha256(source), 'timecodes': 'HH:MM:SS:FF; timebase required; never assume 30fps',
        'inputs_sha256': sha256(root / 'medit/inputs/cases.jsonl'),
        'references_sha256': sha256(root / 'medit/references/answers.jsonl')})
    return inputs


def media_url(mirror, vid):
    # The pinned fallback mirror partitions by lowercase initial, while the
    # video filename itself remains case-sensitive (including YouTube IDs).
    return mirror['template'].format(vid=vid, initial=vid[0].lower())


def fetch_qvh_media(root):
    lock = json.loads(LOCK.read_text())
    rows = read_jsonl(root / 'qvh/inputs/cases.jsonl')
    records = []
    for vid in dict.fromkeys(r['vid'] for r in rows):
        dest = root / 'qvh/media' / (vid + '.mp4')
        errors = []
        for mirror in lock['qvh_video_mirrors']:
            url = media_url(mirror, vid)
            try:
                # Existing bytes must match recorded provenance on resume.
                provenance = dest.with_suffix('.source.json')
                if dest.exists() and not provenance.exists():
                    raise ValueError('media exists without provenance: ' + str(dest))
                old = json.loads(provenance.read_text()) if provenance.exists() else None
                digest = download(url, dest, old['sha256'] if old else None)
                rec = old or {'vid': vid, 'url': url, 'sha256': digest, 'origin': 'community mirror'}
                write_json(provenance, rec)
                records.append({**rec, 'ok': True})
                print('media ready', vid, flush=True)
                break
            except Exception as exc:
                errors.append(str(exc))
        else:
            records.append({'vid': vid, 'ok': False, 'errors': errors})
            print('media unavailable', vid, flush=True)
    write_json(root / 'qvh/media-manifest.json', records)
    return records


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['fetch', 'prepare-qvh', 'prepare-medit', 'media-qvh'])
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--limit', type=int, default=5)
    p.add_argument('--seed', default=SEED)
    p.add_argument('--exclude-inputs', type=Path, help='exclude all original source videos in this public case file')
    a = p.parse_args()
    if a.command == 'fetch': fetch(a.root)
    elif a.command == 'prepare-qvh': print('prepared', len(prepare_qvh(a.root, a.limit, a.seed, a.exclude_inputs)))
    elif a.command == 'prepare-medit': print('prepared', len(prepare_medit(a.root)))
    else: fetch_qvh_media(a.root)


if __name__ == '__main__':
    main()
