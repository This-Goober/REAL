# E10: submission validation, frozen 2026-10-18

## Assembly validation

Development: existing seeds 1–30. A fresh rerun at imported head `c9df6a2`
found two projects with one-frame placement differences. Preserve that run as
`assembly-initial`. Preserve the rerun after the timing-precision fix as
`assembly-development`. Neither is held-out evidence.

Before running new seeds, freeze the current skills and harness by content
hash. Evaluate **seeds 1001–1100 inclusive**, 4–8 beats, normal difficulty,
explicit asset tags, unchanged `project.py` and existing synthetic pool.
No seed removal, replacement, early stopping, or tuning against these results.
Any later fix must be named separately and these seeds marked consumed.

Conditions are the original baseline at
`16c34d59f7db1ca0618e35fbcdaaf30a4494c952` with measured-clock swap; the current
pipeline with measured-first timing; and the current pipeline with its estimated
clock. This is an implementation/clock ablation, not a competing editing system.

Primary outcome: mean project-level exact-placement F1, identity and temporal
IoU=1, over every selected seed. Compilation or parse failures receive zero.
Secondary: F1 at IoU .5, topmost-visual source-frame agreement, pipeline success,
and fraction of projects with every placement exact. Boundary error among
IoU-.5 matches is explicitly conditional on successful matching. Bootstrap
10,000 paired seed draws, seed 20261018, percentile 95% intervals. Degenerate
intervals at perfect scores are descriptive of this sample, not guarantees.

This run is structural only. No pixel score, aesthetic score, or Final Cut
application-import pass is inferred. Geometry/source-audio conformance has
separate fixed unit fixtures. Save reference/scorer/skills hashes, package and
FFmpeg versions, raw per-seed rows, and the initial manifest before execution.

## Public-dataset extension

Keep the ten already examined QVHighlights queries as development data. Exclude
every source video they represent. Select the next 100 queries by ascending
SHA256(`real-academic-confirmatory-v1:qid`) without reading answers into the
inference process. Publish the selected IDs before running a model. Keep all
missing-media and failed cases; report both failure rate and all-case metrics.
This is a source-disjoint validation subset, not the official held-out test.

Primary comparison: REAL temporal against direct vision using the same model
revision, sampled images, query set, and fixed allowance. REAL uses one blind
catalogue call plus one text grounding call. Include the existing one-call
direct method and a two-call direct-refinement comparator before describing
results as matched-budget. Fix prompts and retry policy before execution;
include all inference and retry costs, catalogue cost, tokens, and latency.
At protocol freeze, the two-call comparator was not implemented or evaluated.
An implementation was subsequently added in `bench.academic.refine`, with five
offline tests; no predictions on the next 100 queries have been generated.
Before inference, freeze the runner and prompts by hash and record the exact
model revision, cap, and package versions. This does not change the selected IDs.

Use the unmodified pinned official evaluator; first reproduce all five sample
metrics over 1,550 validation queries. Primary endpoint is MR full mAP;
R@1 at .5/.7 are secondary. Bootstrap paired *source videos*, keeping all
queries from the same original video together. Superiority requires the
paired primary-metric CI to exclude zero. Equivalence/noninferiority requires
a substantively justified, prespecified margin; a nonsignificant difference
or equal R@1 counts does not establish equivalence.

The released Moment-DETR sample predictions can be scored on exactly the same
IDs as an additional supervised reference. They use a different training and
feature regime, so report them separately from matched-input model comparisons.
Do not compare five-case numbers directly with full-split leaderboard scores.

No public model inference is part of the structural command. Larger paid
inference, missing media, and native-editor validation are tracked separately.
