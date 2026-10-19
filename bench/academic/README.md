# Academic evaluation for REAL

This suite adds external data alongside the synthetic assembly benchmark. It
keeps three claims separate: finding footage, choosing an edit, and faithfully
compiling an approved timeline. These are not interchangeable scores.

## Current scope

| Evaluation | Inputs | Prediction | Scoring |
|---|---|---|---|
| QVHighlights component pilot | Video samples and a text query | Ranked source-time intervals | Pinned, unmodified official moment-retrieval functions |
| MEDit-Bench adapter | A source video and editing message | Ordered source-time cuts | Our implementation of the paper's temporal metrics |
| Existing REAL assembly suite | Approved notebook, assets and timing | FCPXML and render | Frame fidelity, structural checks and revision locality |

The QVHighlights runner exercises REAL's existing `bind.py` scoring and
acceptance thresholds, with a model-generated catalogue. It does **not** run
brainstorm, narration alignment, timeline construction, or Final Cut import.
Its two-second candidate windows and grouping are an explicit benchmark
adapter. Do not describe this as full-pipeline REAL performance.

MEDit preparation and scoring are implemented. A MEDit model runner and verified
source/timecode manifest are still required for a real editorial evaluation.
No MEDit model score is implied by importing its annotations or passing tests.

## Reproduce

Run from the repository root. Python 3.10+, FFmpeg/FFprobe, Pillow, NumPy and
scikit-learn are needed for QVHighlights; MEDit preparation additionally needs
PyArrow. Claude CLI must be installed and authenticated for model inference.
The evaluator itself needs no model account.

```sh
python3 -m pip install -r bench/academic/requirements.txt
python3 -m bench.academic.data fetch --root bench/work/academic
python3 -m bench.academic.data prepare-qvh --root bench/work/academic --limit 5
python3 -m bench.academic.data media-qvh --root bench/work/academic
REAL_ACADEMIC_DATA=bench/work/academic python3 -m unittest bench.academic.test_academic -v
python3 -m bench.academic.pilot --root bench/work/academic \
  --out bench/work/academic/qvh/runs/pilot --model claude-sonnet-5-5 \
  --max-cost-per-call 1.0
python3 -m bench.academic.qvh --root bench/work/academic \
  --predictions bench/work/academic/qvh/runs/pilot/real-binder.jsonl \
  --references bench/work/academic/qvh/references/answers.jsonl \
  --out bench/work/academic/qvh/runs/pilot/real-binder-score.json
```

Score `direct-vision.jsonl`, `random-window.jsonl`, and `full-video.jsonl` the
same way, or generate all scores and a summary together:

```sh
python3 -m bench.academic.report --root bench/work/academic \
  --run bench/work/academic/qvh/runs/pilot
```

`prepare-qvh --limit 0` selects the complete validation split; use a
**separate root** so a pilot's inputs cannot be replaced accidentally. The
five-case development pilot is not a leaderboard submission, held-out test, or
statistically reliable estimate. Full evaluation requires a frozen protocol,
complete split, multiple runs where stochastic, and uncertainty estimates.

`fetch` checks SHA-256 for every pinned source. The official evaluator is
downloaded into the ignored work directory rather than modified or copied into
REAL's code. Its sample predictions over all 1,550 validation cases must reproduce
the authors' five full-split MR metrics exactly. Tests also check perfect,
disjoint, empty, duplicate, malformed and missing-prediction cases.

## Protocol and comparison

1. Select cases by `sha256("real-academic-pilot-v1:" + qid)` before inference.
   No replacement of missing media or hard examples. Record every selected ID.
2. Create separate `inputs/cases.jsonl` and `references/answers.jsonl`. Inference
   accepts only query ID, video ID, query, and duration. It never reads answers.
3. Divide each video into uniform two-second windows, using one centre frame
   per window. This is a visual-only, coarse proposal strategy; fast motion,
   sound and events between samples can be missed. Save the exact frames,
   contact sheets, times, media hashes and measured duration.
4. REAL condition: one query-blind vision call produces `role`, `shows`, and
   `binds_to` for every window. The unchanged REAL binder scores the query
   against those descriptions with **no creator/oracle tags**. Merge adjacent
   accepted windows and rank each run by its mean binder score; retain ten.
5. Direct condition: the same model sees the same contact sheets plus the query
   and proposes intervals directly on the same grid. Both conditions get one
   model call and the same dollar cap per case. Record actual tokens/cost;
   this controls the allowance, not realized token consumption.
6. Add deterministic random-window and full-video baselines. Preserve empty
   predictions and infrastructure/model errors. Never score only successful
   cases or silently repair malformed model output. A single intact JSON object
   may have surrounding prose or a code fence; multiple or broken objects fail.
   Save the extraction mode. `bench.academic.replay` can re-decode saved responses
   into a new directory after a parser fix without another model call, while
   preserving and hashing the original attempts.

Model calls disable tools, MCP, skills, memory, hooks and repository context and
run in an empty temporary working directory. Inputs contain only the task and
inline contact-sheet images. Saved prompts and responses support audit. Public
data may still have been seen during model pretraining; this is not a claim of
training-data decontamination.

