# E08 run log

- **2026-10-17:** User approved adding QVHighlights and MEDit-Bench evaluations.
  Added the harness in isolated `codex/hardening`, first checkpoint `493d897`.
  No existing synthetic reference, ground-truth film, or REAL skill was changed.
- Pinned QVHighlights `b7e553ac3b0c898ee6b85e03ee507c064eab89ca` and MEDit
  `87c88bc316ac457088342fa988383f0c3400e091`; verified source hashes. Selected
  five validation IDs by hash before inference and downloaded all five clips.
- `pilot-v1`: CLI transport rejected image-stream input with JSON output before
  model inference. Preserved as a harness failure. Fixed the CLI to stream output;
  a small transport check succeeded. This was not a model performance result.
- `pilot-v2`: ten calls completed with the unchanged sampled inputs, prompts,
  budget and models. REAL binder produced four nonempty and one empty prediction;
  direct vision produced five answers, two with surrounding prose rejected by the
  initial parser. Pre-fix direct R@1/.5 was 40 and mAP 35.
- `pilot-v2-replayed`: accepted the unique intact JSON object from each response,
  using the same general decoder for both conditions. No timestamps, scores,
  catalogue text or REAL thresholds were changed; no new model calls. Verified
  unchanged REAL predictions and the three previously parsed direct outputs.
  Final direct R@1/.5 is 60, mAP 46.93; REAL remains zero at both metrics.
- Official author sample reproduced exactly across 1,550 queries. Final 17
  academic harness checks pass; the existing 40 core regression checks are a
  separate suite and were not rerun for this isolated benchmark addition.
- MEDit prepared: 60 videos / 180 messages / 540 references / 6,231 cuts.
  Timecode audit finds frame fields above 29 for 18 source IDs. Rates cannot be
  guessed from maxima, so actual MEDit editorial scoring remains pending.
