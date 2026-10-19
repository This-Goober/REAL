# E01 log

- **2026-10-17 18:25** Harness written; 3-beat smoke project frame-exact after fixing the
  composer's ffmpeg input indexing (renders were wrong, not REAL).
- **18:36** First 30-seed run started (3 conditions). Killed at 18:48: decoding read full
  frames and would have taken hours. Decoder changed to read only the marker rows.
- **18:59** Restarted at half-resolution renders (cost only; the decoder locates strips
  proportionally). Completed 10 seeds.
- **19:10** Seeds 9 and 10 failed. Seed 10's revised failure was a REAL defect (re-anchored
  hold left the beat stretched; journal 002-E). Seed 9's published failure is defect 002-C,
  already fixed in revised. Measure-first (002-D) and the refit fix added.
- **19:15** Found that 4 of 30 projects (seeds 3, 10, 16, 23) put an overlay where REAL's
  documented hold rule applies, which the reference does not model. Generator fixed to keep
  every overlay inside its line at its default anchor; only those 4 projects changed
  (verified byte-identical for the other 26). Ledger decision not filed at the time: recorded
  here and in journal 002. All earlier results invalidated; run restarted from scratch.
- **19:20–20:06** 7 seeds complete on the live skills tree. The tree's skill files at that
  time match commit 9ff7a8b (Astra's baseline), so these rows are valid for 9ff7a8b.
- **20:06** Astra began editing the live skills tree on branch `astra/hardening`.
- **20:12** Run stopped; evaluation pinned to a frozen worktree at 9ff7a8b; restarted with
  `--resume` (7 seeds kept, 23 to run). Each row now records its skills commit.
