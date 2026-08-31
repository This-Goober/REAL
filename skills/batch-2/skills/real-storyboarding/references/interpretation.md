# Reading a loose notebook

The notebook is written by a person in a text editor, at speed, with no tooling
and no syntax to learn. It is **meant** to be loose. Interpreting it is this
skill's work — not an error condition, not something to push back on. The only
unforgivable moves are refusing to read it, and interpreting it silently.

The order of operations is always: **interpret → place → show what you did →
let them correct it.** Never: ask → wait → place.

---

## 1. Type inference, and where it goes wrong

`notebook.py` types a component from its **first four words**, so a narration
line containing "sound" or "play" is not mistaken for audio. Everything below
is a real edge case, in decreasing order of how often it bites.

| The line | Typed | What to do |
|---|---|---|
| `<the thing from before>` | `unknown` | A warning is emitted. Bind it as a visual with low confidence if the neighbouring beat makes it obvious; otherwise stub it and quote the line back. Never drop it. |
| `<play the demo again>` | `audio` (from "play") | Almost always means the video. If a video asset scores far higher than any audio, bind that and flag `unknown-type`. |
| `<cut to black>` | `video` | A deliberate blank. Give it a reason in the beat's note or it is a defect, not a blank. |
| `<caption: it's not pressure>` | `text` | `content` strips the `caption:` prefix. The text is the content — it never needs an asset and never becomes a stub. |
| `<show the ratio panel for the fifth>` | `image` | "show" wins. If the catalogue's matching asset is a video, bind it anyway and flag `aspect`/kind mismatch rather than stubbing something that exists. |
| A bare fragment of five or more words with no verb | `narration` | This is the fallback and it is usually right. If it lands in the narration lane and reads like a stage direction, re-type it as a visual and flag that you did. |

An `unknown` in the reel is a **question with a placeholder attached**, never a
gap. It gets a stub, a spec, and a numbered request.

## 2. `|` versus prose parallelism

`|` inside one `<...>` is unambiguous: those components are simultaneous, and
they stack **as written, bottom first**. `audio` and `narration` sit in their
own lanes and their position in the group carries no z-order.

Two adjacent `<...>` are **sequential**. Only `|` means parallel — in the
parser.

But the format explicitly says the sentence is never wrong. A cell note saying
*"show the text and the image at the same time"*, *"this runs under the whole
thing"*, *"keep the diagram up while I talk"* means exactly what it says, and
`notebook.py` raises a warning when it spots that language in a note. When you
see one:

1. Read the note against that cell's components and decide what it licenses.
2. Apply it — merge the groups by giving the later layer the earlier one's
   anchor word, or extend a layer's span across the beat.
3. **Say what you did, in the creator's own words**: *"'show them at the same
   time' — I put the caption on the same frame as the diagram in B4."*
4. Flag it so it appears in the tracks page and can be undone in one click.

What a plain-English note licenses:

| The note says | You may | You may not |
|---|---|---|
| "at the same time", "over the top", "while I talk" | merge two adjacent groups into one simultaneous group | reorder beats |
| "under the whole thing", "throughout" | make an audio component a `connected` span across the reel | add audio nobody mentioned |
| "slow this down", "let this breathe" | prefer fewer, longer layers in that beat; hold the base longer | change the narration, or add seconds to the clock |
| "fast cuts here", "densest beat" | spread the beat's layers across more anchor words | invent extra components to cut to |
| "don't talk over this" | make a demo a hold that runs after the words stop | mute or trim the narration |
| "text stays on a beat after the line" | extend that text layer to the end of the beat | extend the beat itself |

The line that separates them: **you may re-read the components that exist; you
may not invent components or move time.** New content is `/real-brainstorm`.
Time is the clock's.

## 3. Placing a component on a word

Everything anchors to a word index. Seconds are a cache.

- **Cuts land ~40% into the anchor word, not on its leading edge.** A cut on a
  word boundary lands on the breath before it and reads as a slide change
  rather than an edit. This is `cut_into_word` in `rates.json`.
