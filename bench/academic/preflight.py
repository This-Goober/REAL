"""Check frozen public inputs and pinned media URLs without model inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error
import urllib.request

from .common import read_jsonl, sha256, write_json
from .compare import source_id
from .data import LOCK, media_url


def media_head(vid, mirrors):
    attempts = []
    for mirror in mirrors:
        url = media_url(mirror, vid)
        try:
            request = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'REAL-academic-eval/1'})
            with urllib.request.urlopen(request, timeout=30) as response:
                size = response.headers.get('Content-Length')
                status = response.status
                if status != 200:
                    raise ValueError('unexpected status: ' + str(status))
                return dict(vid=vid, available=True, url=url, status=status,
                            reported_bytes=int(size) if size is not None else None,
                            previous_attempts=attempts)
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            # Retain the pinned URL, not transient signed redirect credentials.
            attempts.append(dict(url=url, error=f'{type(exc).__name__}: {exc}'))
    return dict(vid=vid, available=False, attempts=attempts)


def run(cases_file, manifest_file, out, workers=4):
    cases = read_jsonl(cases_file)
    manifest = json.loads(Path(manifest_file).read_text())
    if (not cases or any(set(c) != {'qid', 'vid', 'query', 'duration'} for c in cases)
            or len(cases) != len({c['qid'] for c in cases})):
        raise ValueError('unique answer-free inputs required')
    if (sha256(cases_file) != manifest['inputs_sha256']
            or [c['qid'] for c in cases] != manifest['qids']):
        raise ValueError('inputs differ from frozen selection')
    lock = json.loads(LOCK.read_text())
    vids = list(dict.fromkeys(c['vid'] for c in cases))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(lambda vid: media_head(vid, lock['qvh_video_mirrors']), vids))
    available = {r['vid'] for r in records if r['available']}
    known = [r['reported_bytes'] for r in records if r['available'] and r['reported_bytes'] is not None]
    result = dict(checked_at=datetime.now(timezone.utc).isoformat(),
                  inputs_sha256=sha256(cases_file), selection_manifest_sha256=sha256(manifest_file),
                  mirrors_lock_sha256=sha256(LOCK), n_queries=len(cases), n_video_excerpts=len(vids),
                  source_hashes={name: sha256(Path(__file__).with_name(name))
                                 for name in ['preflight.py', 'data.py']},
                  n_original_sources=len({source_id(c['vid']) for c in cases}),
                  available_excerpts=len(available), available_queries=sum(c['vid'] in available for c in cases),
                  known_bytes_total=sum(known), available_excerpts_without_size=len(available)-len(known),
                  media_downloaded=False, new_model_calls=0,
                  note='HTTP availability only; media hashes and duration must be verified after download. '
                       'Unavailable inputs remain selected; no replacements.',
                  media=records)
    write_json(out, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.cases, args.manifest, args.out)
    print(json.dumps({k: v for k, v in result.items() if k != 'media'}, indent=2))
