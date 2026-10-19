> **Anonymous submission boundary (18 October 2026):** v7 preserves the named
> short-paper predecessor. The current anonymous PDF/source and the authors' full v4
> playback confirmation postdate it. This research ZIP contains identifying
> metadata, archives and unmasked internal evidence. Do not upload it as an
> anonymous supplement. See `paper/himas-2027/ANONYMITY.md`.

# REAL research artifact — frozen review package

Start by downloading and extracting
`REAL-HIMAS-2027-artifact-v7.zip` (distributed outside the repository; SHA-256 `2f9af73628f6431e9559f51971d2e7297dd5a6393d994a8bc670b44b279d6ddc`).
Its checksum is in the adjacent `.zip.sha256` file. Run the commands below inside
the extracted `REAL-research` folder. This is a local review candidate, not a
submitted or author-approved package.

The package combines the current nine-body-page short-paper manuscript with the exact
experiment implementation and data from verified v5. The frozen E10 code remains
at `skills/batch-2`, even though the live repository has later title changes.
The 180-attempt direct-model analysis is included as a separately frozen
[offline replay supplement](../experiments/E03-oneshot-baselines/results/offline-20261018/README.md).
Its executed scorer, prompts and responses are inside `replay-inputs.zip`.
The package manifest records the base archive hash and every replaced path.

The original
[v5 archive](../paper/artifacts/REAL-HIMAS-2027-artifact-v5.zip) remains unchanged
(SHA-256 `5eea96567a69e5200ab4f2f5033b5643876d510b1cc2ff098473ac1323300526`).
The ten-page predecessor and full expanded manuscript are preserved under
`paper/review-archive`; the earlier v6 package remains a separate historical
release in the development repository.
The new package contains no complete production recording or Paganini tutorial
ZIP. No Git clone, model account or Final Cut installation is needed for the
E10 offline checks below. Full E03 validity replay additionally requires a local
copy of Apple's hash-matching proprietary DTD and `xmllint`; follow its README.

The benchmark result is bounded: the revised implementation preserves placement
identity and timing on 100 generated projects, improving on REAL's own earlier
implementation. The public retrieval pilot is mixed; the next 100-query model
comparison has not run. Software fixtures are not model-performance evidence.

## Setup and quick checks

Use Python 3.13 and FFmpeg/FFprobe on PATH. The recorded environment used Python
3.13.5; exact Python package versions are in the lock file. Installing missing
dependencies requires network access. All commands after setup work offline.
Run from the extracted package root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r experiments/E10-submission-validation/requirements.lock.txt
export PYTHONDONTWRITEBYTECODE=1
.venv/bin/python research-artifact/verify.py
.venv/bin/python -m bench.audit_submission
REAL_ACADEMIC_DATA=artifact-data .venv/bin/python -m unittest \
  bench.academic.test_academic bench.academic.test_refine \
  bench.academic.test_compare bench.academic.test_preflight \
  bench.academic.test_budget bench.academic.test_suite bench.test_assembly_study
.venv/bin/python paper/himas-2027/make_results.py
```

The file verifier checks every packaged file against `ARTIFACT-MANIFEST.json`.
It also checks the frozen E10 snapshots, the exact synthetic pool, and the pinned
official evaluator/data against their original evidence hashes. It detects
changes relative to the manifest; it is not a cryptographic signature.
The evidence audit recomputes the three saved assembly summaries and checks that
the packaged skills match the evaluated revision. It should run in this extracted
package, rather than the evolving live checkout. The 48 benchmark-tool
tests include official scoring parity over 1,550 author sample predictions.
Tests substitute fixture responses for paid inference.

## Rerun the reported experiments

```sh
# All 100 validation seeds, all three conditions. Use a new output directory.
.venv/bin/python bench/assembly_study.py bench/work/artifact-validation \
  --pool artifact-data/synthetic-pool --n 100 --seed0 1001 --jobs 3 \
  --baseline-snapshot frozen/assembly-validation/baseline
# Re-score the existing public pilot and official sample; no model calls.
.venv/bin/python -m bench.academic.recheck_submission \
  --root artifact-data --out bench/work/artifact-public-recheck
