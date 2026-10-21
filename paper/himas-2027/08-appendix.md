# Implementation of the skills

The code is public at `github.com/This-Goober/REAL` under
`skills/batch-2/skills/`: four skills, 10,508 lines of Python, standard
library plus Pillow, ffmpeg and PocketSphinx. This appendix states the
representations and rules the results depend on, as pseudo-code where a
sentence would be ambiguous.

## Division of labour

| Stage | The model | The scripts | Refuses when |
|-----------|------------------------|------------------------------|------------------------|
| brainstorm | Drafts sequence and mock components with the creator | A words-per-second ballpark, badged as such | Asked for media, ids or times |
| catalogue | Describes sampled frames; suggests uses | Probes facts; samples 16 frames per clip; groups near-duplicate takes by perceptual hash; assigns stable ids | Sameness is uncertain (asks); unknown facts stay `unresolved` |
| storyboarding | Interprets loose notes; reviews the tracks page; picks a source event from listed observations | Parse, bind, clock, place, revise, preserve, validate, render the tracks page | No notebook; unknown revision; anchor text and index disagree; unclassified text; a line that would change the clock |
| compile | Nothing | Adapt, parity, validate, align, assemble voice, report | No reel; a dropped element; a validator error; any request for a time |

: Who decides what. The model is whichever model the host runs; the structural experiments supply descriptions and word times and call none.

Handoffs: `NOTEBOOK.md` to `notebook.json` to `bindings.json` and
`clock.json` to `reel.json` to `story.json` to the timeline file. Each is
validated against a JSON schema on write and on read. The reel is the only
editorial handoff; the story is regenerated from it on every run and never
edited.

## Vocabulary

| Term | Meaning |
|-----------|------------------------------------------------------------|
| beat | One narration block with its visuals and sounds; spans first to last word, extended by holds |
| component | One annotation such as `<show image of two waves>`; typed from its first four words; id is a hash of its text; modifiers `~4s`, `!`, `?`, `#tag`; `\|` means simultaneous |
| word anchor | Token index plus its text; placements store anchors, times are derived; text and index must agree |
| clock | Word times, estimated from the syllable model or measured by forced alignment; swapping re-derives every placement without re-planning |
| layer | One visual on one lane: asset, source interval, anchor, requested duration `dur`, occupied span, style, `chosen_by`, runner-ups |
| ownership | `chosen_by: creator`, set by any revision; preserved by id across rebuilds; a conflict is asked once |
| stub | A grey placeholder file at the exact size and duration for an unbound component, so the import shows a hole, not missing media |

Revision lines, written by the tracks page on a click or typed by the
creator, one per instruction:

```
B7: L1 anchor = pressure      B7: L1 source = 12-18      B7: L1 offset = +200
B7: layer L1 = A03            B7: remove L1              B7: confirm L1
B7: stagger L1                B7: add text = "..." anchor 150
B7: <free text>               -> a note on the layer or beat
B7: duration = 6.0 | hold longer | trim 2s   -> refused: the clock is not a placement
```

## Timing

Estimated word duration is $\mathrm{speed}\,(W_0 + K_s\,\mathrm{syllables})$
with $W_0 = 0.0665$ s, $K_s = 0.1403$ s, plus a pause after punctuation
(0.111 s comma, 0.148 s dash, 0.258 s sentence, 0.332 s paragraph, 0.406 s
beat). Fitted to 486 recorded words in five sections:
3.11 words per second, worst section error 5.8%. Text durations (0.6 s plus
0.32 s per word, minimum 1.2 s) are conventions, not measurements.

```
derive(plan, words):                 # plan is fixed; only word times change
  for beat in plan:
    n0, n1 = start(first word), end(last word)
    beat.t0 = max(0, n0 - longest explicit cold open)
    leads: laid backwards from n0, one cursor per lane; flagged if they no longer fit
    holds: after n1, in written order
    inline p:    p.t0 = n0 if anchored on the first word, else cue(anchor) + offset
    post p:      p.t0 = n1 + offset
    beat.t1 = max(n1, end of holds, end of post layers)
    cued a, b consecutive by t0: if 0 < b.t0 - a.t0 < 0.3 and not b.stagger: b.t0 = a.t0
    base visual: runs to the next base or beat.t1, never under 0.4 s; explicit lengths fixed
    overlay:     t1 = min(t0 + requested, beat.t1), flagged clipped when cut
    every p:     span = t1 - t0; dur keeps the creator's explicit number
  if pause policy = hold: each base runs to 0.1 s before the next beat's first word
cue(i) = s_i + 0.4 (e_i - s_i) for word bounds s_i, e_i

swap(clock, measured):
  s_i, e_i = measured[i] where present (missing words keep estimates, warned)
  derive(plan, words)                # anchors untouched
  report per beat: estimated vs measured span; a coherent same-sign error is a clock fault
```

