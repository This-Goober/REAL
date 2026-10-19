"""Offline, immutable replay of saved one-shot compiler outputs; no model API.

python bench/replay_oneshot.py OUT --saved bench/work/full \
  --real bench/work/submission-assembly-final --dtd /path/FCPXMLv1_13.dtd
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODELS = ('claude-sonnet-5-5', 'claude-opus-5-5', 'claude-fable-5-1')
CONDITIONS = ('real-revised-measured',) + tuple('oneshot-' + m + suffix
                for suffix in ('', '-norules') for m in MODELS)
INPUTS = ('NOTEBOOK.md', 'revisions.txt', 'asset-catalog.json', 'measured.json', 'spec.json', 'truth.json')
SCORES = ('f1@1.0', 'f1@0.5', 'frame_exact_acc')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def audit_prompt(project, folder):
    """Compare actual retained inputs, not a fresh prompt with today's notes."""
    from oneshot_llm import extract_xml
    text = (folder / 'prompt.txt').read_text()
    notebook = text.split("NOTEBOOK.md (the creator's script):\n----------------------------------\n", 1)[1].split('\n----------------------------------', 1)[0]
    words = text.split('MEASURED WORD TIMES (index:word[start-end] in seconds):\n', 1)[1].split('\n\nCREATOR REVISIONS:', 1)[0]
    wt = json.loads((project / 'measured.json').read_text())['words']
    expected_words = ' '.join('%d:%s[%.3f-%.3f]' % (w['i'], w['w'], w['start'], w['end']) for w in wt)
    # The stored measured inputs already use millisecond precision: formatting
    # here must not hide a mismatch against higher-precision reference inputs.
    precise = all(float('%.3f' % w[k]) == w[k] for w in wt for k in ('start', 'end'))
    revisions = text.split('CREATOR REVISIONS:\n', 1)[1].split('\n\n', 1)[0]
    cat = json.loads((project / 'asset-catalog.json').read_text())
    expected_cat = '\n'.join('- %s: %s (%s%s)' % (a['id'], a['f'], a['k'],
        ', %.1fs, %dx%d' % (a['dur'], a['w'], a['h']) if a['k'] == 'video'
        else ', %dx%d' % (a['w'], a['h'])) for a in cat['assets'])
    actual_cat = text.split('<relative path>):\n', 1)[1].split('\n\nMEASURED WORD TIMES', 1)[0]
    response_xml = extract_xml((folder / 'response.txt').read_text())
    xml = folder / 'timeline.fcpxml'
    extracted_matches = (xml.read_text() == response_xml) if xml.exists() else response_xml is None
    rec = json.loads((folder / 'run.json').read_text())
    model = folder.name.removeprefix('oneshot-').removesuffix('-norules')
    checks = dict(notebook=notebook == (project / 'NOTEBOOK.md').read_text(),
        word_times=words == expected_words and precise, catalogue=actual_cat == expected_cat,
        revisions=revisions == ((project / 'revisions.txt').read_text().strip() or '(none)'),
        response_extraction=extracted_matches, model=rec.get('model') == model,
        xml_presence=bool(rec.get('got_xml')) == xml.exists(),
        format_notes=('FCPXML RULES (these are' in text) == (not folder.name.endswith('-norules')))
    return dict(passed=all(checks.values()), checks=checks)


def reader_coverage(xml):
    """Reject unsupported timeline structures before the small reader drops them."""
    root = ET.parse(xml).getroot()
    spine = root.find('.//sequence/spine')
    if spine is None:
        raise ValueError('missing sequence spine')
    supported = {'gap', 'asset-clip', 'video', 'title'}
    issues = []
    for item in spine:
        if item.tag not in supported:
            issues.append('spine:' + item.tag)
        for child in item:
            if child.get('lane') is not None and int(child.get('lane')) > 0:
                if child.tag not in supported:
                    issues.append('connected:' + child.tag)
                if any(e.get('lane') is not None for e in child):
                    issues.append('nested connected clips')
    if len(root.findall('.//sequence')) != 1:
        issues.append('multiple sequences')
    return issues