Scores are native QVHighlights MR mAP and R@1, in percent. QVHighlights's own
sample predictions sometimes exceed annotated duration; the scorer preserves
these for protocol parity and reports their count. The pilot producer rejects
out-of-bounds output. A scorer-only zero-length sentinel gives empty predictions
zero credit without allowing upstream AP to omit them from the denominator.
Highlight-detection scores are not reported.

## MEDit-Bench

```sh
python3 -m bench.academic.data prepare-medit --root bench/work/academic
python3 -m bench.academic.medit \
  --predictions /path/to/predictions.jsonl \
  --references bench/work/academic/medit/references/answers.jsonl \
  --timebases /path/to/verified-timebases.json --out /path/to/score.json
```

The release contains 60 source IDs, 180 unique messages, and 540 editor
annotations. The Hugging Face storage split is named `train`; these are reserved
as evaluation references here. Do not train or tune on the reference cuts.

Prediction rows: `{"qid":"...","vid":"...","cuts":[[1.5,4.2],[8,12]]}`.
Cuts are seconds on the source clock, in output order. A failed case must still
appear with `cuts: []` and an `error` field. All three reference edits are
averaged equally; do not choose whichever editor favors the prediction.

The release uses `HH:MM:SS:FF`. Supply a verified manifest, for example:

```json
{
  "VIDEO_ID": {
    "fps": "30000/1001",
    "duration": 824.0,
    "provenance": "Record how the annotation/export timebase was verified"
  }
}
```

Values above are illustrative, not dataset metadata. `editor_fps` may override
the rate by annotator index (`"0"`, `"1"`, `"2"`) when documented export rates
differ. A source video's average frame rate alone is not proof of an editor's
timecode rate. Missing rates and invalid frame fields stop scoring. Non-drop
fractional rates use nominal frame labels divided by the rational playback rate;
drop-frame semicolon timecodes are refused until explicitly supported.
Preparation writes `timebases.template.json` with unset rates and durations,
plus observed frame-field maxima for each editor. Those maxima are diagnostics,
not inferred frame rates. The checked release has frame fields above 29 in 18
of its 60 videos; silently treating all annotations as 30 fps would be wrong.

Section 3.5 is implemented directly: union-of-cuts IoU, its hit rate at
0.3/0.5/0.7, and greedy one-to-one cut F1 at those thresholds. These are fractions
in [0,1]. Temporal overlap does not assess narrative ordering or artistic merit;
human review remains necessary for those claims. No author scorer was linked
from the checked project release, so this is labelled a **reimplementation**.

## Sources, availability and rights