Measurement runs PocketSphinx forced alignment on the assembled take, with
a built-in out-of-vocabulary list for music terms and compounds spelled from
their parts; it fails rather than guess when audio and script disagree.

## Frames

```
frames(t) = round_half_even(t * (den / num))   # rate formed first; called once per boundary
duration = frames(t1) - frames(t0)             # never a separately rounded length
```

Snapping happens once, in the adapter; the story carries integer frames
and both targets write exact rationals of the frame duration. Rounding
derived seconds to milliseconds first moved 9.2498 s across a half frame;
evaluating `t * 3000 / 100` turned 8.55 s into 256.50000000000006, rounding
to 257 against the reference's 256 (failure 14).

## Binding

```
score(c, a):                          # component c, catalogued asset a
  s = 0
  for tag in c.tags: s += 6 if tag in a.tags else 2.5 if tag in a.text else 0
  for field, cap in (binds_to 4, shows 3, role 2.5, use 2):
    s += min(cap, sum(idf(w) for shared w) / 2.2)        # idf(w) = log((N+1)/(df(w)+0.5))
  if c is text and c.content in a.excerpt: s += 3
  content = s                                            # evidence about content only
  s += kind(c.type, a.kind)   # +2 same; -1.5 / -2.5 image-video; -9 incompatible
  s -= 8 if a.reference, 3 if a.unused, 20 if a.do_not_use, 4 if file missing

bind(c): rank assets by s, ties by id
  text:      own content; an asset attaches only on a verbatim match
  narration: top if s >= 2 and content >= 1, confidence low (confirmed by ear)
  else:      top if s >= 2 and content >= 2.5; high iff s >= 5, margin >= 1.5, kinds agree
             otherwise a stub and a numbered request
```

Type words (image, clip, show, caption) are stop words. Kind alone never
binds. Runner-ups and signals are kept for the tracks page.

## Preservation

```
rebuild(notebook, catalogue, old_reel):
  reel = assemble(bind(notebook, catalogue), derive(plan, words))
  for item in old_reel where chosen_by = creator:
    if item.asset exists: copy asset, anchor, dur, style, style_by, chosen_by into reel[item.id]
    else: ask once
retime(reel, words):
  creator-moved layers keep anchor and length; the rest take derive()'s times
  each beat: t1 = max(narration end, ends of holds and post layers, held pause)
apply(reel, lines):
  refuse a line that changes the clock; apply the rest; mark the item creator's; refit the beat
  report every unparsed line; exit non-zero if anything was refused or unhandled
```

A re-anchor restores `dur` when the beat has room, because `dur` is kept
apart from the span the layer last occupied (failure 13). The same inputs
compile to the same bytes.

## Compile

```
compile(reel, target):
  validate(reel): schema; anchor text equals the word at its index; a style on every
                  text layer; an asset or a stub on every other layer; audio kinds
  story = adapt(reel): snap boundaries once; resolve media facts; compute no time
  assert layers in = elements out and lanes in = clips out     # parity, or refuse
  file = target.build(story); target.validate(file) reports 0 errors or nothing is delivered
```

The FCPXML validator checks well-formedness and Apple's DTD, reference and
id integrity, every time on a whole frame, stills as `video` with zero
duration and timed media as `asset-clip`, a contiguous spine, children
inside the parent's timebase, in and out points inside the source, and
media files present. Children are emitted in the order the DTD's own error
text prescribes. Positions are converted from pixels to percent of project
height on both axes (failure 16).

## Failure modes the checks catch

Table 4 lists the failure modes the conformance checks are built to catch
and the rule that prevents each. Every one produces a valid-looking
timeline or is caught only by the compile step's refusal.

