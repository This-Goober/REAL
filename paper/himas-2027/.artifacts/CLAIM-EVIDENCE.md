# Claim/evidence map — short-paper candidate, 18 October 2026

Paths below are repository-relative unless stated otherwise. This map supports
review of the current paper; it is not an independent replication or a human
study. No new model inference was used to shorten the manuscript. Hash-bound
PDF/source/citation checks are in `review-artifacts.json`.

| Paper claim | Retained evidence | Interpretation limit |
|---|---|---|
| Final frozen pipeline matches all 1,269 placements in 100 projects; original implementation exact on zero | `experiments/E11-preservation-contract/results/unified-snapshot/assembly-validation/{manifest.json,results.jsonl,summary.json}` and `parity.json` | Tagged, synthetic, 30 fps grammar; reused after E11-informed fixes, not untouched held-out or real-project generalization. Original E10 evidence retained |
| Estimated-clock prose: 14/1,269 exact; project-mean matched-event start/end error 0.31/0.66 s, maximum 2.37 s | Same all-case rows; `paper/himas-2027/.artifacts/results-diagnostics.json` | Uses 641 IoU≥.5 matches and excludes 628 unmatched placements; mean of project means, not a pooled or all-placement error |
| Revised development result was 28/30 before precision fix | `experiments/E10-submission-validation/results/assembly-initial/summary.json` | Development observation; implementation and timing order change together |
| 30/30 repaired targets, zero other identity/boundary changes | `experiments/E11-preservation-contract/results/unified-snapshot/repair-development.jsonl`; original E10 rows retained | Same fixed eligible-anchor rule on reused development data; no appearance, audio or human-effort guarantee |
| Under ×0.8/×1.2 word times, 100/100 corrections survive retiming and rebuild per condition; repeat compilation identical | E11 `results/{corrected-isolated,control-isolated}` and unified `parity.json`/`source-manifest.json` | Same 100 projects, two artificial scales, same 67-file pipeline as assembly/REAL comparator. Original failures retained: two one-frame errors and style-ownership loss across 88 projects. Not new speakers, other edits or native playback |
| Figure 3: img07 moves 607–631 to 562–586 and retains duration | `paper/himas-2027/.artifacts/figure-data/placement.json`; `demo/build.py` | Synthetic walkthrough; illustrative correction, no participant |
| All 180 direct-model attempts retained; two models match REAL with notes; Table 1 | `experiments/E11-preservation-contract/results/unified-snapshot/oneshot/{manifest.json,results.jsonl,summary.json}`; original E03 `replay-inputs.zip` (distributed outside the repository; SHA-256 `9f93ff17c23ac28a20a409ca9bfbc6d1dbeaa69b1666170897dbdf5dffa04422`) | REAL regenerated with unified source; unchanged E03 scorer modules, validator, prompts and responses. Summary byte-identical. Retrospective CLI labels and shared plan; no equivalence or native appearance claim |
| E03 independent portable replay exactly matches summary | `experiments/E03-oneshot-baselines/results/offline-20261018/{README.md,verification.json}` | Re-scores retained outputs; does not reproduce model generation |
| Blank pauses leave 209/900 frames without picture, timeline ends at 875 | `experiments/E05-tier2-codex-reproduction/results/transformer-math-30s-mode-A.json` | Full 900-frame horizon; reference-trimmed clips and labelled assets |
| Holding shots gives seven exact shots; caption mean errors remain 8/6 frames | Corresponding E05 `transformer-math-30s-mode-B.json` | Supplied pause convention; no raw-footage discovery; paper does not claim pixel-quality improvement |
| PocketSphinx/provider onset disagreement 51.3 ms median, 90.9 ms p95 | `experiments/E06-forced-alignment/results/transformer-math-30s-pocketsphinx.json` | Provider timestamps are a comparison signal, not acoustic ground truth |
| Five fresh QVHighlights queries: both 3/5 at IoU .5; mAP 25.75/32.83 and interval | `experiments/E10-submission-validation/results/academic/fresh-paired-comparison.json`; retained predictions in artifact | Tiny source-disjoint-at-selection probe; two calls versus one; no superiority, equivalence or full-benchmark result |
| Official evaluator parity across 1,550 sample predictions | `experiments/E10-submission-validation/results/academic/official-parity.json` | Evaluator compatibility, not REAL retrieval performance |
| Figure 2: sampled visual evidence and tag-led binding | `paper/himas-2027/.artifacts/figure-data/{paganini.json,provenance.json}` and five included JPEGs | Five of sixteen sampled proxy frames; source window and tag supplied by project script |
| Recorded-case paragraph: eight proposed overlay moves, five base clips retained | Figure-data `paganini.json`; project `RUN-LOG.md`; frozen before/after data | Model-proposed editorial choices, not participant repairs; drawn from prior 67.4 s state |
| Paganini alignment fallback: two failures, median 60–90 ms on other three, max 3.5 s | `paper/himas-2027/.artifacts/figure-data/paganini-case-evidence.json` contains all 95 paired onsets and source hashes | Numeric disagreement recomputed from saved raw take-relative onsets. Two failures are reported by historical run log; original exception logs not packaged. Neither ASR source has manual annotations |
| v4 adds a 419-frame intro and preserves 18 tutorial source/anchor records | Same case-evidence JSON, 18 before/after frame pairs; the integration receipt in the local project folder (its hashes are copied into the case-evidence JSON) | Caption wording/style intentionally changed. Boundary/source/anchor check does not establish visual appearance or audio mix |
| Visible Glow after importing v4 | Hash-bound creator quote in that receipt and case-evidence JSON | the authors' specific visible-Glow observation only; no systematic checkbox, all-caption or re-export coverage |
| Full named v4 opening, all stills/captions and clean audio reported working in Final Cut | `demo/paganini-no23/native-playback-confirmation.json`; integration receipt and case-evidence JSON | the authors' report in response to the explicit full-project question; source XML identified by hash, native project not compared; no inspector, frame-accuracy, round-trip or participant claim |
| Human comprehension, usability or agency benefits | No completed participant evidence | Proposed study only; no benefit claim |

