# REAL Pipeline — Claude Skills for Video Reel Production

An experiment in building and **field-testing** AI agent skills against real
creative work: taking a short-form video from idea → script → catalogued
footage → storyboard → an editable Final Cut Pro timeline.

Two generations of the pipeline live here, and the honest difference between
them matters:

| | Status |
|---|---|
| [`skills/batch-1/`](skills/batch-1/) | **Field-tested.** Four skills run against real productions across four logged sessions. Its centerpiece is the [**Workflow Gap Report**](skills/batch-1/GAP-REPORT.md) — everything that broke, why each break was dangerous, and what we measured. |
| [`skills/batch-2/`](skills/batch-2/) | **Rebuilt from those findings.** Four `/real-*` skills where each Batch-1 gap is structurally impossible or pinned by a 21-check regression suite. Regression-tested, **not yet field-tested** — treat as a well-founded hypothesis until a full real project has run through it. |

If you're here to learn, start with the
[Gap Report](skills/batch-1/GAP-REPORT.md). If you're here to build, read the
[user manual](skills/batch-2/REAL-PIPELINE-MANUAL.md) and the
[responsibility matrix](skills/batch-2/skills/real-storyboarding/references/responsibility-matrix.md)
before installing anything.

## The one-line thesis

> A random error looks like noise. A coherent error reads as an editorial
> fact. Agent pipelines fail dangerously when they fail *coherently* — so
> every step here is built to refuse, flag, and ask rather than quietly
> guess.

## Method

Each skill was tested by running it on real work and logging every deviation
verbatim: prompts, observed behavior, interventions tagged **[BAKE IN]**
(belongs in the skill) vs **[PER-USE]** (legitimately situational), root
cause, revised skill. The full record is
[`skills/batch-1/TEST-LOG.md`](skills/batch-1/TEST-LOG.md).
