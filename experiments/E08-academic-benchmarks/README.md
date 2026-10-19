# E08 — External academic benchmarks

**Question.** Can REAL select the right source footage and its temporal extent
when asset descriptions must come from video evidence, without reference tags?

**Status, 2026-10-17.** QVHighlights development pilot complete: five validation
queries from four source videos. MEDit-Bench annotations and scorer prepared;
its model evaluation awaits verified media/timecode metadata and a runner.

## What actually ran

The [harness and full protocol](../../bench/academic/README.md) freeze upstream
revisions and SHA-256 hashes. Five QVHighlights IDs were selected by a seeded
identity hash before inference: 193, 9823, 3666, 6383, 7416. All five media clips
were obtained; no cases were replaced. Media came from pinned community mirrors,
with recorded hashes and duration checks. Byte identity with the authors' large
video archive has not been independently established.

Both model conditions used `claude-sonnet-5-5` (confirmed by the provider's usage
records), one call per case, the same contact sheets, and a $1 per-call allowance.
Each two-second source window was represented by one centre frame. Actual
reported usage was $0.470160 for REAL's catalogue calls and $0.210792 for direct
vision, $0.680952 total. This is an equal allowance, not equal realized tokens.

- **REAL binder:** query-blind visual descriptions, then the unchanged REAL
  lexical binder and acceptance thresholds; neighboring accepted windows merge
  into proposals ranked by mean score.
- **Direct vision:** the query and the same images go directly to the model,
  which returns ranked intervals on the same grid.
- **Random / full-video:** deterministic sanity baselines.

This is a component adaptation. It does not evaluate brainstorm, narration,
FCPXML, Final Cut import or full-film quality.

## Results

Native QVHighlights moment-retrieval metrics, in percent:

| Condition | R@1, IoU ≥ .5 | R@1, IoU ≥ .7 | mAP | Failed calls/output | Empty predictions |
|---|---:|---:|---:|---:|---:|
| REAL binder | 0.00 | 0.00 | 0.00 | 0 | 1 |
| Direct vision | 60.00 | 60.00 | 46.93 | 0 | 0 |
| Random window | 0.00 | 0.00 | 0.00 | 0 | 0 |
| Full video | 0.00 | 0.00 | 0.00 | 0 | 0 |

[Machine-readable scores and per-case results](results/scores.json) are the
authority. The sample is much too small for superiority, population accuracy,
or leaderboard claims. Two queries share one original YouTube source.

The current adapter often retrieves an isolated relevant frame instead of an
event's full duration. For query 193 it returns 106–108 seconds while the external
reference spans 106–124 seconds. This suggests a temporal grouping/selection
limitation worth testing on separate development examples. Other cases also
expose lexical mismatch and ambiguity in the descriptions. These observations
do not isolate the catalogue, sampling and binder contributions; that requires
controlled ablations. No binder weights or thresholds were tuned on these cases.

The direct baseline originally had two parsing failures because its intact JSON
objects were preceded by prose. A general output-decoding fix accepts one intact
object, rejects ambiguous/broken objects, and changes no predictions. We replayed
**the same ten raw responses**, with zero additional model calls. Original raw
attempts and pre-fix scores remain available; REAL predictions and all previously
parsed direct predictions were verified identical.

## Evaluator verification

- **17/17 checks pass**, including no-answer input projection, sampling identity
  independent of labels, true empty/missing failures, duplicate cut penalties,
  interval unions, fractional timecodes, transport, and JSON extraction.
- The unmodified official QVHighlights functions reproduce the authors' sample
  on **all 1,550 validation queries**: mAP 32.20, mAP@.5 54.96, mAP@.75 31.01,
  R@1/.5 53.94 and R@1/.7 34.84. **These are the authors' sample predictions,
  not REAL results.** [Verification](results/official-sample-check.json).
- Perfect-reference fixtures score 100; disjoint/empty fixtures score zero.
  Missing or duplicate query IDs cannot silently shrink the denominator.

## MEDit-Bench readiness

The released 60 source IDs, 180 messages, 540 professional annotations and 6,231
cuts are imported. Inference input files omit reference cuts. The scorer
implements paper Section 3.5: union IoU, R@.3/.5/.7, greedy one-to-one cut F1,
averaged over all three editors. It is our tested implementation, not the
authors' released evaluator.

The release supplies frame timecodes but no timebase column. **18 videos contain
frame fields above 29**, and some editors' ranges differ for the same source.
These observations do not determine the correct rates. The scorer requires
verified frame rates, durations and provenance, with per-editor overrides when
documented. No MEDit performance number is reported until those are resolved.

## Reproduce and inspect

Follow [the harness commands](../../bench/academic/README.md). Original run:
`bench/work/academic/qvh/runs/pilot-v2/`; current decoded results:
`bench/work/academic/qvh/runs/pilot-v2-replayed/`. Both are under the isolated
checkout `/tmp/real-codex-hardening`. Videos, sampled frames, prompts and raw
responses are local and ignored by Git. Small results and provenance are copied
to this experiment's `results/`; `experiments/sync.py` does not manage E08 yet.

```sh
python3 -m bench.academic.replay --root bench/work/academic \
  --source bench/work/academic/qvh/runs/pilot-v2 \
  --out bench/work/academic/qvh/runs/a-new-replay-directory
python3 -m bench.academic.report --root bench/work/academic \
  --run bench/work/academic/qvh/runs/a-new-replay-directory
```

Before a paper-level run: freeze a development-tested protocol, resolve the
MEDit source/timecode manifest, implement and test the MEDit editorial runner,
evaluate complete official splits, and report uncertainty and matched baselines.
Keep reconstruction fidelity separate from choices made without reference cuts.

Sources: [QVHighlights, NeurIPS 2021](https://github.com/jayleicn/moment_detr),
[MEDit-Bench paper](https://arxiv.org/abs/2607.25300),
[MEDit annotations](https://huggingface.co/datasets/kattyan/MEDit-Bench).
Annotations are CC BY-NC-SA 4.0; underlying footage rights remain separate.