## Reproduction versions

The v7 research ZIP preserves the named predecessor with the unchanged evaluated E10
implementation from verified v5. The included E03 supplement preserves the later
retrospective scorer, inputs and all retained outputs in its own frozen ZIP.
Current live title code has evolved and must not replace the frozen E10 source
for reproduction. The active anonymous paper, full playback confirmation and
unified E11 source postdate v7. E11's unified-snapshot records bind the later
source and reruns; v7 does not contain those results. The full later runs are in
`REAL-preservation-unified-20261018-v2.zip` (distributed outside the repository; SHA-256 `56af08815b179730ebf67fb6dfe4d33f118a1dd8e2aa73716ccacd1cd0fcf74b`), with an adjacent
verification JSON covering archive integrity and fresh-extraction checks.
Identified research artifacts, demo media and branch patches are internal and
must not be submitted as anonymous supplements. The final submission still
needs approved versions and suitable published links. Earlier packages (v5, v6, the withdrawn unified ZIP, the longer drafts) are archived outside the repository under `bench/work/paper-archive-20261018/`.

The standalone paper ZIP rebuilds the document and its three figures from their
PDFs, class and bibliography; it is not the experiment artifact. E05/E06 saved
metrics can be re-tabulated, but their source recordings and reference project
are absent from the research ZIP. Do not describe those original runs as fully
reproducible from the package alone.

## Strict metric and untested operations

The paper's exact-placement F1 requires identity plus both frame boundaries;
a one-frame miss leaves both a prediction and reference unmatched. The existing
`boundaries_within_1f` and mean boundary-error diagnostics in `bench/metrics.py`
are conditional on IoU-.5-matched events. They are not shares/errors over every
reference boundary. The estimated-clock diagnostic is presented with its
641-match denominator, excluded unmatched events and project-mean aggregation. Failed
projects still receive zero in the all-case F1 summaries.

The repair result covers re-anchoring. E11 adds two artificial word-time scales
on the same 100 projects and a clipped-duration fixture, reviewed at that scope
by the reviewer. New recordings, other edits and native round trips remain evidence gaps.

## Appendix A claims

| Appendix claim | Retained evidence | Interpretation limit |
|---|---|---|
| Repository size, 10,508 lines of Python; six handoff schemas | `skills/batch-2/skills/*/scripts/`, `skills/batch-2/skills/*/references/schemas/` | Count of the tree as published with this PDF |
| Estimated-clock constants and calibration (486 words, 3.11 w/s, worst section 5.8%) | `skills/batch-2/skills/real-storyboarding/scripts/rates.json` (`calibration` block) | One speaker, five sections; take lengths include leading and trailing silence; text-duration rates are conventions |
| Placement, pause, snap, clipping and preservation rules | `real-storyboarding/scripts/clock.py`, `build.py`, `revise.py`, `real_core.py` | Describes the implemented rules; their editorial quality is not evaluated |
| Frame arithmetic and the two rounding failures | `real_core.py` (`Frames`); `experiments/E11-preservation-contract/README.md` | Same evidence as the body's retiming paragraph |
| Binder weights and thresholds | `real-storyboarding/scripts/bind.py` | Binding accuracy without reference tags is not measured in this paper |
| Validator checks, DTD child order, position units | `real-compile/scripts/validate.py`, `fcpxml.py`, `adapt.py` | Validity checks, not native-import evidence |
| Failure-mode table, 16 rows | The rule column is implemented in the scripts above and pinned by `real-storyboarding/tests/` | Failure modes the checks catch, not a defect rate |
| 40 regression checks over 35 rules; 38 unit tests with 48 subtests | `real-storyboarding/tests/regression.py` and `tests/test_*.py` | Rerun on the published tree |
| OTIO mapping and raster-title calibration (1.78 em in portrait, 0.2 em shift, 1.73 measured) | `real-compile/scripts/targets/otio_target.py`, `title_raster.py`, `real-compile/references/targets.md` | Calibration measured on one export |
| 130/130 projects equivalent across the two targets | `bench/cross_target_check.py`, `bench/otio_edl.py` | Independent readers of the two files; no editor import of the 130 |
| Paganini renders in Final Cut and Resolve: 2,747 frames, 6/6 cuts, 22/22 caption edges, glyph boxes within 1%, median SSIM 0.992, audio lag 0 ms, translucent still darker in Resolve | `demo/paganini-no23/comparison/` (`COMPARISON.md`, `report.json`, `cuts.csv`, `captions.csv`) | One tutorial, two editors, one import each |
