"""Audit the saved E10 evidence and its match to the current implementation."""
import hashlib
import json
from pathlib import Path

from bench.assembly_study import summarize

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'experiments/E10-submission-validation/results'


def read_rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def main():
    checked = {}
    for name in ('assembly-initial','assembly-development','assembly-validation'):
        d = RESULTS / name
        manifest = json.loads((d/'manifest.json').read_text())
        assert manifest['snapshot_unchanged'], name
        assert hashlib.sha256((d/'results.jsonl').read_bytes()).hexdigest() == manifest['results_sha256'], name
        computed = summarize(read_rows(d/'results.jsonl'), manifest['seeds'])
        assert computed == json.loads((d/'summary.json').read_text()), name
        checked[name] = len(manifest['seeds'])
    m = json.loads((RESULTS/'assembly-validation/manifest.json').read_text())
    files = 0
    for relative, expected in m['snapshot_sha256'].items():
        if relative.startswith('current/'):
            p = ROOT / relative.removeprefix('current/')
            assert hashlib.sha256(p.read_bytes()).hexdigest() == expected, str(p)
            files += 1
    consumed = read_rows(RESULTS/'academic/consumed-cases.jsonl')
    next_cases = read_rows(RESULTS/'academic/next100-cases.jsonl')
    source = lambda r: r['vid'].rsplit('_',2)[0]
    assert len(next_cases) == len({r['qid'] for r in next_cases}) == 100
    assert not {source(r) for r in consumed} & {source(r) for r in next_cases}
    assert all(set(r)=={'qid','vid','query','duration'} for r in next_cases)
    result = dict(assembly_seed_counts=checked,current_skill_files_verified=files,
                  next100_source_disjoint=True,next100_answer_free=True)
    (RESULTS/'evidence-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