| # | Failure | Kind | Symptom | Rule |
|--|--------------------------|-----------|------------------------|----------------------------|
| 1 | Base shot cued 40% into its first word | placement | Every beat opens 3 to 4 frames late | A cue on a line's first word lands on the beat boundary |
| 2 | A timed still after a running shot taken as the next base | notebook semantics | Shot cut short, up to a third of the beat black | An image interrupting a running shot is an overlay, not a cut |
| 3 | Explicit `~1.7s` overwritten by the span the first clock allows | state | Clipped durations stay clipped after re-timing | `dur` is the creator's number; the span is recomputed per clock |
| 4 | Instructions say "measure first"; the code can only estimate, then swap | instruction-code drift | Inline versus hold decided on estimated lengths | The clock takes measured times directly; every stated rule has a regression check |
| 5 | Re-anchoring a hold leaves the beat stretched | state | Beat overlaps the next; compile refuses | The beat end is recomputed from its contents after every revision |
| 6 | Validation splits narration on whitespace, the clock with a regex | interface | A valid notebook fails validation | One shared tokeniser |
| 7 | A visual description ending in "." typed as narration | type inference | Descriptions counted as speech, 2.0 s on a 60 s example | Type from the first four words; a component is never speech |
| 8 | The aligner writes `s`/`e`; the clock reads `start`/`end` | interface | The measured path cannot consume the aligner's output | A schema on the measured handoff; the reader accepts both spellings |
| 9 | Technical compounds absent from the aligner's dictionary | algorithm | Alignment refuses technical vocabulary | Compounds pronounced from their parts; a built-in out-of-vocabulary list |
| 10 | Prose before the first heading becomes an empty beat | representation | Zero-length beat; compile refuses | Leading prose is a note, not a beat |
| 11 | Silence between lines is always a black gap | representation | 209 of 900 frames black against an editor's cut | The `hold` pause policy |
| 12 | A held shot outlasts its clip | representation | A one-frame alignment difference makes compile refuse | The cut moves to where the footage ends, flagged; a clip shorter than its line is refused |
| 13 | Re-anchoring a clipped cue keeps the clipped length | state | Requested duration lost after a move | `dur` kept apart from the occupied span |
| 14 | Half-frame rounding, 8.55 s to 256.50000000000006 frames | arithmetic | One-frame errors on exact half frames | Rate formed first; one snap per boundary |
| 15 | Style ownership relabelled as model-selected on rebuild | state | Values survive, provenance lost | `style_by` on the preservation list |
| 16 | Positions written in pixels; Final Cut expects percent of height | target | Overlays off-position while exporter and reader agree | Conversion at the target |

: Failure modes and the rule that prevents each. The assembly benchmark catches 1 to 5 and 13, the narrated reconstruction 7 to 12, the retiming check 14 and 15, the shipped example 6, and an editor import 16.

Three rules generalise the table. A skill is two artifacts, instructions
and scripts, so every rule stated in an instruction file has a regression
check. Handoffs drift without types, so every handoff has a schema and the
skills share one core module. Where a fixed rule would stand in for
something the format cannot say, the notebook gets the word for it, and
what remains is a declared convention.

## Tests

A 40-check end-to-end suite runs the scripts on synthetic data, one check
per stated rule (35 rules), and 38 unit tests with 48 subtests cover timing
precision, layout, geometry, titles, style ownership and grounding. All
pass.

## Second target

The sequencing logic never learns an output format: the adapter produces
the story, and a target is a module with `build` and `validate`. Two
targets exist. FCPXML is the primary. OpenTimelineIO, which DaVinci Resolve
and Premiere Pro import natively, is mapped element for element (beats to
the first video track, overlay lanes to further tracks, four audio lanes to
four tracks). It has no title schema, so text
travels as a generator clip with its parameters or, for editors without a
title importer, as a transparent PNG drawn at sequence size and calibrated
to Final Cut's template (1.78 em per nominal em in a 1080 by 1920 project,
block 0.2 em below the glyph centre; 1.73 measured on an export). All 130
benchmark projects read back equivalent through the two independent
readers. The Paganini tutorial imported into both editors renders to 2,747
frames in each, all 6 cuts and 22 caption edges on the expected frame,
glyph boxes within 1%, median SSIM 0.992 between renders, audio lag 0 ms;
a semi-transparent still is 22% darker in Resolve, a renderer property.
One tutorial in two editors, not systematic compatibility evidence.
