# Batch 2 — the `/real` skills (testing in progress)

The pipeline rebuilt from Batch 1's documented failures:

1. `skills/real-brainstorm` — idea → script notebook + plain-language SHOTLIST
2. `skills/real-create-catalogue` — scan, group, rename (with approval), describe
3. `skills/real-storyboarding` — measure the narration, bind media, the
   tracks-page review loop; finalizes the authoritative `reel.json`
4. `skills/real-compile` — translate to FCPXML with parity accounting; zero
   editorial decisions

**Honest status:** every Batch-1 finding maps to a change in this batch, and
a 21-check regression suite pins them
(`skills/real-storyboarding/tests/regression.py` — run it from inside
`skills/`). But this batch has **not yet carried a full real project** from
idea to a Final Cut import. Until it has, treat it as a well-founded
hypothesis, not a conclusion.

[`REAL-PIPELINE-MANUAL.md`](./REAL-PIPELINE-MANUAL.md) is the step-by-step
user manual — what you bring to each skill, what happens, what you get out.
The [responsibility matrix](./skills/real-storyboarding/references/responsibility-matrix.md)
defines one owner per decision and the one authoritative handoff.
