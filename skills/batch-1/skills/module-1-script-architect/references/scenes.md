# Scenes — the grammar

A **scene** is one visual state of the video: everything on screen at once, held
as a unit. A **scene change** is the screen resetting, like advancing a slide.
(Vocabulary from `claude/editing-principles.md` — use his words, not synonyms.)

A scene is the unit [director] vetoes independently. Not every frame; not a whole
paragraph. If he would never say "change just that," it is not its own scene.

## Duration windows

| | |
|---|---|
| **floor** | 1.2s — under this the screen flickers rather than shows |
| **comfortable** | 2.0–5.0s — where most scenes should land |
| **ceiling** | 6.5s — over this the screen goes stale and the eye leaves |

Both bounds are enforced by the audit. A scene over the ceiling has three fixes,
in order of preference: **split it**, **add a reveal** (a second stimulus appears
mid-scene, so the state changes without the slate clearing), or **punch in**. A
scene under the floor almost always wants merging into its neighbour.

A 2-minute video lands around 25–40 scenes. Far fewer means the screen is static;
far more means you are cutting on nothing.

## Where boundaries go

In descending priority:

1. **Explicit cues in the script.** A `[img: …]` or `[text: …]` bracket is [director]
   already deciding. Honour it.
2. **Sentence starts.** The default, and usually right.
3. **Clause boundaries** — after a comma, at a conjunction, before a "but" or a
   "however". Use these to split a sentence that would otherwise blow the ceiling.
4. **The word that names the thing.** When narration says the noun the image
   shows, the image should land there, not a beat early.

Never split mid-clause just to hit a duration. If a 9-second sentence has no
internal seam, it wants a reveal, not a cut.

**Every scene needs a reason the screen changed.** If you cannot say what is new
in one clause, the previous scene should have continued. Write that reason into
the `visual` field — it is what [director] reads.

## Treatments

The vocabulary for *how* a scene arrives. Use these words exactly:

| Treatment | What it means |
|---|---|
| `cut` | hard change; the default |
| `cut (mid-word)` | b-roll switch landing ~40% into a word, never on a breath (Principle 3) |
| `reveal` | a stimulus appears mid-scene — pop-in, wipe, fade — the slate does not clear |
| `punch-in` | scaling into the current frame for emphasis |
| `hold` | the previous stimulus stays up (screen-hold), covering a gap |
| `stagger` | two cues deliberately not simultaneous, overriding the 0.3s snap (Principle 7) |
| `element continuity` | something on screen moves into its new position rather than being replaced — the strongest tool for showing that two things are related |

Cues resolving within ~0.3s snap to the same frame unless marked `stagger`
(Principle 7). If you want two things to land separately, say so.

## Blanks

A **blank** is deliberate black with no stimulus, chosen for a conceptual reason —
a tone shift, a debunk setup, a beat before a demo. **Dead time** is screen time
that carries nothing and was not meant to; that is a defect.

- A blank is never longer than one content segment (Principle 1).
- Max 1–2 blanks per video; over budget the plan halts and asks (Principle 8).
- A sub-second breath of black (~0.3s) before a reveal is good rhythm, not a
  blank against the budget (Principle 9).
- Blanks carry **explicit** durations. Never estimated.
- Fill imagery must be *relevant to what is being said*. Covering a gap with a
  leftover neighbouring image that does not match the words is worse than the
  blank (Principle 10).

## Layers

A scene can stack: background, b-roll underlay, overlay image, text, captions.
List them in `layers` in the order they sit, bottom first. Two images side by side
is one scene with two layers, not two scenes.

## Recurring shapes worth reaching for

- **Matched sets.** Images sharing styling (the three ratio panels) are a
  ready-made multi-beat sequence — same position, panel swaps, one beat each.
  Spotting a matched set is worth more than describing its members individually.
- **Callback.** Re-showing an earlier stimulus at the moment the argument returns
  to it. Cheap, and it makes the video feel constructed rather than listed.
- **Staged reveal.** One diagram revealed in parts across several scenes, so the
  picture builds with the sentence instead of arriving complete and being read
  ahead of the narration.
- **A/B pair.** Two scenes, identical framing, one variable. The comparison
  happens in the audience rather than in your description of it.
