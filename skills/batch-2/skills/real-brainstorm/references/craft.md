# Craft: writing components that are worth writing

The notebook format (`notebook-format.md`) tells you what a component *is*. This
tells you what makes one good. Everything here serves one test:

> **Can the creator act on this line without asking you a follow-up question?**

If the answer is no, the component is decoration.

---

## 1. The triple-purpose rule

Every component is read three times by three different readers:

1. **The creator**, deciding whether this beat works at all.
2. **An image/video generator**, taking the text as a prompt.
3. **A human on shoot day**, holding a camera or opening a plotting script.

One sentence has to serve all three. That is not as hard as it sounds — the
three readers want the same thing, which is *concrete visual detail*. The
generator wants subject, composition, background, mood. The shooter wants
framing, action, and what has to be visible. Those overlap almost entirely.

The parts that make a line survive all three readings:

| Part | Question it answers | Example fragment |
|---|---|---|
| **Subject** | what is in frame | `two sine waves` |
| **State / action** | what it is doing | `drifting out of phase` |
| **Composition** | how it is framed | `dark background, waves filling the lower third` |
| **The point** | what must be legible | `the gap between them clearly visible` |

The last one is the one people skip and the one that matters most. It is what
lets a shooter know when they have the take, and what stops a generator from
producing a beautiful image that misses the idea.

```
DEAD    <show image of a violin>
ALIVE   <show image of a violin resting on sheet music, warm window light from
         the left, close on the bridge and strings, shallow depth>

DEAD    <video clip of me playing>
ALIVE   <video clip of me playing a slow shift on the G string, phone on a
         stand at bow height, drone audible in the room — the wobble has to be
         hearable by 2s in ~4s !>
```

### Write for the cheapest path, not the most expensive one

You do not know yet whether this gets shot, found, or generated. Write it so any
of the three works. If one path is obviously cheaper, you may say so in the
cell's prose note ("this one is probably a screenshot, not a shoot"), but keep
the component itself path-agnostic.

### Say what must be visible, not what it should feel like

"Dramatic", "beautiful", "engaging" are unactionable. "Backlit", "hands only",
"the two lines visibly diverging by the end" are actionable. Feeling is a
consequence of the concrete choices; name the choices.

---

## 2. Showing vs saying

Every idea in a script goes one of three ways. Choosing wrong is the most common
way a reel goes flat.

- **Say it** (narration only) — abstractions, causality, the "why". Some
  sentences genuinely have no picture; forcing one produces a stock-photo
  non-sequitur.
- **Show it** (image/video, no narration) — anything the eye gets faster than
  the ear. Comparisons, before/after, physical technique, anything with a shape.
- **Show it and say something else** — the strongest move available. Narration
  carries the reasoning while the visual carries the evidence. Used well this is
  what makes a 60s reel feel dense rather than rushed.

Rules of thumb that hold up:

- **If you can demonstrate it, don't describe it.** A 3s clip of the wobble
  beats 12 words about wobble, and costs a quarter of the runtime.
- **Don't illustrate the noun, illustrate the idea.** The word "practice" does
  not need a picture of practice. The *claim* being made about practice does.
- **A caption is for the phrase you want remembered**, not a transcript. One or
  two words, on the beat, and then gone. Captioning the whole narration is a
  platform accessibility feature, not a component decision — it does not belong
  in the notebook.
- **Silence and a held frame are real choices.** A beat with one image and no
  narration reads as deliberate if it is short and lands after tension. Say in
  the cell note that you meant it.

---

## 3. Layering patterns that read as intentional

`|` inside one `<...>` means simultaneous. Stacking is bottom-first, as written.
`audio` and `narration` have their own lanes and carry no z-order.

Patterns worth reaching for:

**Text over a held image** — the image gives the idea a place to sit; the words
name it. Works when the caption is short and the image is still enough to read
against.
```
<show image of two waveforms stacked, the upper one visibly ragged | caption: dissonant>
```

