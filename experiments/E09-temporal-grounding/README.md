# E09 — Selecting complete source events

REAL's original QVHighlights component pilot scored 0/5 at R@1 IoU ≥ 0.5.
Its query-blind catalogue often described the right content, but the lexical
binder treated each sampled frame independently. This experiment adds a reusable
storyboarding stage that matches a request against ordered observations and
returns complete source events, evidence and limitations.

## Results

2026-10-17. Official, pinned QVHighlights MR evaluator; model `claude-sonnet-5-5`.
Metrics are percentages except the explicit success counts.

| Set | Condition | R@1 ≥ .5 | R@1 ≥ .7 | mAP |
|---|---|---:|---:|---:|
| Original five (development) | Lexical REAL binder | 0/5 | 0/5 | 0.00 |
| Original five (development) | Direct vision | 3/5 | 3/5 | 46.93 |
| Original five (development) | REAL temporal v2 | **4/5** | **4/5** | **56.88** |
| Fresh five | Lexical REAL binder | 0/5 | 0/5 | 0.00 |
| Fresh five | Direct vision | **3/5** | 1/5 | **32.83** |
| Fresh five | REAL temporal v2 | **3/5** | **2/5** | 25.75 |

The goal of 5/5 on the original cases is **not yet met**. This improves REAL's
component retrieval over its lexical baseline on both sets. It does not establish
superiority to direct vision: the fresh R@1 .5 result ties, and direct vision has
higher fresh mAP. Five cases per set cannot establish statistical reliability.

The unchanged lexical baseline and direct-vision original results are in
[E08](../E08-academic-benchmarks/). `results/development` and `results/fresh`
contain final temporal predictions, groundings, per-case metrics and manifests.
`results/fresh-baselines` contains the comparable fresh baseline results.

## Frozen design

The original five are development cases with known failures. Before implementation
or new inference, we froze qids **2428, 10243, 1678, 2967, 1548**: the first five
in ascending SHA256(`real-academic-pilot-v1:qid`) order after excluding all four
original YouTube source videos. No missing case was replaced. They span five
new source videos. Public case files contain only qid, vid, query and duration;
references are separate and enter only the scorer. The new subset was used once
with the frozen v2 prompt; it is now consumed validation data, not a permanent
unseen test set or the benchmark's official held-out test split.

All conditions see the same centre frame per two-second window. The catalogue
call is blind to the query. REAL temporal reads chronological role/shows text
from that catalogue and makes **one additional text-only model call** per case.
Direct vision makes one query-conditioned image call. These have unequal total
inference budgets; we do not present them as equal-cost methods. No transcript,
reference interval, saliency label, or oracle tag enters either model request.
No model tools, filesystem context, web access or repository memory are supplied.

`ground.py` derives boundaries from first/last observation IDs; it does not allow
invented times or interpolate unseen gaps. Alternatives may overlap, and stable
sorting by the model's confidence defines rank. Coordinates, scores and tied
order are unchanged. The official evaluator and all reference answers remain
unchanged. Every selected case stays in the denominator, including failures.

The final validation artifact checks that the final production resolver returns
all ten frozen predictions unchanged and that the inference prompts are exactly
those saved in the raw calls. Inference manifests retain the source hashes at
the time each run started; later integration fixes affect binding confidence,
creator revisions and exports, not the frozen retrieval predictions.

## Remaining failures

- **193** now selects 108–124s for the ghee presentation (reference 106–124).
- **9823** now selects the opening 0–32s interview event instead of returning no match.
- **6383** now selects 112–140s of shopping instead of isolated mirror frames.
- **7416** now selects the 18–50s product-page event and explicitly records the
  product-type mismatch, rather than pretending a supplement is a beauty cream.
- **3666**, still wrong at rank one: 120–132s indoor hallway vs reference 82–104s
  covered walkway. A matching 84–102s alternative is present but ranked lower.
- **1678**, fresh cycling failure: 82–108s is only 26/54 of the 82–136s annotated
  event (IoU ≈ .481), narrowly below .5. Other cycling recurrences exist too.
- **2967**, fresh berries failure: 12–24s cuts the event too early relative to
  16–50s. The wider action context is still lost.

