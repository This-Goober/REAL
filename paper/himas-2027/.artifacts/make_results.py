"""Generate results from retained E03/E05/E06 and the unified E11 snapshot."""
import hashlib
import json
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parents[2] / 'experiments'
E10 = EXPERIMENTS / 'E10-submission-validation/results'
E11 = EXPERIMENTS / 'E11-preservation-contract/results'
RESULTS = E11 / 'unified-snapshot'


def read(path):
    return json.loads(path.read_text())


def interval(value):
    lo, hi = value['ci95']
    return f"{value['mean']:.3f} [{lo:.3f}, {hi:.3f}]"


def main():
    study = read(RESULTS / 'assembly-validation/summary.json')
    initial = read(E10 / 'assembly-initial/summary.json')
    repair = [json.loads(line) for line in (RESULTS / 'repair-development.jsonl').read_text().splitlines()]
    direct = read(RESULTS / 'oneshot/summary.json')
    paired = read(E10 / 'academic/fresh-paired-comparison.json')
    retiming = read(E11 / 'corrected-isolated/summary.json')
    prior_retiming = read(E11 / 'control-isolated/summary.json')
    parity = read(RESULTS / 'parity.json')
    assert parity['e11_pipeline_tree_identical']
    assert all(v['all_checks_passed'] == 100 and v['additional_style_by_changed'] == 0
               for v in retiming['scales'].values())
    delta = paired['intervals']['left_minus_right']['MR-full-mAP']
    modes = {m: read(EXPERIMENTS / f'E05-tier2-codex-reproduction/results/transformer-math-30s-mode-{m}.json') for m in ('A', 'B')}
    align = read(EXPERIMENTS / 'E06-forced-alignment/results/transformer-math-30s-pocketsphinx.json')
    all_rows = [json.loads(line) for line in (RESULTS / 'assembly-validation/results.jsonl').read_text().splitlines()]
    estimated = [row['structural'] for row in all_rows if row['condition'] == 'estimated']
    assert len(estimated) == 100 and all(row and row['matched@0.5'] for row in estimated)
    reference_count = sum(row['n_truth'] for row in estimated)
    exact_count = sum(round(row['f1@1.0'] * (row['n_truth'] + row['n_pred']) / 2) for row in estimated)
    matched_count = sum(row['matched@0.5'] for row in estimated)
    in_error = mean(row['in_err_mean_f'] for row in estimated) / 30
    out_error = mean(row['out_err_mean_f'] for row in estimated) / 30
    diagnostic = {
        'scope': 'Retabulation of saved estimated-clock diagnostics; no scorer or predictions changed',
        'projects': len(estimated), 'reference_placements': reference_count,
        'exact_matches': exact_count, 'matched_at_iou_half': matched_count,
        'unmatched_excluded_from_boundary_error': reference_count - matched_count,
        'boundary_error_aggregation': 'Mean of each project\'s IoU>=.5-matched-event absolute errors; not a pooled event mean',
        'mean_project_start_error_s': in_error, 'mean_project_end_error_s': out_error,
        'worst_matched_error_frames': max(max(row['in_err_max_f'], row['out_err_max_f']) for row in estimated),
        'source_sha256': hashlib.sha256((RESULTS / 'assembly-validation/results.jsonl').read_bytes()).hexdigest()}
    (HERE/'results-diagnostics.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    lines = ['# Results', '', '## Assembly and local repair', '',
        f"The frozen measured-clock pipeline compiles and matches every one of {reference_count:,} "
        f"reference placements in {study['conditions']['revised']['all_placements_exact']}/100 validation projects. "
        'This establishes conformance to the declared generator. The benchmark exposed five timing defects '
        f"during development; the original implementation was exact on {study['conditions']['published']['all_placements_exact']}/100 projects.", '',
        f"With estimated word times, {exact_count} of {reference_count:,} placements are exact (about 1%); "
        f"project-averaged start/end errors are {in_error:.2f}/{out_error:.2f} seconds among the "
        f"{matched_count} placements matched at IoU≥.5 (maximum {diagnostic['worst_matched_error_frames']/30:.2f} seconds), with {reference_count-matched_count} unmatched "
        'placements excluded from those error averages.', '',
        f"The imported implementation was exact on {initial['conditions']['revised']['all_placements_exact']}/30 "
        'development seeds. Retaining derived precision resolved two one-frame discrepancies without changing '
        'the reference or scorer. In the 30 development re-anchor repairs, '
        f"{sum(bool(r.get('target_correct')) for r in repair)}/30 targets have correct revised bounds and "
        f"{sum(r.get('collateral',0) for r in repair)} non-target identities change boundaries. "
        'This supports the tested locality contract, not human repair efficiency.', '',
        'Under ×0.8 and ×1.2 word-time scales, the correction survives retiming and preserved '
        'rebuilding in 100/100 projects each, with saved choices unchanged and repeated compilation '
        'byte-identical. The check exposed two one-frame endpoint errors among 200 retimed exports '
        f"and lost style-ownership labels in {prior_retiming['scales']['faster']['additional_style_by_changed']} "
        'projects in the earlier code; both defects were fixed before rerunning the reported snapshot.', '',
        '## Direct generation from the same plan', '',
        'Table 1 compares REAL with direct Claude CLI generation on all 30 development projects per condition. Raw temporal F1 retains parsable invalid '
        'XML; gated F1 assigns zero unless both the DTD and semantic validator pass. One retained response '
        'contains no XML and receives zero in both columns.', '',
        '| Compiler | Format notes | All exact | Format pass | Temporal F1 | Gated F1 |',
        '|---|---|---:|---:|---:|---:|']
    for key,label,notes in [
        ('real-revised-measured','REAL','Scripted'),
        ('oneshot-claude-sonnet-5-5','Sonnet 5.5','Supplied'),
        ('oneshot-claude-opus-5-5','Opus 5.5','Supplied'),
        ('oneshot-claude-fable-5-1','Fable 5.1','Supplied'),
        ('oneshot-claude-sonnet-5-5-norules','Sonnet 5.5','Omitted'),
        ('oneshot-claude-opus-5-5-norules','Opus 5.5','Omitted'),
        ('oneshot-claude-fable-5-1-norules','Fable 5.1','Omitted')]:
        v=direct['conditions'][key]
        lines.append(f"| {label} | {notes} | {v['all_exact']}/30 | {v['both_valid']}/30 | "
                     f"{v['raw']['f1@1.0']['mean']:.3f} | {v['validity_gated']['f1@1.0']['mean']:.3f} |")
    lines += ['',
        'With format notes, Opus and Fable match REAL on all 30 projects. The REAL-minus-Sonnet '
        'difference is .009 [0.000, .020]. Direct generation can therefore reproduce the supplied '
        'plan; equal sample scores do not establish general equivalence. REAL makes validation and '
        'rebuilding of saved decisions scripted operations requiring no new model call. Without notes, paired '
        'differences are .052 [.016, .093], .036 [.007, .072] and .042 [0.000, .117]. Format failures '
        'include still-image element choices, frame-duration declarations and child ordering. '
        'These are exploratory development comparisons. All 180 prompt/reference and response-extraction '
        'audits pass; a portable frozen replay reproduces the summary byte-for-byte.', '',
        '## Where conformance stops', '',
        'The narrated reconstruction selects all seven intended shots and caption assets, but timing '
        f"conventions differ. Blank-pause mode leaves {modes['A']['black_frames_pred']} of 900 reference "
        f"frames without a base picture and ends at frame {modes['A']['total_f_pred']}. "
        'Holding shots through pauses recovers all seven shot boundaries, while mean caption start/end '
        f"errors remain {modes['B']['captions']['in_err_mean_f']:.0f}/{modes['B']['captions']['out_err_mean_f']:.0f} "
        'frames. Source clips were reference-trimmed: this does not demonstrate discovery of those '
        'conventions in raw footage. Against provider word onsets, PocketSphinx median absolute error '
        f"is {align['onset_err_ms_median']:.1f} ms (95th percentile {align['onset_err_ms_p95']:.1f} ms); "
        'neither timestamp source is independent acoustic ground truth.', '',
        'On the five fresh QVHighlights cases, REAL temporal and direct vision each retrieve 3/5 '
        'at IoU .5, but mAP is 25.75 versus 32.83. The exploratory source-bootstrap difference is '
        f"{delta['mean']:.2f} percentage points [{delta['ci95'][0]:.2f}, {delta['ci95'][1]:.2f}]. "
        'The small, unequal-call probe establishes neither superiority nor equivalence. Detailed '
        'predictions and official-evaluator parity are in the artifact.', '',
        'Frozen source hashes, all-case rows, independent references and reproduction commands accompany '
        'the results. No new model inference was used for this analysis. Native import and creator '
        'outcomes require their own evidence.']
    (HERE.parent/'05-results.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
