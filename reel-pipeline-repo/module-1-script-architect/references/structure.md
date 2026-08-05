# Structure — intro / body / demo / end

Four roles. Every moment of the video is exactly one of them. They are not
decoration: each has a different job, a different budget, and a different failure
mode, and the audit in `estimate.py` checks the budgets.

## The roles

### INTRO — buy the next ten seconds
Everything before the audience has committed. Its only job is to create a **why**,
not to tell (Principle 2). It ends the moment the video starts explaining.

- Budget: **≤15% of runtime**, hard flag over 18%. On a 60s reel that is 9s.
- Failure mode: *preamble*. Context the audience did not ask for yet.
- The strongest opening for this series is a **sensation, not a claim** — for a
  video about sound, lead with the sound. The Drone 60s cut opens on 5 seconds of
  wrong-then-right with no narration at all, and it works because the hook is the
  thing itself.
- A cold open with no narration is legitimate and often better. Do not assume the
  intro must contain words.

### BODY — the actual argument
The explanation. Split into **2–4 idea chunks**, one per thing the audience has to
newly believe. Each chunk should be nameable in three words ("waves collide",
"perfect ratios", "so intonation matters").

- Budget: the remainder, typically 55–70%.
- Failure mode: *one undifferentiated block*. If a chunk runs past ~25s without a
  demo, a callback, or a turn, flag it — attention decays and the plan should say
  so before the render does.
- Chunk boundaries are natural scene-change points and natural places for the
  script's `---` section breaks.

### DEMO — the narration steps back
Stretches where the sound, the playing, or the action carries the meaning and the
voice gets out of the way. In this series a demo is usually a purpose-shot clip
with its own audio at full (Principle 4 governs ducking everywhere else).

- Budget: 5–15%. Two demos in a 60s reel is plenty.
- **Never estimated.** A demo carries an explicit duration from the director. If
  they have not given one, that is a question in the plan, not a default you
  invent.
- Demos are most powerful in **matched pairs** — same framing, same length, only
  the thing being demonstrated differs, so the ear does the comparing and not the
  eye. When you propose one demo, check whether its opposite belongs somewhere.
- A demo placed immediately after the claim it proves is worth more than the same
  demo at the end.

### END — land it
The payoff and the exit. Not a summary of what was already said.

- Budget: **≤20%**, and the last beat should be short.
- Failure mode: *trailing off*. A second thesis, a list of caveats, a slow fade.
- A **callback** — returning to the exact image or sound from the opening — closes
  the loop and is the series' strongest ending shape.
- Leaving the last 2–4 seconds without narration is good: whatever the video was
  about gets the last word.

## Runtime targets

| Target | Words (at ~3.1 w/s) | Shape that fits |
|---|---|---|
| 30s | ~90 | one idea, one demo, callback end |
| 60s | ~185 | hook · 2 body chunks · 1–2 demos · callback |
| 90s | ~275 | hook · 3 body chunks · 2 demos · payoff + callback |
| 3min | ~550 | full treatment; expect to cut it later |

These assume near-continuous narration. Cold opens, demos, and blanks all buy
runtime without words, so a 60s reel with a 5s silent open and two 4s demos needs
closer to 145 words.

**Report overruns in words, not seconds.** "You're 34s over — about 105 words" is
actionable; "34s over" is not.

## When the script does not fit

Do not cut it yourself. Present the options and let the director choose:

1. **Drop a whole idea.** Usually right, and usually obvious once the section
   durations are on screen. A half-explained idea costs more than a missing one.
   The Drone 60s cut dropped the entire debunk section and became Part 2.
2. **Split into parts.** A section that needs ~15s and competes with the payoff
   is a sequel, not a trim.
3. **Tighten phrase by phrase.** Cheapest per second but lowest ceiling — and
   Principle 10 phrases (subordinate clauses that eat seconds and add only
   flavour) are where to look first, since they also force a stimulus need.

## What the audit checks

`estimate.py apply` raises these automatically:

- intro over 18% of runtime
- end over 20% of runtime
- total vs target off by more than 8%, expressed in words
- any scene under 1.2s or over 6.5s
- any demo/blank scene with no explicit duration (**error**, not a warning)

Everything else — chunk count, demo placement, whether the hook is a sensation or
a claim — is your judgement, delivered as a flag with options.
