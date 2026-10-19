# E11: preservation under a changed clock — fixed diagnostic protocol

This follows the retiming/preservation gap identified in the reviewer's experiment plan (A4) and the
documented `clock.py swap` → `build.py retime` workflow. It is an offline
engineering conformance check, not a participant study or a model comparison.
The paper, frozen E10 results and existing submission package remain unchanged.
The authors selected this follow-up on 18 October 2026. The settings below are fixed
before the full run; this is not an externally preregistered study. No result
is claimed in this protocol.

## Fixed inputs and scope

- Reuse all 100 E10 validation projects, seeds 1001–1100, without selection
  based on this follow-up's outcomes. These are reused fixtures, not fresh
  held-out projects or a population of creator edits.
- Use the exact hash-verified E10 revised skills and the existing synthetic
  media. Snapshot the harness and inputs separately; do not substitute the
  evolving live title/export code or rewrite E10 evidence.
- Keep the existing 30 fps, tagged-asset, zero-source-in-point grammar and
  ordinary inline overlays. This check does not establish other frame rates,
  arbitrary source windows, native appearance, audio quality or all revisions.
- No model calls, native editor operations or paid inference.

## Interventions and workflow

For each seed, use the existing repair eligibility rule and deterministic
`Random(seed * 31337)` selection: an overlay moves at least two words, stays
inside its beat and initially has its requested duration plus 50 ms available.
Retain an explicit ineligible row if none exists; never silently remove a seed.

1. Apply the one-line anchor correction to a copy of the original revised reel.
   Check the target against an independent expectation before proceeding.
2. Rebuild using the same clock and `--preserve` the corrected reel. Check saved
   choices and the complete non-gap identity/boundary multiset (no-op control).
3. In separate copies, multiply every original word start/end by **0.8** and
   **1.2**, rounding the supplied word times to milliseconds. Keep words,
   indices, asset choices and requested overlay durations unchanged. These
   are two artificial global time scales, not recordings of new speakers.
4. Run the documented clock-swap/retime path on each corrected reel. Compare
   the exported placements with the unchanged independent reference semantics
   evaluated on the new supplied times and corrected anchor.
5. Rebuild each retimed reel with `--preserve`, compile it again and check that
   saved choices and exported placements survive. Compile the same story twice
   to check byte determinism separately from retiming correctness.

Absolute endpoints round once to the 30 fps grid using the declared ties-to-even
rule. Ordinary overlays clip to the new beat end. Requested duration remains
distinct from visible clipped duration. A controlled clipped-cue fixture should
also verify that moving an overlay earlier restores its requested duration.
Duration edits are notebook changes in the documented interface, not supported
revision commands; do not misclassify their rejection as a preservation failure.

## Outcomes and accounting

Primary checks: correct target after the initial repair; complete placement
identity/boundary agreement after retiming; saved identity, anchor, requested
duration, ownership and style fields unchanged. Record source bounds as well.
The primary ownership field is `chosen_by`. Check the saved asset/content,
anchor word/text, offset, duration source/request, style/font/layout and source
bounds on creator-owned placements. Record `style_by` changes separately as
additional ownership metadata; do not silently merge them into timing accuracy.
Report no-op rebuild, post-retime rebuild and repeated compilation separately.
Times intentionally change with the clock; do not count those as collateral.
Reference differences after the declared retiming are errors, not exclusions.

Retain one row per seed and time scale, with stage failures and ineligible seeds
explicit. Freeze the selected interventions and source/input hashes before the
full run, retain logs and per-case differences, and verify hashes afterwards.
Preserve the first run even if a defect is found. Any fix requires a separate
source snapshot and rerun; it must not replace the original result or E10.

The fixture assertions and accounting tests are software checks. Any eventual
paper statement needs owner review of the outcomes and their limited scope.
