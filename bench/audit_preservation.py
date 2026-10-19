"""Recompute E11 result flags from retained reels and XML, without compiling."""
import argparse
import copy
import json
from pathlib import Path

from bench.preservation_study import load_module, read, write, sha


def audit(root):
    root = root.resolve()
    manifest = read(root / 'manifest.json')
    assert manifest['status'] == 'complete'
    frozen = load_module('saved_e11_harness', root / 'harness/preservation_study.py')
    study = frozen.Study(root / 'inputs', root)
    rows = [json.loads(line) for line in (root / 'results.jsonl').read_text().splitlines()]
    assert sha(root / 'results.jsonl') == manifest['results_sha256']
    assert sha(root / 'summary.json') == manifest['summary_sha256']
    for name, expected in manifest['inputs_and_source_sha256'].items():
        assert sha(root / name) == expected, name
    checked, metadata_projects = 0, set()
    for row in rows:
        seed, scale = row['seed'], row['scale']
        pick = manifest['selected'][str(seed)]
        assert frozen.selection(read(root / f'inputs/p{seed}/spec.json'), seed) == tuple(pick)
        assert row['status'] == 'complete' and row['eligible'] is True
        spec = read(root / f'inputs/p{seed}/spec.json')
        bi, oi, wi = pick
        spec['beats'][bi]['overlays'][oi]['anchor'] = wi
        folder = root / f'cases/p{seed}'
        initial_reel = read(folder / 'initial/reel.json')
        initial_truth = study.reference.truth_edl(spec)
        target = frozen.layers(initial_reel)[row['target']]
        target_truth = next(e for e in initial_truth['events']
                            if e.get('beat') == spec['beats'][bi]['id'] and e.get('z') == oi+1)
        flags = dict(initial_target_correct=target['anchor_word'] == wi and
                     target['chosen_by'] == 'creator' and
                     [round(target[k]*30) for k in ('t0','t1')] == [target_truth['f0'],target_truth['f1']])
        expected = initial_truth
        for name, exact_flag, choices_flag in [
            ('initial', 'initial_repair_exact', None),
            ('noop', 'noop_exact', 'noop_choices_preserved'),
            (scale, 'retimed_exact', 'retimed_choices_preserved'),
            (scale+'/rebuilt', 'rebuilt_exact', 'rebuilt_choices_preserved')]:
            if name == scale:
                spec = copy.deepcopy(spec)
                factor = dict(frozen.SCALES)[scale]
                spec['word_times'] = [{**w, 'start': round(w['start']*factor,3),
                                       'end': round(w['end']*factor,3)} for w in spec['word_times']]
                expected = study.reference.truth_edl(spec)
            actual = study.reader.parse(str(folder / name / 'timeline.fcpxml'))
            flags[exact_flag] = frozen.compare_edls(expected, actual)['exact']
            if choices_flag:
                flags[choices_flag] = not frozen.choice_changes(initial_reel, read(folder / name / 'reel.json'))
        flags['compile_deterministic'] = ((folder / scale / 'first-compilation.fcpxml').read_bytes() ==
                                           (folder / scale / 'timeline.fcpxml').read_bytes())
        metadata = frozen.choice_changes(initial_reel, read(folder / scale / 'rebuilt/reel.json'), ('style_by',))
        if metadata:
            metadata_projects.add(seed)
        flags['additional_style_by_changed'] = bool(metadata)
        assert all(row[key] == value for key, value in flags.items()), (seed,scale,flags)
        checked += 1
    summary = read(root / 'summary.json')
    assert {key: summary[key] for key in ('planned_seeds','planned_rows','scales')} == frozen.summarize(rows)
    recorded = manifest['inputs_and_source_sha256']
    unrecorded = sorted(str(p.relative_to(root)) for p in (root / 'inputs').rglob('*')
                        if p.is_file() and str(p.relative_to(root)) not in recorded)
    return dict(passed=True, rows_recomputed=checked, recorded_inputs_and_source_unchanged=True,
                projects_with_changed_style_owner=len(metadata_projects),
                unrecorded_generated_input_files=unrecorded,
                results_sha256=manifest['results_sha256'], summary_sha256=manifest['summary_sha256'],
                run_manifest_sha256=sha(root / 'manifest.json'),
                audit_source_sha256=sha(Path(__file__)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.run)
    write(args.out, result)
    print(result)


if __name__ == '__main__':
    main()
