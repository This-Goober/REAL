"""Frozen, structural-only assembly study. No rendering or model inference.

Run from the repository root:
  python bench/assembly_study.py OUT --pool bench/work/pool --n 30

Each invocation requires a new output directory. Skills and scoring code are
snapshotted before execution; all selected seeds, including failures, remain
in the result. This supplements, rather than replaces, the pixel benchmark.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import tarfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = '16c34d59f7db1ca0618e35fbcdaaf30a4494c952'
SKILLS = Path('skills/batch-2/skills')
METRICS = ('f1@0.5', 'f1@1.0', 'frame_exact_acc', 'boundaries_within_1f', 'time_coverage')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashes(root):
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def copy_baseline(out, source=None):
    if source is None:
        archive = subprocess.check_output(['git', '-C', str(ROOT), 'archive', BASE, str(SKILLS)])
        with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
            tf.extractall(out, filter='data')
        return
    # A review ZIP has no Git history. Accept only the exact baseline tree
    # recorded by the saved E10 validation, including schemas and skill text.
    manifest = json.loads((ROOT / 'experiments/E10-submission-validation/results/'
                          'assembly-validation/manifest.json').read_text())
    expected = {name.removeprefix('baseline/'): value
                for name, value in manifest['snapshot_sha256'].items() if name.startswith('baseline/')}
    if manifest['base'] != BASE or not expected or hashes(source) != expected:
        raise ValueError('baseline snapshot differs from the recorded E10 baseline')
    shutil.copytree(source, out, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def estimate(values):
    """Seed-level percentile bootstrap; the seed is the independent unit."""
    x = np.asarray(values, dtype=float)
    if len(x) == 0:
        raise ValueError('cannot summarize an empty experiment')
    rng = np.random.default_rng(20261018)
    means = x[rng.integers(0, len(x), size=(10000, len(x)))].mean(axis=1)
    return {'mean': float(x.mean()), 'ci95': np.quantile(means, [.025, .975]).tolist()}


def summarize(rows, seeds):
    conditions = ('published', 'revised', 'estimated')
    by = {(r['seed'], r['condition']): r for r in rows}
    if len(by) != len(rows) or set(by) != {(s, c) for s in seeds for c in conditions}:
        raise ValueError('missing or duplicate seed/condition results')
    result = {'n_seeds': len(seeds), 'units': 'fractions',
              'uncertainty': '10000 paired seed bootstrap draws; percentile 95% CI; seed=20261018',
              'failure_policy': 'failed pipelines or reads receive zero for all reported quality metrics',
              'conditions': {}, 'paired_differences': {}}
    for c in conditions:
        group = [by[s, c] for s in seeds]
        result['conditions'][c] = {
            'pipeline_pass': sum(r['pipeline_ok'] for r in group),
            'scored': sum(r.get('structural') is not None for r in group),
            'all_placements_exact': sum(r['quality']['f1@1.0'] == 1 for r in group),
            'metrics': {m: estimate([r['quality'][m] for r in group]) for m in METRICS}}
    for c in ('published', 'estimated'):
        result['paired_differences']['revised-minus-' + c] = {
            m: estimate([by[s, 'revised']['quality'][m] - by[s, c]['quality'][m] for s in seeds])
            for m in METRICS}
    return result


def one(seed, out, pool):
    # Imports resolve to the frozen harness, installed at the front of sys.path.
    import project
    import run_real
    import fcpxml_edl
    import metrics
    pdir = out / ('p%03d' % seed)
    beats = random.Random(seed * 7919).randint(4, 8)
    _, revisions = project.build_project(str(pdir), str(pool), seed, beats, 'normal')
    truth = json.loads((pdir / 'truth.json').read_text())
    rows = []
    for condition, clock, tree in [('published', 'measured', 'baseline'),
                                    ('revised', 'measured', 'current'),
                                    ('estimated', 'estimated', 'current')]:
        start = time.monotonic()
        row = dict(seed=seed, condition=condition, beats=beats, creator_revisions=revisions,
                   pipeline_ok=False, structural=None, quality={m: 0.0 for m in METRICS})
        try:
            rec = run_real.run(str(pdir), clock, str(out / 'snapshot' / tree / SKILLS))
            row.update(pipeline_ok=rec['ok'], pipeline_error=rec['error'])
            dest = pdir / ('cond-' + condition)
            (pdir / ('real-' + clock)).rename(dest)
            if (dest / 'timeline.fcpxml').exists():
                edl = fcpxml_edl.parse(str(dest / 'timeline.fcpxml'))
                save(dest / 'edl.json', edl)
                row['structural'] = metrics.structural(truth, edl)
                if rec['ok']:
                    row['quality'] = {m: row['structural'][m] for m in METRICS}
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
        row['wall_s'] = round(time.monotonic() - start, 3)
        rows.append(row)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out', type=Path)
    p.add_argument('--pool', required=True, type=Path)
    p.add_argument('--n', type=int, default=30)
    p.add_argument('--seed0', type=int, default=1)
    p.add_argument('--jobs', type=int, default=3)
    p.add_argument('--baseline-snapshot', type=Path,
                   help='Baseline root from the review artifact; verified against E10 hashes')
    a = p.parse_args()
    if a.n < 1 or a.jobs < 1:
        p.error('--n and --jobs must be positive')
    out, pool = a.out.resolve(), a.pool.resolve()
    out.mkdir(parents=True, exist_ok=False)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    snapshot = out / 'snapshot'
    current = snapshot / 'current' / SKILLS
    shutil.copytree(ROOT / SKILLS, current,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    copy_baseline(snapshot / 'baseline', a.baseline_snapshot)
    shutil.copytree(ROOT / 'bench', snapshot / 'harness',
                    ignore=shutil.ignore_patterns('work', '__pycache__', '*.pyc'))
    sys.path.insert(0, str(snapshot / 'harness'))
    seeds = list(range(a.seed0, a.seed0 + a.n))
    before = hashes(snapshot)
    head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True)
    manifest = {'protocol': 'REAL-structural-assembly-v1', 'seeds': seeds,
                'scope': 'synthetic structural conformance; no pixel or native-editor validation',
                'base': BASE, 'head': head.stdout.strip() if head.returncode == 0 else None,
                'baseline_source': 'verified snapshot' if a.baseline_snapshot else 'git archive',
                'snapshot_sha256': before, 'pool_sha256': hashes(pool),
                'python': sys.version, 'platform': platform.platform(),
                'packages': subprocess.check_output([sys.executable, '-c',
                    'import importlib.metadata,json; print(json.dumps({d.metadata["Name"]:d.version for d in importlib.metadata.distributions()}))'], text=True).strip(),
                'ffmpeg': subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0],
                'argv': sys.argv, 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    save(out / 'manifest.json', manifest)
    rows = []
    with (out / 'results.jsonl').open('w') as f, ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for group in ex.map(lambda s: one(s, out, pool), seeds):
            rows.extend(group)
            for row in group:
                f.write(json.dumps(row, allow_nan=False) + '\n')
            f.flush()
            print('seed', group[0]['seed'], [(r['condition'], round(r['quality']['f1@1.0'], 4)) for r in group], flush=True)
    if hashes(snapshot) != before:
        raise RuntimeError('snapshot changed during evaluation; results are invalid')
    manifest.update(snapshot_unchanged=True, results_sha256=digest(out / 'results.jsonl'))
    save(out / 'manifest.json', manifest)
    save(out / 'summary.json', summarize(rows, seeds))


if __name__ == '__main__':
    main()
