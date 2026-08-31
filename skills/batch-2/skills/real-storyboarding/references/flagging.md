# What to flag, while you draft

There is no pre-draft interview. You bind every component the first time
through, and the **reel-tracks page is the review surface** — a flag on a block
is a claim you are prepared to be wrong about, not a question waiting to be
asked. These categories tell you *when to flag and how*, never when to stop and
wait.

## Write every flag so a click resolves it

The rule is not "write a question the creator can answer in a sentence". It is
stronger: write a flag a **button** can answer. If resolving your uncertainty
takes more than clicking a candidate chip, picking from a dropdown or typing a
short note, you have not narrowed it down yet — go back and find the real
candidates first.

Every flag lands in the same place: `reel.json` → the beat's `flags[]`, and
`open.questions[]` for anything reel-wide. `tracks.py` computes the "needs a
decision" list live from those, so it can never go stale after a revision the
way a hand-written list does.

## The categories

**1. Ambiguous binding — two or more assets could satisfy one component.**
Bind the one you would bet on (`chosen_by: "claude"`, `confidence: "low"`) and
put every plausible runner-up in `candidates`, with the reason in
`candidates_why`. The tracks page renders them as clickable chips with
thumbnails, so correcting you is a click and the creator never has to describe
which file they meant.

**2. Nothing fits — the component asks for something the folder does not have.**
Do not force a bad fit to avoid an empty slot. Emit a **stub**: a real
placeholder file at the exact duration and resolution, with a spec saying what
must be legible and by when. A stub is visible, self-documenting, and drops out
of the timeline the moment the real render lands on the same filename. An empty
layer is not an option — a layer with `asset: null` and no stub is a schema
error, and it should be.

**3. Orphan assets — a catalogued file lands nowhere.**
List it in `open.unused_assets` with the reason from the binder
(`unused_reasons`). A voice take or a reference cut being unplaced is normal
and says so; a purpose-shot clip being unplaced means either you missed a slot
or the creator changed their mind. Say which you think it is, and let them
answer with a dropdown.

**4. Built assets — the component describes something that must be MADE.**
Draft your own best spec rather than leaving it blank: what has to be legible,
and by when inside the beat ("3.4s · 1080×1920 · the arrow must read as
hand-drawn marker, not vector, and be readable by 0:01"). Getting it 80% right
and handing over an editable field is a far smaller ask than composing one from
nothing. `status: "placeholder"` once the grey file exists on disk.

**5. Loose language — the notebook says something you have to interpret.**
A plain-English note that means layering, an untyped `unknown` component, a
component with no obvious anchor. Interpret it, bind it, and flag *what you
interpreted*, quoting the creator's own words back. See
`references/interpretation.md`. Never fail on a loose notebook; ambiguity is
the normal condition of the input, not an error.

**6. Moment placement — where inside the beat the key thing lands.**
When the anchor word changes the meaning (which frame of a demo shows the thing,
which word a caption should hit), pick one and mark it `confidence: "low"`
rather than picking silently. A badge the creator can ignore is cheap; a wrong
placement they have to notice unaided is not.

**7. A duration nobody gave you.** A wordless beat with no `~Ns` gets
`dur_source: "assumed"` and a question. It is the one number in the whole
pipeline that is neither measured nor estimated, and it must never look like
either.

## What does not get flagged

- Anything the notebook already decided. A `~4s`, a `|` group, an explicit
  `#tag` binding — re-deciding those and badging them low-confidence is noise
  in beats that were never in question.
- A component with exactly one sensible asset. Bind it at full confidence and
  move on. A flag is a claim on the creator's attention; a claim with one
  possible answer is not one.
- A choice the creator already made. See below.

## Recording what the creator changes

Every placement the creator corrects — by clicking a candidate chip, picking
from the dropdown, or typing a note — becomes `chosen_by: "creator"` with
`confidence: "high"`, and drops its `candidates` the instant `revise.py`
applies it. That transition is what makes the second pass fast: only
`claude`-badged, low-confidence placements are still worth their attention.
Everything else is settled and stops asking to be looked at again.

**Their choices are not up for reconsideration; yours always are.** If a later
pass makes you think a creator-chosen placement is wrong, say so in
conversation — do not quietly re-bind it.

## When a correction is really a clock change

If a fix needs different words, a different length, or a different variant, that
is a notebook change, not a placement note. `revise.py` refuses those outright.
Say so plainly and offer `/real-brainstorm` — do not stretch the reel from here.
Trimming to a target is the editor's job, at the end, by hand.
