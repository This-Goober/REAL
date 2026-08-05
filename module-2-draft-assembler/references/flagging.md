# What to flag, while you draft

There is no pre-draft interview. You place something in every slot the first
time through, and the draft itself is the review surface — a flag on a slide
is a claim you're prepared to be wrong about, not a question waiting to be
asked. These categories tell you *when to flag and how*, not when to stop and
wait.

## Write every flag so a click resolves it

The old version of this document told you to write questions the director
could answer in a sentence. The rule is stronger now: write flags a
**button** can answer. If resolving your uncertainty takes more than a click
or a dropdown selection, that's a sign you haven't actually narrowed it down
— go back and find the real candidates first.

## The categories

**1. Ambiguous slots — two or more files could fill one scene.**
Pick the one you'd bet on as the primary placement (`chosen_by: "claude"`,
`confidence: "low"`), and list every plausible runner-up in that layer's
`candidates` array (schema: `references/draft-schema.md`). The storyboard
renders them as real thumbnails the director clicks to swap — they never
have to describe which file they mean.

**2. Empty slots — the plan asks for media and nothing in the folder fits.**
Leave the slot without a lane-0 layer rather than forcing a bad fit. The
storyboard renders a dropdown of every unplaced file for that scene
automatically — you don't need to enumerate candidates by hand the way you do
for an ambiguous slot, since "nothing obviously fits" means the honest answer
is "let them see everything left." If literally nothing in the folder could
ever work — the plan wants a shot that was never gathered — write it as a
MAKE stub instead (category 4) so it isn't silently invisible.

**3. Orphan files — media the director gathered that lands in no scene.**
List them; the storyboard's "placed nowhere" panel gives each one a
scene-picker dropdown right there. Don't guess a home for a file you're not
confident about — an orphan with an honest "unplaced" badge is more useful
than a wrong placement that now looks confirmed.

**4. MAKE items — the scene needs an asset that has to be built.**
Draft your own best specification — what must be legible, and by when inside
the scene — rather than leaving the stub blank. Getting it 80% right and
handing the director an editable text field beats an empty spec field,
because editing existing words is a much smaller ask than composing new
ones. Mark `status: "todo"`.

**5. Abstract media ideas — the plan says something you'd have to invent.**
Same move as category 4: pick the most concrete reading of the type Module 1
proposed and draft it as a MAKE stub with your best spec, rather than leaving
a gap. The director edits the spec text if you read it wrong.

**6. Moment placement — where inside the scene the key thing lands.**
When the plan didn't already say and it changes the media choice (which
frame of a demo shows the beating most clearly, which word a punch-in should
peak on), pick a candidate and mark it `confidence: "low"` rather than
picking arbitrarily and hiding the uncertainty. Never invent false confidence
— a badge the director can ignore is cheap; a wrong placement they have to
notice on their own is not.

## What doesn't get flagged

- Anything the plan already decided. Re-deciding it and marking it low
  confidence just adds noise to scenes that were never in question.
- A slot with exactly one sensible candidate. Place it at full confidence and
  move on — a flag is a claim on the director's attention, and a claim with
  only one possible answer isn't one.
- Style questions a project style guide already settles, if the project keeps
  one.

## Recording what the director changes

Every layer the director corrects — by clicking a candidate chip, picking
from a dropdown, or typing a note — becomes `chosen_by: "director"` and
drops its `confidence` and `candidates` the moment `revise.py` applies the
change. That transition is what makes a second pass over the storyboard
fast: only the `claude`-badged, low-confidence layers are still worth the
director's attention: the rest is settled and stops asking to be looked at
again.

If a correction turns out to conflict with the plan's timing — the director
wants an image that needs four seconds in a two-second scene — that is a
Module 1 change. `revise.py` refuses duration edits outright; say so and ask
whether they want to go back, rather than stretching the scene from here.