**B-roll under narration** — motion under an explanation keeps the eye busy
while the ear does the work. The footage must not compete: no sync sound, no
text, nothing that demands to be read.
```
<video clip of hands moving through a slow scale, mid-shot, no face #practice-broll>
```

**Demo audio ducking narration** — when a demo has to be *heard*, the narration
stops and the demo goes full. Do not talk over the thing you are proving. Note
it in the cell prose ("let the demo run clean here") — storyboarding sets the
actual duck.
```
<video clip of the interval played twice, in tune then flat ~5s ! | audio of the drone under it>
```

**Reveal in two components** — establish, then add. Two sequential components
beat one busy image, because the second one lands as a change.
```
<show image of two sine waves overlapping, clean>
<show image of the same two waves with a third, jagged wave underneath — same framing, same colours>
```
Say "same framing, same colours" explicitly. That one phrase turns two separate
jobs into one, whether it is shot or generated.

**Cut on the idea, not the sentence.** A visual change that lands mid-sentence
feels like the video is thinking; one that lands on every full stop feels like a
slideshow. Place the component where the idea turns.

---

## 4. How many components a stretch wants

Starting convention: **roughly one visual per ~3 seconds of narration** — call
it one per 9–10 words. It is a smell test for dead stretches, not a quota.

- **Under it** (a long stretch with one visual) — fine if the visual is *doing*
  something (motion, a slow reveal, a demo). Dead if it is a static image
  sitting under 20 seconds of talking. That is where viewers leave.
- **Over it** (a visual every few words) — fine at a hook or a montage, where
  speed is the effect. Exhausting for a whole reel, and it makes the demo — the
  one thing that needed room — feel like just another cut.
- **Vary it deliberately.** Dense hook, breathing explanation, one long clean
  demo, tight payoff. Even density is the flattest thing a reel can have.

Count with `scripts/ballpark.py`; it prints components per cell alongside the
word count, which is how you spot the dead stretch.

---

## 5. When a beat should be a variant

Variant a beat when **the choice is real** — two takes that would produce
measurably different reels, and you genuinely cannot tell which is better
without the creator.

Almost always worth varianting:

- **The hook.** The one beat where the whole thing is won or lost, and where
  taste is unpredictable. A question-hook and a demo-hook are different videos.

Sometimes:

- **The ending** — call to action vs a landing line vs a callback to the hook.
- **A structural fork** — demo first then explain, or explain then demo. If you
  variant this, the variants must actually contain the reordered beats, not a
  note saying "or do it the other way".

Never:

- A beat where you are choosing between two adjectives.
- A beat where one option is plainly better — pick it and move on.
- Every beat. Variants cost the creator attention linearly and stop being read
  after about the third one.

**Test for a real variant:** state each in one sentence. If the two sentences
sound the same, you have one beat, not two.

```markdown
## hook (variant A)
Cold open on the sound — no setup, let them hear the problem first.
<audio of a slow beating minor second, three seconds, no narration>
<caption: what is that?>

## hook (variant B)
Question first, sound second — safer, more explainer-shaped.
<Why do some pairs of notes sound like they're arguing?>
<show image of two waveforms colliding, hard black background>
```

Those are different videos. That is the bar.

---

## 6. Modifiers, used sparingly

- `!` — essential. Reserve it for the beats the reel is *about*, usually the
  demo. If half the notebook is `!`, none of it is.
- `?` — unsure. Use it honestly. It is a request for options at storyboarding,
  and it is much better than a confident bad guess.
- `~4s` — only when the creator asked for a duration, or when the content
  dictates one (a demo that needs time to be audible). Never as a general
  timing estimate; that is not this skill's job.
- `#tag` — a binding hint for the catalogue. Use consistent tags across the
  notebook (`#practice-broll`, `#drone-demo`) so a whole class of footage binds
  together later.
