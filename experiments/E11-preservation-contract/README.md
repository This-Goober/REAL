# E11 — Corrections through retiming and rebuilding

Engineering follow-up selected by the authors on 18 October 2026. The
[fixed protocol](PROTOCOL.md) reuses E10's 100 synthetic validation projects,
seeds 1001–1100, with no model calls or native-editor operations. These are
reused fixtures and development diagnostics, not a new held-out evaluation.
The paper and frozen E10 results are not modified by this experiment.

## What is checked

Move one overlay to a different word in every project. Rebuild without changing
the clock; then, in separate copies, shorten all supplied word times to 80%
and lengthen them to 120%. Run the documented clock-swap/retime path, rebuild
with the saved choices, and export again. Check every non-gap placement's
identity and exact frame boundaries against the existing independent reference.
Compare saved creator-owned identity, anchor, requested duration, ownership,
style, layout and source fields separately from the intentionally changed times.
Compile each retimed story twice and compare bytes.

All 100 seeds are eligible: 52 selected image overlays and 48 text overlays.
There are 478 creator-owned layers after the corrections. Each time scale has
its own denominator of 100; the two scales are not 200 independent projects.

## Defects found and corrections

1. **Exact half-frame rounding.** In the frozen code, 8.55 seconds at 30 fps
   becomes `256.50000000000006` frames when evaluated as `seconds * 3000 / 100`.
   It rounds up to 257, whereas the declared reference's `round(seconds * 30)`
   returns the even frame 256. The same issue occurs at 20.35 seconds, producing
   611 instead of 610. Forming the frame rate before multiplication removes
   that extra arithmetic step. The shared utility's three vendored copies are
   updated together. Tests include both failing endpoints and an odd-half tie;
   the earlier checks on both sides of half-frame boundaries remain in place.
2. **Style ownership on rebuild.** The saved style value survives, but its
   `style_by` label is recreated as model-selected. Add that ownership field to
   the existing preservation list. A focused test failed before this correction
   and passes afterwards; additional tests retain model-owned styles and leave
   unconfirmed layers to the new plan.

The candidate is the frozen E10 revised tree with those two corrections and
their tests. It does not import unrelated live title/export changes. The
[source delta](candidate-relative-to-e10.patch) is for reproducing this candidate
from that exact snapshot; it is **not an update patch for PR #3**.

## Run history and verification

The first frozen-code run is retained, including its two one-frame failures.
A first corrected run is also retained. Their generated silent narration file
was shared under the captured media folder; the recorded input bytes did not
change, but an extra generated file was added. Audio quality is outside the
visual checks. To remove that concurrency ambiguity, the harness was changed
to give each export its own generated-audio folder and to reject changes to
the captured input file inventory. Both code versions are repeated under that
same isolated harness. No reference, intervention selection or primary scoring
rule is changed.

## Completed isolated comparison

Every seed completes both conditions; no failures or ineligible cases are
removed. Each cell below has a denominator of 100 projects.

| Check | Frozen ×0.8 | Frozen ×1.2 | Corrected ×0.8 | Corrected ×1.2 |
|---|---:|---:|---:|---:|
| Initial corrected target and complete placement agreement | 100 | 100 | 100 | 100 |
| No-op rebuild: complete placement agreement | 100 | 100 | 100 | 100 |
| Retimed export: complete placement agreement | 99 | 99 | 100 | 100 |
| Post-retime rebuild: complete placement agreement | 99 | 99 | 100 | 100 |
| Saved primary creator-choice fields preserved | 100 | 100 | 100 | 100 |
| Additional human style-ownership labels preserved | 12 | 12 | 100 | 100 |
| Repeated compilation: identical XML bytes | 100 | 100 | 100 | 100 |

The frozen code's two timing failures are seed 1077 at ×0.8 and seed 1034 at
×1.2; each has one base-video endpoint one frame late. All 184 human style
ownership labels lost across 88 projects are retained after the correction.
The primary ownership field `chosen_by` survives in both versions; this is a
separate defect in the style-specific ownership metadata, not lost style values.