def score_case(seed, condition, project, validator, dtd):
    import fcpxml_edl
    import metrics
    folder = project / condition
    xml = folder / 'timeline.fcpxml'
    row = dict(seed=seed, condition=condition, available=xml.exists(), parsed=False,
               dtd_valid=False, semantic_valid=False, reader_coverage_issues=[],
               quality={m: 0.0 for m in SCORES}, valid_quality={m: 0.0 for m in SCORES})
    if condition != CONDITIONS[0]:
        row['input_audit'] = audit_prompt(project, folder)
        if not row['input_audit']['passed']:
            raise ValueError('Unmatched retained prompt/reference or response: ' + str(folder))
        rec = json.loads((folder / 'run.json').read_text())
        row.update(recorded_cli_model=rec.get('model'), recorded_wall_s=rec.get('wall_s'),
                   recorded_usage_valuation_usd=rec.get('cost_usd'), recorded_usage=rec.get('usage'))
    if not xml.exists():
        row['failure'] = 'missing XML in retained response'
        return row
    validation = subprocess.run([sys.executable, str(validator), str(xml)], capture_output=True, text=True)
    row['semantic_valid'] = validation.returncode == 0
    row['semantic_errors'] = [line for line in validation.stdout.splitlines() if line.startswith('ERROR')]
    row['semantic_warning_count'] = sum(line.startswith('WARN') for line in validation.stdout.splitlines())
    if validation.returncode and not row['semantic_errors']:
        row['semantic_process_error'] = validation.stderr[-2000:]
    schema = subprocess.run(['xmllint', '--nonet', '--noout', '--dtdvalid', str(dtd), str(xml)], capture_output=True, text=True)
    row['dtd_valid'] = schema.returncode == 0
    row['dtd_diagnostics'] = schema.stderr.replace(str(xml), xml.name).strip() if schema.returncode else ''
    try:
        row['reader_coverage_issues'] = reader_coverage(xml)
        if row['reader_coverage_issues']:
            raise ValueError('unsupported reader constructs: ' + str(row['reader_coverage_issues']))
        edl = fcpxml_edl.parse(xml)
        truth = json.loads((project / 'truth.json').read_text())
        if (edl['fps'], edl['w'], edl['h']) != (truth['fps'], truth['w'], truth['h']):
            raise ValueError('sequence frame rate or dimensions differ from reference')
        score = metrics.structural(truth, edl)
        row.update(parsed=True, structural=score, quality={m: score[m] for m in SCORES})
        if row['dtd_valid'] and row['semantic_valid']:
            row['valid_quality'] = row['quality'].copy()
    except (ValueError, KeyError, TypeError, AttributeError, ET.ParseError, ZeroDivisionError) as exc:
        row['failure'] = type(exc).__name__ + ': ' + str(exc)
    return row


def estimate(values):
    x = np.array(values, dtype=float)
    rng = np.random.default_rng(20261018)
    boot = x[rng.integers(0, len(x), size=(10000, len(x)))].mean(axis=1)
    return dict(mean=float(x.mean()), ci95=np.quantile(boot, [.025, .975]).tolist())