```

The new assembly summary should match
`experiments/E10-submission-validation/results/assembly-validation/summary.json`.
Elapsed times and machine paths can differ. Exact input media is included to
avoid platform font/encoder differences in regenerated synthetic assets. The
generator remains `bench/synth.py`. The baseline snapshot must match every hash
recorded for commit `16c34d59f7db1ca0618e35fbcdaaf30a4494c952`; changed baseline
files are refused. Git history is unnecessary in this mode. Source hashes, not
a missing checkout's HEAD, identify the new run.

For local-repair reproduction, run the assembly command in a new directory with
`--n 30 --seed0 1`, then:

```sh
REAL_SKILLS="$PWD/bench/work/artifact-development/snapshot/current/skills/batch-2/skills" \
  .venv/bin/python bench/repair.py bench/work/artifact-development --workers 3
```

Use `bench/work/artifact-development` as the first command's output in that case.
No `--models` option is used. Compare the 30 target-correct flags and zero
collateral identity/boundary changes with the saved repair rows. This does not
measure changes in color, effects, or human effort.

## Contents and provenance

The [two-minute interaction walkthrough](../demo/README.md) can be prepared
without inference or Final Cut:

```sh
.venv/bin/python demo/build.py --out bench/work/himas-demo --pool artifact-data/synthetic-pool
```

Open `bench/work/himas-demo/index.html`. The builder produces before/after
tracks, export reports, and FCPXML, and checks the single anchor correction.
This uses estimated timing and silent synthetic media; it is separate from the
reported measured-input repair experiment and adds no empirical sample.

- `skills/batch-2`: active pipeline code, schemas, examples, and instructions.
- `bench`: assembly, retrieval, scoring, spending controls, and offline tests.
- `experiments/E05-*/results`, `E06-*/results`: saved tutorial and alignment metrics.
- `experiments/E08-*`, `E09-*`, `E10-*`: retained development and validation records.
- `frozen/assembly-{initial,development,validation}`: byte-verified snapshots
  from the three historical runs, including the original harnesses.
- `artifact-data/synthetic-pool`: generated assets from the reported E10 run.
- `artifact-data/sources/qvh`: pinned official evaluator, validation references,
  authors' sample predictions, and original licenses. References are used by
  scoring only. The larger inference runner accepts a separate answer-free file.
- `paper/himas-2027`: manuscript, PDF, standalone LaTeX ZIP, figures, exact figure excerpts and template.

REAL code uses the root MIT license. QVHighlights code and data retain their
respective upstream licenses in `artifact-data/sources/qvh`; query text in saved
case lists derives from that dataset. CEURART files retain their own licenses.
These terms are not replaced by REAL's MIT license. Raw benchmark videos,
complete production recordings, credentials, Git internals,
and conversation logs are excluded. Historical result manifests retain local
paths for provenance; the commands above use package-relative paths.

The full repository contains additional historical documentation linked from
some included READMEs. This review package contains the material needed for the
active paper, not every historical demo. The larger model comparison is deferred.
Author review and completed tutorial demonstrations remain separate work. The E05/E06 metrics can be re-tabulated; the source recording and
reference project are not included, so their original runs cannot be reproduced
from this package alone. The small synthetic tracks screenshot and figure
excerpts are included; public-benchmark contact sheets are excluded.
Five low-resolution frames from Eidee's Paganini tutorial and the compact
before/after revision data are included for the manuscript figures. They do
not include the source video, audio or complete project and are not relicensed
under the code's MIT license. The three included paper figures and two additional plots can be regenerated from
the included inputs using ReportLab and Poppler; see `paper/himas-2027/FIGURES.md`.
The included PDF passes independent PDF/A-1b validation; its report and limits
are in `paper/himas-2027/ARCHIVAL.md`. Rebuilding it requires a fresh check.

## Build this package from the development checkout

```sh
python3 research-artifact/build.py --out bench/work/review/REAL-HIMAS-2027-artifact-v7.zip
```

The builder requires the verified v5 ZIP plus the current manuscript and saved
E03 replay. It validates every base-file hash before replacing only the declared
paper, package instructions and replay paths. It refuses a different base ZIP,
a changed paper receipt, or overwriting an existing output. It does not copy
live experiment code or the production tutorial ZIP. The output has deterministic
member timestamps, a full manifest and an adjacent checksum. Publication is a
separate action.
