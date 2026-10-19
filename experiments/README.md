# Experiments

**Current paper evidence (2026-10-18): [E10 submission validation](E10-submission-validation/).**
It records a fresh 100-seed structural comparison, the precision correction,
30 development repairs, official-evaluator parity, and public-pilot replay.
The E01–E07 progress table below and `STATUS.md` describe the historical runs
managed by `sync.py`; they are not the status of E10.

[E11 retiming/preservation diagnostics](E11-preservation-contract/) reuse the
100 E10 fixtures. They expose and fix a half-frame rounding defect and lost
style-ownership metadata; the corrected source passes both artificial clock
changes. E11 remains separate follow-up evidence pending paper review.

One folder per experiment. Each has:

- `README.md`: the question, design, conditions, exact commands to reproduce, status, results and findings, limits.
- `LOG.md`: dated record of every run: which skills commit, what changed, what went wrong and how it was handled.
- `results/`: the small result files (JSON, JSONL, Markdown summaries), refreshed by `python3 experiments/sync.py`.

The harness code lives in [`bench/`](../bench/) because several experiments share it. Raw outputs (rendered videos, per-project working folders) live in `bench/work/` and are not committed; every README says where. [`STATUS.md`](STATUS.md) is rewritten by `sync.py`.

| id | experiment | question | state |
|---|---|---|---|
| [E01](E01-synthetic-assembly/) | Synthetic assembly | Does the compiled project match an independent reference frame for frame? | running (7/30 seeds) |
| [E02](E02-estimated-clock/) | Estimated vs measured clock | What does measuring the narration buy? | running, shares E01's run |
| [E03](E03-oneshot-baselines/) | One-shot LLM baselines | Can a frontier model write the project file directly from the same inputs? | generated, scoring pending |
| [E04](E04-repair-locality/) | Repair locality | When one thing is corrected, what else changes? | not started |
| [E05](E05-tier2-codex-reproduction/) | Reproducing Codex's generated films | How close does REAL get to an independent editor's cut of generated content? | mode A done, B and C running |
| [E06](E06-forced-alignment/) | Forced-alignment accuracy | How precise is REAL's measured clock on a real voice? | 1 of 2 films |
| [E07](E07-generated-tutorials-astra/) | Astra's generated tutorials | The same as E05 with a neural voice and Astra's own cut | waiting for Astra's files |
| [E08](E08-academic-benchmarks/) | Academic benchmarks | Can REAL select relevant footage and its temporal extent without reference tags? | QVHighlights five-case pilot complete; MEDit adapter ready, timebases unresolved |

| [E09](E09-temporal-grounding/) | Temporal grounding | Does matching complete source events improve retrieval and survive export? | original 4/5; fresh 3/5; 71 checks pass |

## Conventions

- **Pin the code.** Pipeline conditions run a frozen checkout of the skills (`bench/work/eval-skills`, git worktree at 9ff7a8b), never the live `skills/` tree another agent may be editing. Every result row records the skills commit it ran on (`"skills"` field), with `+dirty` if the checkout had local changes.
- **Never tune the reference to the code.** A change to a reference (`bench/project.py` semantics, `bench/ground-truth/`) needs a LOG note saying which results it invalidates.
- **Invalidate, don't delete.** A run that turns out to be wrong stays in the LOG with the reason; its rows are dropped from `results/`.
- **Numbers in READMEs are dated.** The authoritative values are in `results/` after the latest `sync.py`.

## Findings across experiments

Defects the experiments found in the skills (details in journal entries 002 and 003):

| defect | found in | status |
|---|---|---|
| beats opened 3–4 frames late (base shot cut 40 % into its first word) | E01 | fixed |
| timed insert cut the running shot short, beat went black | E01 | fixed |
| explicit durations overwritten after the first derivation | E01 | fixed |
| "measure first" in SKILL.md, not in clock.py | E01 | fixed (`clock.py time --measured`) |
| re-anchored hold left the beat stretched | E01 | fixed |
| validate tokenised narration differently from the clock | E01 setup | fixed |
| visual descriptions ending in "." counted as speech | E05 | fixed, regression check 17 |
| aligner writes `s`/`e`, clock read `start`/`end` | E05 | fixed |
| compound technical words unpronounceable to the aligner | E05 | fixed (composed from parts) |
| prose before the first heading became an empty beat | E05 | fixed |
| silence between lines always black | E05 | opt-in fix (`--pauses hold`) |
| held shot longer than its clip | E05 | fixed in 9ff7a8b, verification running |
| re-anchoring a clipped cue keeps the clipped length, not the explicit duration | E01 | open |
