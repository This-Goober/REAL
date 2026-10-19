# E03 — One-shot LLM baselines

**Question.** Given REAL's notebook, labelled catalogue, measured word times and
revision plan, can a model write the project file directly in one response,
without scripted compilation or a validation/repair loop?

**Status.** Offline retrospective scoring completed on 2026-10-18: 180 retained
attempts, 179 XML outputs, all 30 development seeds retained per condition.
See [the replay results](results/offline-20261018/README.md) and
[replay protocol](OFFLINE-REPLAY.md). No new inference was used for scoring.

With format notes, REAL, Opus and Fable are exact on all 30 projects; Sonnet is
exact on 27/30 with mean temporal F1 .991. Without format notes, mean F1 is
.948/.964/.958 and 22/26/26 outputs pass both format checks. These are
retrospective development results, not a general superiority or equivalence claim.

## Design

`bench/oneshot_llm.py` builds one prompt per project: the notebook, the labelled catalogue,
the measured word times, the creator revisions, the placement semantics written out, and
(in the default variant) REAL's own FCPXML generator notes. The model's first answer is the
deliverable. Called through `claude -p` with tools disabled.

| condition | model | FCPXML rules in prompt |
|---|---|---|
| `oneshot-claude-sonnet-5-5` | Claude Sonnet 5.5 | yes |
| `oneshot-claude-opus-5-5` | Claude Opus 5.5 | yes |
| `oneshot-claude-fable-5-1` | Claude Fable 5.1 | yes |
| `…-norules` | same three | no ("write FCPXML 1.13 that Final Cut Pro 11 will import") |
| ChatGPT (planned) | Astra | yes; planned as task D4 |

Scored exactly like E01 (same reference, parser, renderer and metrics), plus the
pipeline's own validator.

## Reproduce

```
cd bench
python3 run_oneshot.py work/full --models claude-sonnet-5-5,claude-opus-5-5,claude-fable-5-1 --phase both --lpips
python3 run_oneshot.py work/full --models claude-sonnet-5-5,claude-opus-5-5,claude-fable-5-1 --phase both --lpips \
    --variant norules --results results-oneshot-norules.jsonl
```

## Historical generation observations (superseded by the replay above)

- With the rules in the prompt, a spot check of Sonnet on seeds 1–15 found 14 of 15
  frame-exact (seed 2: placement F1 0.92). Opus and Fable were frame-exact on seeds 1–3.
- Without the rules, 5 of 25 Sonnet files checked had validator errors, all of the kind
  batch 1's field sessions found: stills placed as `<asset-clip>`, or a still's format
  declaring a frame duration. Final Cut rejects both.
- Spend on the first generation pass, averaged over all calls including the ones later
  invalidated: about $0.08 (Sonnet), $0.15 (Opus) and $0.20 (Fable) per call, against no
  model call for REAL's compile.
- These spot checks used projects later regenerated for seeds 3, 10, 16 and 23; the scored
  results will replace them.

## Limits

One model family so far; the prompt hands the model REAL's representations, so this
measures model-as-compiler, not request-to-video.
