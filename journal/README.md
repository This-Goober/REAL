# 🔬 Capability Journal

This is the **ongoing** track of the project. The [skills batches](../skills/) state and
illustrate our vision for a complete AI-assisted video-editing workflow — that vision is
the North Star. This journal is how we test whether the North Star is reachable:
**one unit at a time.**

## What a unit is

One unit = **one capability**, studied in isolation:

- **one question** — a single, narrow "can the agent actually do X?"
- **one journal entry** — question → method → measurement → result → where it would
  slot into the workflow → limits
- **one demo** — a short video showing the capability working (or failing) for real

A unit is *not* a feature, a release, or a redesign of the workflow. Proving a capability
and proposing where it would insert into the pipeline is a complete contribution on its
own. Periodically, capabilities that hold up get folded into the next revision of the
skills — that's the only way the shipped workflow changes.

## Why this track exists

We're a two-person student team. Designing, building and field-testing a full production
pipeline is a season of work; measuring one capability is an afternoon. The vision has
had its two full iterations ([batch 1](../skills/batch-1/) built and field-tested,
[batch 2](../skills/batch-2/) rebuilt from the findings). From here the honest, sustainable
unit of progress is the probe: small, measured, demonstrated, filed.

The standard a probe has to meet is the same one the whole repo runs on: **numbers, not
impressions.** Every entry says what was measured and how to reproduce it.

## Index

| # | Capability | Question | Verdict |
|---|---|---|---|
| [001](001-word-anchor-snapping/) | Word-anchor snapping | Can media placements land on the *exact spoken word*, and how accurate is the clock that puts them there? | ✅ Works with a **measured** clock; estimated clocks drift coherently (28% on one beat) — measurement is non-optional |

## Entry template

```markdown
# NNN — <capability name>

**Question.** One sentence.
**Status.** ✅ demonstrated / ⚠️ partial / ❌ not yet
**Demo.** link to the video

## Method
## What we measured
## Result
## Where it slots into the workflow
## Limits
## Artifacts
```