The separate clipped-cue fixture passes in both versions: a requested
1.4-second caption clipped to 0.1608 seconds near the beat end recovers all
1.4 seconds when moved earlier. After the ×0.8 timing change it is clipped to
0.1284 seconds and again recovers 1.4 seconds after moving earlier.

The final isolated runs reproduce the first runs' **entire result and summary
files byte for byte**, including the original failures. Captured input bytes
and file inventories are unchanged in the isolated runs. The retained-output
auditor recomputes all 200 result rows for each run from the saved reels and
XML; it does not just read the success flags. All four runs have the same
selected interventions. See [repeat comparison](results/repeat-comparison.json)
and each run's `audit.json` and `source-differences.json`.

Software verification is reported separately: 10 harness/accounting tests,
34 tests on the candidate source, 38 on the live source, and the existing
40-check integration regression pass. Before/after failure logs are retained
under `results/tests/`; these overlapping suites are not additional projects.

Full working inputs, source snapshots, XML, reels, differences and command logs:

- `bench/work/preservation-contract-20261018-frozen-e10`
- `bench/work/preservation-contract-20261018-corrected`
- `bench/work/preservation-contract-20261018-control-isolated`
- `bench/work/preservation-contract-20261018-corrected-isolated`

## Reproduce

Use a new output directory for every invocation. Full E10 working inputs and
its verified synthetic media pool must be present; compact E10 summary files
alone do not contain the input projects. Python 3.12 was used for these runs.

```sh
python3 -B -m unittest bench.test_preservation_study
python3 -B bench/preservation_study.py \
  --projects bench/work/submission-assembly-validation --pool bench/work/pool \
  --out bench/work/new-preservation-control --jobs 3

# Make a separate candidate from E10's snapshot, then apply the recorded delta.
cp -R bench/work/submission-assembly-validation/snapshot/current/skills/batch-2/skills \
  bench/work/new-preservation-candidate
patch -p4 -d bench/work/new-preservation-candidate \
  < experiments/E11-preservation-contract/candidate-relative-to-e10.patch
python3 -B bench/preservation_study.py \
  --projects bench/work/submission-assembly-validation --pool bench/work/pool \
  --candidate-skills bench/work/new-preservation-candidate \
  --out bench/work/new-preservation-corrected --jobs 3
python3 -B -m bench.audit_preservation bench/work/new-preservation-corrected \
  --out bench/work/new-preservation-corrected/audit.json
```

This supports a bounded engineering statement about anchor corrections in the
existing 30 fps, tagged-asset, zero-source-in-point grammar. It does not test
new speakers, arbitrary revisions, rendered appearance, native playback,
participant benefit or a model's ability to make the correction. Duration edits
are notebook changes in the supported interface; the separate clipped-cue
fixture checks recovery of a previously requested duration, not a new duration
revision command. Author review is required before adding a paper claim.


## Unified-source follow-up after review

Fable reviewed the scope and outcomes. The
[unified-source protocol](UNIFIED-SNAPSHOT-PROTOCOL.md) reruns assembly and
repairs on the same corrected pipeline before manuscript integration.
The [parity receipt](results/unified-snapshot/parity.json) shows an unchanged
100-project summary and byte-identical model replay. The only development
quality change is estimated-clock seed 21's timeline length (1081 to 1082
frames) and consequent coverage diagnostic; all 30 measured projects and
repairs remain exact. This difference is retained, rather than claimed as
full-summary parity. The manuscript now includes the bounded finding and
reused-cohort chronology; final author approval remains pending.


## Portable evidence package

`REAL-preservation-unified-20261018-v2.zip` (distributed outside the repository; SHA-256 `56af08815b179730ebf67fb6dfe4d33f118a1dd8e2aa73716ccacd1cd0fcf74b`) contains complete
isolated control/corrected runs, the unified assembly/repair/replay source and
outputs, all synthetic input media, compact records, protocols and offline
reproduction instructions. It is internal identified evidence, not an anonymous
supplement. Its separate checksum/verification receipt is under `paper/artifacts/`.
The first packaging attempt retained a stale README checksum; it is withdrawn
as a delivery, with its log retained. No experimental record was changed.
