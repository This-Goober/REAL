# Run log

- 2026-10-17: Initial work blocked before execution by ENOSPC in both sandbox
  startup and approval-review initialization. User cleared space and selected
  Seagate. Moved the existing clean `codex/hardening` worktree across filesystems
  and repaired Git's pointer; file-mode tracking disabled for this worktree.
- Froze five new source-disjoint identities before implementation/inference.
  No labels were read into inference. Downloaded all five media files; no replacement.
- Development temporal v1 used five saved blind catalogues plus five text calls.
  Strictly rejecting overlapping alternatives caused two avoidable validation
  failures: q6383 and q7416 had plausible full-event top proposals and narrower
  alternatives. Original output JSONL retained. Revalidating complete ranked
  alternatives without changing their values gives 4/5 and mAP 59.17.
- Development v2 emphasized semantic roles, viewpoint and action shape. It again
  gets 4/5; mAP 56.88. It does not fix the hallway ranking. We froze v2 for fresh
  evaluation rather than choosing the better v1 mAP post hoc.
- Fresh baseline run: five blind-catalogue and five direct-vision calls. Two direct
  responses contained valid proposals listed out of confidence order. Preserved
  original failure rows; offline replay stably sorted the unchanged confidence
  values for a fair ranked comparison. No new calls or timestamp edits.
- Applied the same confidence normalization to temporal outputs before fresh
  temporal inference. Five new text-only calls; no rejected or omitted cases.
  Scored once after predictions were complete: lexical 0/5, direct 3/5 (mAP 32.83),
  temporal 3/5 (mAP 25.75). References then inspected to characterize failures.
  No further prompt tuning followed inspection of fresh scores.
- Added pipeline source coordinates, source-audio preservation, creator revision
  support, preview event choices and contract fields. First integration test
  attempt lacked required fixture metadata (`open` and `assets_root`); fixtures
  corrected, not relaxed compiler validation. All 12 temporal tests pass.
- Final 40 core checks and 19 academic tests pass. Node was unavailable for the
  attempted JS check; the shipped script was then successfully compiled in V8.
  Final production validation reproduces all ten selected temporal predictions
  and the exact prompts. New calls: 25; total $1.149150. No frozen ground truth,
  reference intervals, upstream metric code, or old experiment outputs changed.
