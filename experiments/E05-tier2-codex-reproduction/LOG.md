# E05 log

- **2026-10-17 19:21** Codex delivered the ground-truth package (now `bench/ground-truth/`).
- **19:40** First attempt: `voice.py measure` refused, OOV words `dot-product`, `feed-forward`,
  `softmax`. Aligner now composes compound pronunciations from dictionary parts.
- **19:42** Alignment then failed outright: REAL's word list contained the shot descriptions.
  Parser defect (descriptions ending in "." typed as narration). Fixed, regression check 17;
  the same defect had inflated the skills' own example by 2.0 s (check 18 added).
- **19:47** Empty beat from the notebook's preamble; planner fixed.
- **19:55** Mode A scored. Mode B refused by compile (zero-handle clips); `clamp_held_cuts` added.
- **20:03** Modes B and C re-run started on the live tree (its skill files then matched 9ff7a8b).
