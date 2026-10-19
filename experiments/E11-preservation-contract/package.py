"""Freeze the complete offline E11/unified-source evidence for author review."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'REAL-preservation/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(out):
    if out.exists():
        raise ValueError('refusing to overwrite a versioned evidence package')
    experiment = ROOT / 'experiments/E11-preservation-contract'
    compact = json.loads((experiment / 'SHA256SUMS.json').read_text())
    for name, expected in compact.items():
        if sha((experiment / name).read_bytes()) != expected:
            raise ValueError('compact record changed after checksums: ' + name)
    roots = {
        'e11/control': ROOT / 'bench/work/preservation-contract-20261018-control-isolated',
        'e11/corrected': ROOT / 'bench/work/preservation-contract-20261018-corrected-isolated',
        'unified': ROOT / 'bench/work/submission-unified-snapshot-20261018'}
    for key in ('e11/control', 'e11/corrected'):
        root = roots[key]
        manifest = json.loads((root / 'manifest.json').read_text())
        assert manifest['status'] == 'complete' and manifest['inputs_and_source_unchanged']
        for name, expected in manifest['inputs_and_source_sha256'].items():
            assert sha((root / name).read_bytes()) == expected, (key, name)
        assert sha((root / 'results.jsonl').read_bytes()) == manifest['results_sha256']
        assert sha((root / 'summary.json').read_bytes()) == manifest['summary_sha256']
    source = json.loads((roots['unified'] / 'source-manifest.json').read_text())
    candidate = roots['unified'] / 'skills/batch-2/skills'
    for name, expected in source['pipeline_files'].items():
        assert sha((candidate / name).read_bytes()) == expected, name
    files = {}

    def add(name, path):
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError('unsafe evidence input: ' + str(path))
        if name in files:
            raise ValueError('duplicate archive name: ' + name)
        files[name] = path

    for prefix, root in roots.items():
        for path in sorted(root.rglob('*')):
            if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts:
                add(prefix + '/' + path.relative_to(root).as_posix(), path)
    for name in ('preservation_study.py', 'test_preservation_study.py', 'audit_preservation.py'):
        add('bench/' + name, ROOT / 'bench' / name)
    for path in sorted(experiment.rglob('*')):
        if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts:
            add('experiment/' + path.relative_to(experiment).as_posix(), path)
    readme = '''# REAL preservation and unified-source evidence

Internal author-review/reproduction package, 18 October 2026. It contains
machine paths and recorded provenance; it is not an anonymous supplement.
No model, paid service or native editor is needed to reproduce these checks.

The final corrected pipeline is unified/skills/batch-2/skills. Its 67-file
inventory is in unified/source-manifest.json. Reference/scoring sources retain
the original E10/E03 bytes. Read experiment/README.md and the protocols first.
The original failing results, setup failure and small changed development
coverage diagnostic are retained. These are reused regression cohorts.

Use Python 3.13 with NumPy 2.5.4 and Pillow 13.0.0, plus FFmpeg/FFprobe and
libxml2's xmllint on PATH. Run from this package root. Existing directories
are immutable inputs; choose new output paths:

    python -B -m unittest bench.test_preservation_study
    python -B -m bench.audit_preservation e11/control --out control-audit.json
    python -B -m bench.audit_preservation e11/corrected --out corrected-audit.json
    python -B bench/preservation_study.py --projects e11/control/inputs \\
      --pool e11/control/inputs/media --candidate-skills unified/skills/batch-2/skills \\
      --out new-retiming --jobs 3
    python -B unified/bench/assembly_study.py new-assembly \\
      --pool e11/control/inputs/media --n 100 --seed0 1001 --jobs 3 \\
      --baseline-snapshot e11/control/inputs/snapshot/baseline
    python -B unified/oneshot-replay/snapshot/code/replay_oneshot.py \\
      --worker "$PWD/unified/oneshot-replay"

The last command only re-scores saved outputs. It never invokes a model.
Generated silent audio is retained per export. Per-project media symlinks
are omitted; the hash-verified media pool is in each E11 input directory.
Rebuilding projects through the harness creates their new media references.
Past absolute paths in recorded XML/logs document provenance; the read-only
audits use identities/boundaries and do not require those old paths to exist.

Compare new results with the retained JSON summaries and source inventories.
Source or result changes require a new run; do not relabel an old receipt.
The paper and author approval are supplied separately.
'''.encode()
    records = {}
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in sorted(files.items()):
            data = path.read_bytes()
            archive.writestr(PREFIX + name, data)
            records[name] = dict(sha256=sha(data), bytes=len(data))
        archive.writestr(PREFIX + 'README.md', readme)
        records['README.md'] = dict(sha256=sha(readme), bytes=len(readme))
        manifest = dict(format='REAL-preservation-evidence-v1', date='2026-10-18',
                        status='internal author-review evidence; not anonymous or submitted',
                        pipeline_source_id=source['source_id'], files=records)
        archive.writestr(PREFIX + 'MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    checksum = sha(out.read_bytes())
    out.with_suffix('.zip.sha256').write_text(checksum + '  ' + out.name + '\n')
    print(json.dumps(dict(path=str(out), bytes=out.stat().st_size, sha256=checksum,
                          files=len(records)), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    build(parser.parse_args().out.resolve())
