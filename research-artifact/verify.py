"""Verify an extracted review artifact using only the Python standard library."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def checked(path, expected):
    if not path.is_file() or path.is_symlink():
        raise ValueError('missing file or symlink: ' + str(path))
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('hash mismatch: ' + str(path))


def main():
    manifest = json.loads((ROOT / 'ARTIFACT-MANIFEST.json').read_text())
    for name, record in manifest['files'].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or '..' in Path(name).parts:
            raise ValueError('invalid manifest path')
        checked(path, record['sha256'])
    counts = {}
    for name in ['assembly-initial', 'assembly-development', 'assembly-validation']:
        evidence = json.loads((ROOT / f'experiments/E10-submission-validation/results/{name}/manifest.json').read_text())
        for relative, expected in evidence['snapshot_sha256'].items():
            checked(ROOT / 'frozen' / name / relative, expected)
        counts[name] = len(evidence['snapshot_sha256'])
    for relative, expected in evidence['pool_sha256'].items():
        checked(ROOT / 'artifact-data/synthetic-pool' / relative, expected)
    lock = json.loads((ROOT / 'bench/academic/sources.lock.json').read_text())
    for record in lock['files']:
        if record['path'].startswith('sources/qvh/'):
            checked(ROOT / 'artifact-data' / record['path'], record['sha256'])
    print(json.dumps(dict(files_verified=len(manifest['files']), frozen_snapshots=counts,
                          synthetic_pool_verified=True, official_sources_verified=True), indent=2))


if __name__ == '__main__':
    main()