def summarize(rows, seeds):
    by = {(r['seed'], r['condition']): r for r in rows}
    if len(by) != len(rows) or set(by) != {(s, c) for s in seeds for c in CONDITIONS}:
        raise ValueError('Expected exactly one result for every selected seed and condition')
    out = dict(n_seeds=len(seeds), conditions={}, paired_real_minus_model={},
               inference='retrospective development comparison; pointwise exploratory intervals',
               bootstrap='10000 paired project-seed draws, percentile 95%, seed 20261018',
               raw_failure_policy='zero for missing or unparseable XML; parsable invalid XML retains temporal scores',
               gated_failure_policy='zero unless both DTD and semantic validation pass')
    for c in CONDITIONS:
        group = [by[s, c] for s in seeds]
        vals = [r.get('recorded_usage_valuation_usd') for r in group]
        out['conditions'][c] = dict(outputs=sum(r['available'] for r in group),
            parsed=sum(r['parsed'] for r in group), dtd_valid=sum(r['dtd_valid'] for r in group),
            semantic_valid=sum(r['semantic_valid'] for r in group),
            both_valid=sum(r['dtd_valid'] and r['semantic_valid'] for r in group),
            all_exact=sum(r['quality']['f1@1.0'] == 1 for r in group),
            valid_all_exact=sum(r['valid_quality']['f1@1.0'] == 1 for r in group),
            raw={m: estimate([r['quality'][m] for r in group]) for m in SCORES},
            validity_gated={m: estimate([r['valid_quality'][m] for r in group]) for m in SCORES},
            recorded_attempt_valuation_usd=sum(v for v in vals if v is not None) if any(v is not None for v in vals) else None,
            failure_counts=dict(Counter(r['failure'] for r in group if r.get('failure'))))
        if c != CONDITIONS[0]:
            out['paired_real_minus_model'][c] = {field: estimate([
                by[s, CONDITIONS[0]][field]['f1@1.0'] - by[s, c][field]['f1@1.0'] for s in seeds])
                for field in ('quality', 'valid_quality')}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--saved', type=Path, required=True)
    parser.add_argument('--real', type=Path, required=True)
    parser.add_argument('--dtd', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    snapshot = out / 'snapshot'
    code = snapshot / 'code'; code.mkdir(parents=True)
    for name in ('replay_oneshot.py', 'fcpxml_edl.py', 'metrics.py', 'oneshot_llm.py', 'project.py'):
        shutil.copy2(ROOT / 'bench' / name, code / name)
    shutil.copy2(ROOT / 'skills/batch-2/skills/real-compile/scripts/validate.py', code / 'validate.py')
    shutil.copy2(args.dtd, snapshot / 'fcpxml.dtd')
    seeds = list(range(1, 31))
    for s in seeds:
        source = args.saved / ('p%03d' % s); target = snapshot / 'inputs' / source.name
        target.mkdir(parents=True)
        real = args.real / source.name
        for name in INPUTS:
            if name != 'asset-catalog.json' and (source / name).read_bytes() != (real / name).read_bytes():
                raise ValueError('E10 project differs: ' + str(source / name))
            shutil.copy2(source / name, target / name)
        dest = target / CONDITIONS[0]; dest.mkdir()
        for name in ('timeline.fcpxml', 'run.json'):
            shutil.copy2(real / 'cond-revised' / name, dest / name)
        for c in CONDITIONS[1:]:
            (target / c).mkdir()
            for name in ('prompt.txt', 'response.txt', 'run.json', 'timeline.fcpxml'):
                file = source / c / name
                if file.exists():shutil.copy2(file, target / c / name)
    before = inventory(snapshot)
    manifest = dict(protocol='E03-offline-replay-v1', seeds=seeds, conditions=CONDITIONS,
        scope='retrospective structural model-as-compiler comparison; no new inference',
        snapshot_sha256=before, python=sys.version, platform=platform.platform(),
        numpy=np.__version__, saved_root=str(args.saved.resolve()), real_root=str(args.real.resolve()),
        real_e10_manifest_sha256=sha(args.real / 'manifest.json'),
        current_git_head=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip())
    save(out / 'manifest.json', manifest)
    # Launch the frozen scoring source so every executed scorer byte is recorded.
    subprocess.run([sys.executable, str(code / 'replay_oneshot.py'), '--worker', str(out)], check=True)
    if inventory(snapshot) != before:
        raise ValueError('Scoring snapshot changed during replay')
    manifest.update(snapshot_unchanged=True, results_sha256=sha(out / 'results.jsonl'), summary_sha256=sha(out / 'summary.json'))
    save(out / 'manifest.json', manifest)


def worker(out):
    snap = out / 'snapshot'
    manifest = json.loads((out / 'manifest.json').read_text())
    jobs = [(s, c, snap / 'inputs' / ('p%03d' % s), snap / 'code/validate.py', snap / 'fcpxml.dtd')
            for s in manifest['seeds'] for c in CONDITIONS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda a: score_case(*a), jobs))
    with (out / 'results.jsonl').open('w') as f:
        for row in rows:f.write(json.dumps(row, allow_nan=False) + '\n')
    summary = summarize(rows, manifest['seeds'])
    save(out / 'summary.json', summary)
    for c, r in summary['conditions'].items():
        print(c, 'exact', r['all_exact'], 'F1', round(r['raw']['f1@1.0']['mean'], 4), 'valid', r['both_valid'], flush=True)


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':worker(Path(sys.argv[2]))
    else:main()
