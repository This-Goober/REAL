# E10 — Submission validation

2026-10-18. This experiment separates development, new synthetic validation,
and replay of the public-data pilot. See [the frozen protocol](PROTOCOL.md).
No new model inference was used.

## Completed results

| Condition, seeds 1001–1100 | Pipeline pass | All placements exact | Mean exact-placement F1 [95% CI] |
|---|---:|---:|---:|
| Original measured | 82/100 | 0/100 | .428 [.385, .469] |
| Revised measured | 100/100 | 100/100 | 1.000 [1.000, 1.000] |
| Revised estimated | 100/100 | 0/100 | .011 [.005, .018] |

These are **structural timing/identity** results on generated projects, not
rendering, human preference, or native-editor scores. Exact source/asset frame
agreement is .251 / 1.000 / .228 respectively. There are 1,269 non-gap reference
placements over the 100 new seeds. Failed runs receive zero rather than being
removed. Bootstrap uses 10,000 paired seed draws; its degenerate interval for
perfect sample scores is not a population guarantee.

The imported implementation was exact on 28/30 development projects. Seeds 1
and 14 exposed millisecond rounding across half-frame boundaries. Timing now
retains precision through derivation, revision, retiming, and beat refitting;
the compiler quantizes absolute boundaries once. Four independent fixtures
cover those paths and both sides of half-frame boundaries at five frame rates.
The corrected development run is 30/30. Neither the reference generator nor
the scoring functions were changed to obtain this result.

Thirty development re-anchor repairs all move the target correctly, with zero
non-target changes under the existing event-identity/boundary metric. This
does not measure every visual property or establish human repair efficiency.

The public pilot was re-scored from committed predictions. Fresh-five temporal
and direct-vision R@1 .5 are both 60%; temporal mAP is 25.75 versus direct
32.83. The separately supervised authors' sample predictions score 35.97 mAP
on those same five IDs, saved as context only, not a matched-input comparison.
Official sample metric reproduction over all 1,550 queries passes. A larger
source-disjoint 100-query selection is frozen but has **no REAL results yet**.

The follow-up's 100 clips (82 original source videos, 1.15 GB) are now downloaded
and hash/duration-verified. A fallback-mirror case-mapping bug initially caused
eight false 404s; correcting the folder mapping recovered all eight without
changing query selection. Before/after URL checks, download provenance, and
the prepared runner's code/media hashes are saved under `results/academic`.
The four-condition runner and shared budget checks are implemented; **no paid
inference or next-100 model predictions exist**. The combined benchmark-tool
suite passes 48 tests, with the log in `results/benchmark-tool-tests.log`.
The latest integration test runs real contact-sheet generation, all four
conditions, cached reuse, and official scoring with fixture responses replacing
the paid CLI. It caught and now prevents a resumed run clearing a final-call
cost-overrun flag. These fixtures are software checks, not model-quality scores.
The v2 preparation also freezes the catalogue schema and runtime versions and
prevents simultaneous execution/scoring writes. It supersedes the first plan
before inference; queries, media, prompts, and scoring rules are unchanged.

The fresh-five paired mAP difference (REAL temporal minus direct vision) is
−7.08 percentage points, with an exploratory 95% interval [−24.33, 7.17].
`bench.academic.compare` bootstraps original source videos with all their queries
together, preserving query weighting. It reproduces official aggregate metrics
from unrounded per-query contributions; six offline tests include full 1,550-query
parity, failure accounting, and clustered pairing. This five-source interval is
descriptive and neither establishes superiority nor equivalence.

## Files

- `results/assembly-initial`: imported implementation on development seeds.
- `results/assembly-development`: corrected implementation on development seeds.
- `results/assembly-validation`: frozen corrected implementation on 100 new seeds.
- `results/repair-development.jsonl`: one local repair per development seed.
- `results/academic`: official parity, pilot replay, consumed IDs and next selection.
- `results/academic/next100-run-plan-v2.json`: active frozen source/media hashes for the
  prepared four-condition follow-up; paths describe this Mac's ignored work root.
  The first `next100-run-plan.json` is retained as superseded preparation evidence.
- `results/*/manifest.json`: exact code/media hashes, environment and invocation.

Full XML, reference EDLs, working inputs, logs and frozen code snapshots remain
in ignored `bench/work/submission-assembly-*`. Compact saved result files
are sufficient to rebuild the paper tables; rerunning generates full outputs.
The prior E01–E09 records remain historical and are not silently replaced.
The [review artifact](../../research-artifact/README.md) packages verified
snapshots, exact synthetic inputs, saved results, and pinned official scoring
files for offline reproduction. The assembly runner accepts a verified baseline
snapshot when Git history is absent; this changes packaging, not the reference,
scorer, selected seeds, or evaluated skills.

## Reproduce

Use Python 3.13 (the recorded run used 3.13.5), Pillow, NumPy, FFmpeg and FFprobe.
Academic parity additionally needs the versions in `requirements.lock.txt`.

```sh
uv venv bench/work/paper-env
uv pip install --python bench/work/paper-env/bin/python -r experiments/E10-submission-validation/requirements.lock.txt
export PYTHONDONTWRITEBYTECODE=1
bench/work/paper-env/bin/python bench/synth.py pool bench/work/pool
bench/work/paper-env/bin/python bench/assembly_study.py bench/work/new-validation \
  --pool bench/work/pool --n 100 --seed0 1001 --jobs 3
# Use a NEW output path: existing result directories are refused.
bench/work/paper-env/bin/python -m unittest bench.test_assembly_study
bench/work/paper-env/bin/python -m unittest discover \
  -s skills/batch-2/skills/real-storyboarding/tests -p 'test_*.py'
bench/work/paper-env/bin/python skills/batch-2/skills/real-storyboarding/tests/regression.py
bench/work/paper-env/bin/python -m bench.academic.data fetch --root bench/work/academic
REAL_ACADEMIC_DATA=bench/work/academic bench/work/paper-env/bin/python \
  -m unittest bench.academic.test_academic
bench/work/paper-env/bin/python -m bench.academic.recheck_submission \
  --root bench/work/academic --out bench/work/new-academic-recheck
python3 paper/himas-2027/build.py
```

For the repair reproduction, first run 30 seeds from 1 into a new directory,
then set `REAL_SKILLS` to that run's absolute
`snapshot/current/skills/batch-2/skills` directory and run
`bench/repair.py RUN_DIRECTORY --workers 3`. With no `--models` argument it
makes no model calls. Its counter covers identity and boundaries, not effects.

## Limits and next acceptance gates

1. Broaden native-editor verification beyond the music-video case. On 18 October
   The authors confirmed the corrected v2 piano and lyric layout with two screenshots.
   This closes that case's reported position defect; linked source audio and
   other export features still need application-specific coverage.
2. Freeze the implemented two-call direct-refinement baseline and actual model
   revision before inference. Five offline comparator tests pass; the next 100
   queries remain unrun. Include catalogue and any failed-call costs and retain
   every query. Report source-clustered paired uncertainty before considering
   the full split. Equal call allowances do not imply equal realized cost.
3. Add a small creator error-localization/repair study if claiming interaction
   benefit; the current workshop draft explicitly leaves that claim untested.