No predictions were manually widened, reordered using answers, or replaced to
obtain a perfect score. Next work should improve event completeness and ranking,
then freeze another source-disjoint validation subset before evaluating it.

## Real pipeline changes

- Structured observations are optional catalogue fields, preserved by the builder.
- `ground.py prepare/resolve` provides model instructions, evidence validation,
  stale-input protection and source-time intervals. `bind.py --groundings`
  applies these to actual notebook components while respecting creator tags.
- `build.py` carries source windows, limitations and alternatives into `reel.json`.
  Unsupported inspected events become stubs. Partial/ambiguous matches stay flagged.
- Source in-points survive picture and source-audio FCPXML export. Overruns are
  refused. Explicit audio intervals are checked before use and kept separate.
- The tracks page shows the selected source thumbnail and alternative events.
  Source revisions retain the clock and linked audio; creator choices survive
  rebuilds, and changing assets clears stale source coordinates.

The academic metric still tests the selection component. The additional synthetic
integration test checks an actual notebook → bind → build → FCPXML path with a
six-second source in-point for both video and audio. It does not establish
full-pipeline editing quality or verify a Final Cut application import.

## Cost and verification

25 new calls cost **$1.149150**: $0.136626 for development v1, $0.142902 for
v2, $0.718066 for both fresh baselines, and $0.151556 for fresh temporal grounding.
The development catalogue was reused from E08. A complete temporal condition costs
$0.613062 on the original set ($0.470160 catalogue + $0.142902 grounding), and
$0.655036 on the fresh set ($0.503480 + $0.151556). Replays make zero new calls.

**40 core checks + 12 temporal tests + 19 academic tests pass (71 total).**
This includes exact reproduction of the authors' provided 1,550-query sample
metrics; that check is evaluator verification, not REAL performance. The tracks
JavaScript also passes a V8 compilation check. Logs and final source hashes are saved.

## Reproduce and inspect

Working branch: `codex/hardening`, worktree:
`/media/shared/seagate/REAL/codex-hardening`.
All new video data, inference records and temporary files live under its
`bench/work/`. The worktree was relocated from `/tmp/real-codex-hardening` after a
full-filesystem error. Old artifacts retain their original paths and hashes;
`bench/work/storage-migration.json` records the mapping. Main branch was not switched.

```sh
# Fresh root: fetch the same pinned annotations/evaluator, then select without labels.
python3 -m bench.academic.data fetch --root bench/work/academic-fresh
python3 -m bench.academic.data prepare-qvh --root bench/work/academic-fresh --limit 5 \
  --exclude-inputs bench/work/academic/qvh/inputs/cases.jsonl
python3 -m bench.academic.data media-qvh --root bench/work/academic-fresh
# Use NEW run paths; historical runs and their failure records stay immutable.
python3 -m bench.academic.pilot --root bench/work/academic-fresh \
  --out bench/work/academic-fresh/qvh/runs/new-baselines
python3 -m bench.academic.temporal --root bench/work/academic-fresh \
  --cached-catalogues bench/work/academic-fresh/qvh/runs/new-baselines \
  --out bench/work/academic-fresh/qvh/runs/new-temporal
python3 -m bench.academic.report --root bench/work/academic-fresh \
  --run bench/work/academic-fresh/qvh/runs/new-temporal
```

See the [production workflow](../../skills/batch-2/skills/real-storyboarding/references/temporal-grounding.md).
Results are copied explicitly, not managed by the older `experiments/sync.py`.
Model outputs are stochastic; a new call need not reproduce saved predictions.
Use `temporal --replay-source OLD_RUN` with the same catalogue to revalidate saved
responses without inference. Historical manifests pin the exact prompts and code.

Data/evaluator attribution and licenses remain those pinned in
[the academic suite](../../bench/academic/README.md) and `sources.lock.json`.
QVHighlights annotation-derived records retain the dataset's CC BY-NC-SA 4.0
terms; evaluator code is MIT. Video mirrors have recorded provenance/hashes,
but byte identity with the authors' archive is unverified. No footage or extracted
frames are committed. Audio evaluation, exact frame boundaries, a full validation
run, and MEDit timebase verification remain outstanding.
