"""Offline preservation diagnostics on the frozen E10 validation projects.

No models or native editors are called. Every seed/scale stays in the report.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import platform

ROOT = Path(__file__).resolve().parents[1]
SEEDS = tuple(range(1001, 1101))
SCALES = (('faster', .8), ('slower', 1.2))
CHOICES = ('kind', 'asset', 'content', 'anchor_word', 'anchor_text', 'offset_ms',
           'dur_source', 'dur_s', 'chosen_by', 'style', 'font', 'font_face',
           'font_size', 'color', 'align', 'position', 'fit', 'transform',
           'opacity', 'src_in', 'src_out', 'z', 'base', 'placement',
           'source_component', 'source_text')
CHECKS = ('initial_repair_exact', 'initial_target_correct', 'noop_exact',
          'noop_choices_preserved', 'retimed_exact', 'retimed_choices_preserved',
          'rebuilt_exact', 'rebuilt_choices_preserved', 'compile_deterministic')
INPUTS = ('spec.json', 'measured.json', 'cond-revised/notebook.json',
          'cond-revised/clock.json', 'cond-revised/bindings.json',
          'cond-revised/reel.json', 'cond-revised/timeline.fcpxml')


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def event_key(event):
    return (event['kind'], event.get('asset'),
            ' '.join((event.get('text') or '').lower().split()),
            event['f0'], event['f1'], event.get('src_in', 0))


def compare_edls(expected, actual):
    a = Counter(event_key(e) for e in expected['events'] if e['kind'] != 'gap')
    b = Counter(event_key(e) for e in actual['events'] if e['kind'] != 'gap')
    format_equal = all(expected[key] == actual[key] for key in ('fps', 'w', 'h'))
    return {'exact': a == b and expected['total_f'] == actual['total_f'] and format_equal,
            'missing': sorted((a - b).elements(), key=str),
            'extra': sorted((b - a).elements(), key=str),
            'format_equal': format_equal,
            'expected_total_f': expected['total_f'], 'actual_total_f': actual['total_f']}


def layers(reel):
    items = [item for beat in reel['beats'] for item in beat['layers']]
    result = {item['id']: item for item in items}
    if len(items) != len(result):
        raise ValueError('duplicate layer identity')
    return result


def choice_changes(before, after, fields=CHOICES):
    a, b = layers(before), layers(after)
    changes = []
    for ident, item in a.items():
        if item.get('chosen_by') != 'creator':
            continue
        other = b.get(ident)
        if other is None:
            changes.append({'id': ident, 'field': 'placement', 'before': 'present', 'after': 'missing'})
            continue
        for field in fields:
            if item.get(field) != other.get(field):
                changes.append({'id': ident, 'field': field,
                                'before': item.get(field), 'after': other.get(field)})
    if set(a) != set(b):
        changes.append({'field': 'layer_ids', 'before': sorted(a), 'after': sorted(b)})
    return changes


def selection(spec, seed):
    """Existing repair eligibility and seeded selection; no pipeline imports."""
    words = {w['i']: w for w in spec['word_times']}
    candidates = []
    for bi, beat in enumerate(spec['beats']):
        for oi, overlay in enumerate(beat['overlays']):
            for wi in range(beat['w0'] + 1, beat['w1']):
                if wi == overlay['anchor']:
                    continue
                word = words[wi]
                cut = word['start'] + .4 * (word['end'] - word['start'])
                if cut + overlay['dur'] <= words[beat['w1']]['end'] - .05 and abs(wi - overlay['anchor']) >= 2:
                    candidates.append((bi, oi, wi))
    return random.Random(seed * 31337).choice(candidates) if candidates else None


def summarize(rows, seeds=SEEDS):
    expected = {(seed, name) for seed in seeds for name, _ in SCALES}
    keys = [(row['seed'], row['scale']) for row in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError('missing, duplicate or unexpected seed/scale rows')
    result = {'planned_seeds': len(seeds), 'planned_rows': len(expected), 'scales': {}}
    for name, factor in SCALES:
        group = [r for r in rows if r['scale'] == name]
        result['scales'][name] = {
            'factor': factor, 'denominator': len(seeds),
            'eligible': sum(r.get('eligible') is True for r in group),
            'stage_complete': sum(r.get('status') == 'complete' for r in group),
            'ineligible': sum(r.get('status') == 'ineligible' for r in group),
            'failed': sum(r.get('status') == 'failed' for r in group),
            'checks_passed': {key: sum(r.get(key) is True for r in group) for key in CHECKS},
            'additional_style_by_changed': sum(r.get('additional_style_by_changed') is True for r in group),
            'all_checks_passed': sum(all(r.get(key) is True for key in CHECKS) for r in group)}
    return result


def capture(projects, pool, out, candidate=None):
    manifest = read(projects / 'manifest.json')
    for name, expected in manifest['snapshot_sha256'].items():
        if sha(projects / 'snapshot' / name) != expected:
            raise ValueError('E10 source snapshot mismatch: ' + name)
    for name, expected in manifest['pool_sha256'].items():
        if sha(pool / name) != expected:
            raise ValueError('E10 media mismatch: ' + name)
    dest = out / 'inputs'
    dest.mkdir()
    shutil.copyfile(projects / 'manifest.json', dest / 'manifest.json')
    shutil.copytree(projects / 'snapshot', dest / 'snapshot',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    if candidate is not None:
        current = dest / 'snapshot/current/skills/batch-2/skills'
        shutil.rmtree(current)
        shutil.copytree(candidate, current, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in manifest['pool_sha256']:
        target = dest / 'media' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pool / name, target)
    selected = {}
    for seed in SEEDS:
        source, target = projects / f'p{seed}', dest / f'p{seed}'
        for name in INPUTS:
            file = target / name
            file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, file)
        selected[str(seed)] = selection(read(target / 'spec.json'), seed)
    hashes = {str(p.relative_to(out)): sha(p) for p in dest.rglob('*') if p.is_file()}
    return dest, hashes, selected


class Study:
    def __init__(self, inputs, out):
        self.inputs, self.out = inputs, out
        self.media = inputs / 'media'
        self.skills = inputs / 'snapshot/current/skills/batch-2/skills'
        self.sb = self.skills / 'real-storyboarding/scripts'
        self.co = self.skills / 'real-compile/scripts'
        self.reference = load_module('e11_reference', inputs / 'snapshot/harness/project.py')
        self.reader = load_module('e11_reader', inputs / 'snapshot/harness/fcpxml_edl.py')

    def clipped_fixture(self):
        """A fixed late-then-early revision, separately from the 200 case rows."""
        folder = self.out / 'clipped-recovery'
        folder.mkdir()
        source = self.inputs / 'p1001/cond-revised'
        spec = read(self.inputs / 'p1001/spec.json')
        beat = spec['beats'][0]
        ident = f"{beat['id']}.L2"
        requested = beat['overlays'][0]['dur']
        words = {w['i']: w for w in spec['word_times']}
        late, early = beat['w1'], beat['w0'] + 1
        logs, observations = [], []

        def run(stage, script, *args):
            result = subprocess.run([sys.executable, '-B', str(script), *map(str, args)],
                                    capture_output=True, text=True, timeout=45)
            logs.append(dict(stage=stage, returncode=result.returncode,
                             args=list(map(str, [script, *args])),
                             output=result.stdout + result.stderr))
            if result.returncode:
                raise RuntimeError(stage + ': ' + (result.stdout + result.stderr)[-1500:])

        def move(old, clock, anchor, name):
            revision = folder / (name + '.txt')
            revision.write_text(f"{beat['id']}: L2 anchor = {anchor}\n")
            target = folder / (name + '.json')
            run(name, self.sb / 'revise.py', 'apply', old, revision,
                '-o', target, '--clock', clock)
            return target

        def observe(path, anchor, times, name, clipped):
            wt = {w['i']: w for w in times}
            w = wt[anchor]
            start = w['start'] + .4 * (w['end'] - w['start'])
            end = min(start + requested, wt[beat['w1']]['end'])
            item = layers(read(path))[ident]
            exact = (abs(item['t0'] - start) < 1e-9 and abs(item['t1'] - end) < 1e-9
                     and item.get('dur_s') == requested and item.get('chosen_by') == 'creator'
                     and item['anchor_word'] == anchor)
            duration = item['t1'] - item['t0']
            observations.append(dict(stage=name, requested_s=requested, expected_start_s=start,
                                     expected_end_s=end, actual_start_s=item['t0'], actual_end_s=item['t1'],
                                     visible_s=duration, passed=exact and
                                     (duration < requested - .05 if clipped else abs(duration-requested) < 1e-9)))

        try:
            clock = source / 'clock.json'
            clipped = move(source / 'reel.json', clock, late, 'late')
            observe(clipped, late, spec['word_times'], 'late', True)
            recovered = move(clipped, clock, early, 'early')
            observe(recovered, early, spec['word_times'], 'early', False)
            changed = [{**w, 'start': round(w['start'] * .8, 3),
                        'end': round(w['end'] * .8, 3)} for w in words.values()]
            measured, new_clock = folder / 'measured.json', folder / 'clock.json'
            write(measured, dict(words=changed))
            run('swap-clock', self.sb / 'clock.py', 'swap', clock, measured, '-o', new_clock)
            retimed = folder / 'retimed.json'
            run('retime', self.sb / 'build.py', 'retime', clipped, new_clock, '-o', retimed)
            observe(retimed, late, changed, 'retimed-late', True)
            recovered = move(retimed, new_clock, early, 'retimed-early')
            observe(recovered, early, changed, 'retimed-early', False)
            result = dict(status='complete', passed=all(o['passed'] for o in observations),
                          target=ident, observations=observations)
        except Exception as error:
            result = dict(status='failed', passed=False, error=str(error), observations=observations)
        write(folder / 'commands.json', logs)
        write(folder / 'result.json', result)
        return result

    def one(self, seed, pick):
        work = self.out / 'cases' / f'p{seed}'
        work.mkdir(parents=True)
        logs = []
        spec = read(self.inputs / f'p{seed}/spec.json')
        source = self.inputs / f'p{seed}/cond-revised'

        def run(stage, script, *args):
            result = subprocess.run([sys.executable, '-B', str(script), *map(str, args)],
                                    capture_output=True, text=True, timeout=45)
            logs.append({'stage': stage, 'args': list(map(str, [script, *args])),
                         'returncode': result.returncode,
                         'output': result.stdout + result.stderr})
            if result.returncode:
                raise RuntimeError(stage + ': ' + (result.stdout + result.stderr)[-1500:])

        def export(reel_path, folder, repeat=False):
            story, xml = folder / 'story.json', folder / 'timeline.fcpxml'
            run('adapt', self.co / 'adapt.py', reel_path, '-o', story, '--assets-root-local', self.media)
            run('compile', self.co / 'compile.py', 'build', story, xml)
            run('validate', self.co / 'compile.py', 'validate', xml)
            first = xml.read_bytes()
            deterministic = None
            if repeat:
                (folder / 'first-compilation.fcpxml').write_bytes(first)
                run('repeat-compile', self.co / 'compile.py', 'build', story, xml)
                deterministic = first == xml.read_bytes()
            return self.reader.parse(str(xml)), deterministic

        def rebuild(old_path, clock_path, folder):
            folder.mkdir()
            path = folder / 'reel.json'
            run('preserve-build', self.sb / 'build.py', 'build', source / 'notebook.json',
                clock_path, source / 'bindings.json', '-o', path, '--assets-root', self.media,
                '--stubs-dir', folder / 'stubs', '--preserve', old_path)
            return path

        def failed(scale, factor, error):
            return dict(seed=seed, scale=scale, factor=factor, eligible=pick is not None,
                        status='failed', error=str(error), **{key: False for key in CHECKS})

        if pick is None:
            return [dict(seed=seed, scale=name, factor=factor, eligible=False, status='ineligible')
                    for name, factor in SCALES]
        bi, oi, wi = pick
        beat = spec['beats'][bi]
        ident = f"{beat['id']}.L{oi + 2}"
        word = beat['words'][wi - beat['w0']]
        repaired_spec = copy.deepcopy(spec)
        repaired_spec['beats'][bi]['overlays'][oi]['anchor'] = wi
        initial, common = work / 'initial', {}
        initial.mkdir()
        try:
            baseline = self.reader.parse(str(source / 'timeline.fcpxml'))
            if not compare_edls(self.reference.truth_edl(spec), baseline)['exact']:
                raise ValueError('original E10 baseline differs from declared reference')
            reel = read(source / 'reel.json')
            reel['assets_root'] = reel['assets_root_local'] = str(self.media)
            original_path = initial / 'original-reel.json'
            write(original_path, reel)
            corrected = initial / 'reel.json'
            revision = initial / 'revision.txt'
            revision.write_text(f"{beat['id']}: L{oi + 2} anchor = {word}\n")
            run('repair', self.sb / 'revise.py', 'apply', original_path, revision,
                '-o', corrected, '--clock', source / 'clock.json')
            corrected_reel = read(corrected)
            first, _ = export(corrected, initial)
            expected = self.reference.truth_edl(repaired_spec)
            comparison = compare_edls(expected, first)
            common['initial_repair_exact'] = comparison['exact']
            write(initial / 'expected.json', expected)
            write(initial / 'placement-differences.json', comparison)
            target = layers(corrected_reel)[ident]
            reference_target = next(e for e in expected['events']
                                    if e.get('beat') == beat['id'] and e.get('z') == oi + 1)
            common['initial_target_correct'] = (
                target['anchor_word'] == wi and target.get('chosen_by') == 'creator'
                and [round(target[k] * 30) for k in ('t0', 't1')]
                == [reference_target['f0'], reference_target['f1']])
            try:
                noop = rebuild(corrected, source / 'clock.json', work / 'noop')
                noop_edl, _ = export(noop, noop.parent)
                comparison = compare_edls(expected, noop_edl)
                common['noop_exact'] = comparison['exact']
                write(noop.parent / 'placement-differences.json', comparison)
                changes = choice_changes(corrected_reel, read(noop))
                common['noop_choices_preserved'] = not changes
                write(noop.parent / 'choice-differences.json', changes)
            except Exception as error:
                common.update(noop_exact=False, noop_choices_preserved=False, noop_error=str(error))
        except Exception as error:
            write(work / 'commands.json', logs)
            return [failed(name, factor, error) for name, factor in SCALES]

        rows = []
        for name, factor in SCALES:
            folder = work / name
            folder.mkdir()
            row = dict(seed=seed, scale=name, factor=factor, eligible=True,
                       target=ident, new_anchor=word, target_kind=target['kind'],
                       creator_layers=sum(x.get('chosen_by') == 'creator' for x in layers(corrected_reel).values()),
                       **common)
            try:
                times = {'words': [{**w, 'start': round(w['start'] * factor, 3),
                                    'end': round(w['end'] * factor, 3)} for w in spec['word_times']]}
                write(folder / 'measured.json', times)
                changed_spec = copy.deepcopy(repaired_spec)
                changed_spec['word_times'] = times['words']
                expected = self.reference.truth_edl(changed_spec)
                write(folder / 'expected.json', expected)
                clock = folder / 'clock.json'
                run('swap-clock', self.sb / 'clock.py', 'swap', source / 'clock.json',
                    folder / 'measured.json', '-o', clock)
                retimed = folder / 'reel.json'
                run('retime', self.sb / 'build.py', 'retime', corrected, clock, '-o', retimed)
                exported, deterministic = export(retimed, folder, repeat=True)
                comparison = compare_edls(expected, exported)
                row.update(retimed_exact=comparison['exact'], compile_deterministic=deterministic)
                write(folder / 'placement-differences.json', comparison)
                changes = choice_changes(corrected_reel, read(retimed))
                row['retimed_choices_preserved'] = not changes
                write(folder / 'choice-differences.json', changes)
                rebuilt = rebuild(retimed, clock, folder / 'rebuilt')
                rebuilt_edl, _ = export(rebuilt, rebuilt.parent)
                comparison = compare_edls(expected, rebuilt_edl)
                row['rebuilt_exact'] = comparison['exact']
                write(rebuilt.parent / 'placement-differences.json', comparison)
                changes = choice_changes(corrected_reel, read(rebuilt))
                row['rebuilt_choices_preserved'] = not changes
                write(rebuilt.parent / 'choice-differences.json', changes)
                metadata = choice_changes(corrected_reel, read(rebuilt), ('style_by',))
                row['additional_style_by_changed'] = bool(metadata)
                write(rebuilt.parent / 'additional-ownership-metadata.json', metadata)
                row['status'] = 'complete'
            except Exception as error:
                row.update(status='failed', error=str(error))
                for key in CHECKS:
                    row.setdefault(key, False)
            rows.append(row)
        write(work / 'commands.json', logs)
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--projects', type=Path, required=True)
    parser.add_argument('--pool', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--candidate-skills', type=Path,
                        help='Separate candidate skills tree; exact differences from E10 are recorded')
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs, hashes, selected = capture(args.projects.resolve(), args.pool.resolve(), out,
                                      args.candidate_skills.resolve() if args.candidate_skills else None)
    prefix = 'current/skills/batch-2/skills/'
    e10 = read(inputs / 'manifest.json')['snapshot_sha256']
    before = {name[len(prefix):]: value for name, value in e10.items() if name.startswith(prefix)}
    current = inputs / 'snapshot' / prefix
    after = {str(p.relative_to(current)): sha(p) for p in current.rglob('*') if p.is_file()}
    source_changes = {
        'changed': {name: dict(e10=before[name], candidate=after[name])
                    for name in sorted(before.keys() & after.keys()) if before[name] != after[name]},
        'added': {name: after[name] for name in sorted(after.keys() - before.keys())},
        'missing': sorted(before.keys() - after.keys())}
    write(out / 'source-differences.json', source_changes)
    for source in [Path(__file__), ROOT / 'bench/test_preservation_study.py',
                   ROOT / 'experiments/E11-preservation-contract/PROTOCOL.md']:
        destination = out / 'harness' / source.name
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, destination)
        hashes[str(destination.relative_to(out))] = sha(destination)
    manifest = dict(status='running', scope='Reused E10 synthetic fixtures; no model or native-editor calls',
                    started_utc=datetime.now(timezone.utc).isoformat(), seeds=SEEDS,
                    scales=SCALES, selected=selected, inputs_and_source_sha256=hashes,
                    candidate_skills=str(args.candidate_skills) if args.candidate_skills else None,
                    source_differences_sha256=sha(out / 'source-differences.json'),
                    python=sys.version, platform=platform.platform(), argv=sys.argv)
    write(out / 'manifest.json', manifest)
    study, rows = Study(inputs, out), []
    clipped = study.clipped_fixture()
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        for batch in executor.map(lambda seed: study.one(seed, selected[str(seed)]), SEEDS):
            rows.extend(batch)
            if len(rows) % 20 == 0:
                print(f"Completed {len(rows)//2}/100 projects", flush=True)
    for name, expected in hashes.items():
        if sha(out / name) != expected:
            raise ValueError('captured input/source changed during run: ' + name)
    rows.sort(key=lambda row: (row['seed'], row['scale']))
    with (out / 'results.jsonl').open('w') as file:
        for row in rows:
            file.write(json.dumps(row, sort_keys=True) + '\n')
    summary = summarize(rows)
    summary['clipped_recovery_fixture'] = clipped
    write(out / 'summary.json', summary)
    manifest.update(status='complete', inputs_and_source_unchanged=True,
                    completed_utc=datetime.now(timezone.utc).isoformat(),
                    results_sha256=sha(out / 'results.jsonl'), summary_sha256=sha(out / 'summary.json'))
    write(out / 'manifest.json', manifest)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