- [QVHighlights / Moment-DETR, NeurIPS 2021](https://github.com/jayleicn/moment_detr).
  Official code, annotations, sample outputs and licenses are pinned in
  `sources.lock.json`. Code: MIT; annotations: CC BY-NC-SA 4.0.
- The authors distribute raw videos as a large
  [archive](https://nlp.cs.unc.edu/data/jielei/qvh/qvhilights_videos.tar.gz).
  The small pilot uses individually downloadable community mirrors
  [gradguy](https://huggingface.co/datasets/gradguy/qvhilights) and
  [ayushsdev](https://huggingface.co/datasets/ayushsdev/qvhighlights-videos), at
  pinned revisions. Each downloaded file has recorded URL and SHA-256 and a
  duration check. Equality to the original archive's bytes is **not verified**.
- [MEDit-Bench paper, Section 3.5](https://arxiv.org/html/2607.25300v1#S3.SS5)
  and [released annotations](https://huggingface.co/datasets/kattyan/MEDit-Bench).
  Annotations: CC BY-NC-SA 4.0; source footage is not included in this release.
- [AVE](https://github.com/dawitmureja/AVE) remains a later shot-ordering track.
- [Timeline-Bench media access](https://timelinebench.tensortest.com/docs/inputs)
  currently requires a maintainer-run evaluation; source packs are not distributed.

Keep videos and derived frames in ignored local work directories. A code or
annotation license does not confer redistribution rights to underlying footage.
Publish aggregate results, provenance and reproduction commands subject to the
dataset terms; do not commit media or contact sheets.

## Temporal grounding and fresh validation

`python3 -m bench.academic.temporal` evaluates the production `ground.py` stage
on saved blind catalogues, adding one text-only call per case. Its total cost
includes catalogue creation; the report labels grounding-stage cost separately.
Use `--replay-source` to validate saved responses into a new run without model
calls. Coordinates and confidence values remain unchanged; alternatives may
overlap and are stably ranked by their original confidence.

`prepare-qvh --exclude-inputs OTHER_PUBLIC_CASES.jsonl` excludes all original
source videos represented in that file before deterministic identity selection.
This supports a fresh source-disjoint check after development. Once scored, the
subset is consumed validation data. Results and all failed attempts are recorded
in [E09](../../experiments/E09-temporal-grounding/README.md): original cases improve
from 0/5 to 4/5; fresh cases improve from 0/5 to 3/5, tying direct vision at R@1 .5
while trailing its fresh mAP. The full benchmark remains unrun.

## Two-call direct comparator (implemented; not yet evaluated)

`bench.academic.refine` adds an independent review of the first direct-vision
answer using exactly the same contact-sheet bytes. It checks complete event
extent and ranking, with the same per-call allowance and an exact model revision.
This supplies a two-call comparator for REAL's catalogue-plus-grounding path;
it does not establish equal realized cost or a performance result.

```sh
python3 -m unittest bench.academic.test_refine -v
python3 -m bench.academic.refine \
  --cases PATH_TO_FROZEN_INPUTS/cases.jsonl \
  --cached-direct PATH_TO_COMPLETED_PILOT \
  --out NEW_REFINEMENT_DIRECTORY \
  --model EXACT_REVISION_FROM_FIRST_CALL_RECORDS --max-cost-per-call 1.0
```

The second command performs paid inference. Freeze prompts, source hashes,
model revision and total spending allowance before running it. Existing call
records must report that same revision. Both stages' costs and usage appear
in `costs.json`; missing costs are marked incomplete. First-call failures stay
failed, malformed refinements do not fall back to first-pass answers, and no
automatic retries are performed. All input IDs must remain in the output.
The ordinary one-stage report is not a full-cost report for this condition;
use `costs.json` and the prediction file with `bench.academic.qvh`.

The [E10 protocol](../../experiments/E10-submission-validation/PROTOCOL.md)
freezes the next 100 public query IDs, excluding all original source videos
represented in the ten development queries. None has a new model score yet.
`bench.academic.compare` computes paired original-source-video bootstrap intervals
while preserving the benchmark's query-weighted mean. It uses unmodified official
per-query AP before rounding and verifies aggregate parity. Every selected query,
including failures, must appear exactly once in both prediction files:

```sh
REAL_ACADEMIC_DATA=bench/work/academic python3 -m unittest bench.academic.test_compare -v
python3 -m bench.academic.compare --root bench/work/academic \
  --left REAL_TEMPORAL.jsonl --right DIRECT_REFINED.jsonl \
  --references FROZEN_REFERENCES.jsonl --out paired-comparison.json
```

Report actual costs separately, with both REAL stages and both direct stages.
A nonsignificant difference does not establish equivalence. The retrospective
fresh-five comparison in E10 is exploratory; prespecify the primary endpoint
and any equivalence margin before the next inference run.

## Frozen four-condition run

`bench.academic.suite prepare` verifies the frozen input hash, media hashes and
duration checks, and saves a code snapshot. It never calls a model. `execute`
runs the lexical binder, direct vision, REAL temporal grounding and direct
refinement with one shared budget. The two primary conditions use two calls
each; binder and one-pass direct results are retained as secondary comparisons.
The snapshot includes the catalogue schema and records Python, package, FFmpeg,
and FFprobe versions. Changing that environment requires a new preparation
before inference; existing paid results must not be silently moved to a new plan.

```sh
python3 -m bench.academic.suite prepare --root bench/work/academic \
  --selection experiments/E10-submission-validation/results/academic/next100-manifest.json \
  --out bench/work/academic/qvh/runs/NEW_RUN
# Paid inference: supply the approved total allowance and exact model identifier.
python3 -m bench.academic.suite execute --out bench/work/academic/qvh/runs/NEW_RUN \
  --model MODEL_REVISION --total-cap APPROVED_USD --per-call-cap CALL_CAP_USD
python3 -m bench.academic.suite score --out bench/work/academic/qvh/runs/NEW_RUN
```

The local budget admits a call only when its full per-call allowance remains.
It halts on unknown costs, reported model drift, or a per-call overrun, and
blocks concurrent calls. An interrupted request without a final record cannot
be automatically retried. This is an admission/stop rule, not a provider billing
guarantee: a single in-flight response may overrun its limit. All attempted-call
costs persist, and cached results do not spend again. A stopped run cannot be
scored as the planned comparison. Changed execution settings require review;
do not start a new paid run merely to bypass a budget stop.
Execution and scoring also hold a whole-run lock to protect shared output files.
A stale lock requires inspecting its recorded process, not automatic removal.
Cached reuse cannot clear a prior cost overrun, and scoring rechecks the call
records rather than trusting a previously saved completion flag.

Media or inference failures remain explicit empty predictions for their original
IDs, including missing catalogues in the temporal condition. Frozen inputs and
media are checked again after inference. The scoring command alone opens the
references; it produces official metrics, paired source-video intervals, and
complete per-condition stage costs. Reusing a baseline in two comparisons does
not imply it was billed twice: `budget-status.json` records actual total spending.

On 18 October, all 100 selected clips were downloaded and verified locally,
covering 82 original source videos. The fallback mirror stores uppercase-leading
IDs in lowercase initial-letter folders; the downloader preserves filename case
and now uses the correct folder. No query was replaced. The prepared local run
is `bench/work/academic/qvh/runs/confirmatory-20261018-v2`; it has no model calls yet.
The earlier preparation is retained for provenance and superseded before
inference by this cost-check and reproducibility update. Selected queries,
media, prompts, and scoring rules are unchanged.