- **Two cues within ~0.3s snap to the same frame** (the earlier one wins).
  Simultaneous pop-ins read as one event; near-simultaneous ones read as a
  mistake. If the separation is deliberate, mark the later layer `stagger` —
  `B4: stagger L2` — and it stops snapping.
- **Distribution inside a beat.** With one visual group, it lands on the beat's
  first word — it illustrates the line, so it accompanies the line. With *k*
  groups, group *i* anchors at `w0 + floor(i·L/k)`: evenly spread across the
  words of that line, in written order. Written order is never reshuffled.
- **If there is no good anchor** — a wordless demo, a title card, a beat whose
  narration has already ended — place it at the start of the beat (or, for
  anything written after a hold, at the start of the hold) and **say so**. Do
  not invent a word to anchor to, and never anchor into a neighbouring beat.
- **Explicit durations never move.** A `~4s` is the creator's number. If it
  doesn't fit where it lands, the layer becomes a hold that runs after the
  narration; the duration is not shortened to fit the line.

## 4. Lead-ins, inline layers and holds

Three placements, decided once, on the estimated clock, and never re-decided
when the measured clock arrives:

- **lead** — written before the first narration in its cell. With an explicit
  duration it is a **cold open**: it consumes real time before the first word,
  running backwards from that word so its `~2s` stays 2s. Without a duration it
  simply starts at the top of the beat and holds into the line.
- **inline** — it fits inside the narration, so it anchors to a word.
- **hold** — its explicit duration would run past the last word, so it plays
  *after* the words stop. This is what a demo that must not be talked over
  actually needs, and it is why beat length is not the same as narration length.
- **post** — written after a hold, so it rides the hold (the two captions
  labelling the two strokes of a demo), spread across the hold's length rather
  than jumping back over narration that has already finished.

## 5. Order inside a parallel group

Stacking is as written, bottom first, and that is the whole rule. In practice
a creator writes the backdrop first and the thing on top of it last, which is
why the rule works. Two consequences worth knowing:

- The **first visual in a group is the base** (`fit: "fill"`); later visuals in
  the same group are overlays (`fit: "fit"`). Successive base visuals form the
  primary storyline and each holds until the next one starts.
- A caption written *before* an image in the same group will sit under it. That
  is what the notebook said, so do it — but flag it, because it is more often a
  typo than an intention.

Audio and narration have no z-order, so their position in a group means
nothing — but their *presence* in it means a great deal:

> **An audio component parallel to a video component that names the same thing
> is that clip's own sound, not a second asset.**

`<video clip of the two strokes ~7s | audio of the raw take at full volume>` is
one file heard twice over, not a clip plus a separate recording. Bind the audio
lane to the same asset as the video and type it **`source`** — never `bed`.
That distinction is load-bearing downstream: a bed is music or ambience laid
under the narration and ducks (default `-12`); a `source` lane defaults to
`duck_db: 0`, because a demo's own sound is the argument the reel is making and
ducking it under the voice destroys the thing the shot exists to show. Typing it
`bed` is a bug, not a taste call.

Stubbing that sound is the other failure mode: it asks the creator to go and
record something that already exists inside a file they handed you.

## 6. Variants

Cells sharing a name where at least two carry `(variant X)` labels are a fork.
The first is selected; the rest travel as `alternates` — narration, component
count, and their own estimated length — and appear in the tracks page as
switchable.

**Switching a variant changes which words are spoken, so it changes the clock.**
It is a re-run (`clock.py time … --variant hook=B`), not a revision.
`revise.py` refuses it and says so.

## 7. Things that are always defects, however loose the notebook is

- A beat with nothing on screen and no reason attached. A blank is deliberate
  or it is a defect; either way it needs a sentence.
- A layer with `asset: null` and no stub.
- A duration presented as estimated when it was assumed, or as measured when it
  was estimated.
- A creator's `~4s`, `!`, `?` or `#tag` quietly overridden. `!` survives cuts,
  `?` means they want options, `#tag` is them pointing at a file. All four are
  instructions, not hints.
