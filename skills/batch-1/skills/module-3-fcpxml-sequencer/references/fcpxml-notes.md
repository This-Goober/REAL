# FCPXML — what actually matters when you write it by hand

Working notes for the generator. Everything here is either encoded in
`scripts/fcpxml.py` or checked by `scripts/validate.py`. When Final Cut
rejects an import, start at the top of this list.

## Document shape

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.13">
  <resources> … formats, assets, effects … </resources>
  <library>
    <event name="…">
      <project name="…">
        <sequence format="r1" duration="…" tcStart="0s" tcFormat="NDF"
                  audioLayout="stereo" audioRate="48k">
          <spine> … story elements in order … </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
```

Version 1.13 is what FCP 11 writes. 1.10/1.11 import fine into 11 too, so if
1.13 ever gives trouble, dropping `FCPXML_VERSION` is a cheap thing to try.

## Final Cut DTD-validates on import

This is the single most useful fact about the format. A malformed file gets
you a dialog quoting the exact content model it expected, e.g.

> Element title content does not follow the DTD, expecting
> `(param*, text*, text-style-def*, note?, (object-tracker?, adjust-crop?,
> adjust-corners?, adjust-conform?, adjust-transform?, adjust-blend?, …),
> (audio | video | clip | title | caption | …))`

So a rejection is never a mystery — read the model in the dialog, fix the
order or the element, done. It also means **content models are ordered
sequences, not choices**: children in the wrong order are a hard rejection
even when every element is individually legal. `CHILD_RANK` in
`scripts/fcpxml.py` encodes the canonical order (params → text →
text-style-def → note → adjust-\* in their fixed order → adjust-volume →
filters → anchored items → markers) and `order_children()` applies it to the
whole tree just before rendering. `validate.py` checks the same table, so this
class of bug should never reach Final Cut again.

Confirmed against FCP 11 on 2 Aug 2026: `<title>` wants `<text>` and
`<text-style-def>` **before** its `adjust-*` elements, not after.

## The five things that break imports

1. **Wrong element type for stills.** An image must be an `<asset>` with
   `duration="0s"` whose `<format>` has **no** `frameDuration`, placed on the
   timeline as `<video>`. A movie must be an `<asset>` with a real duration
   whose `<format>` **has** a `frameDuration`, placed as `<asset-clip>`.
   Crossing these over gets you a refusal or a crash, not a warning.

2. **Times off a frame boundary.** Every `offset`, `duration`, `start` must be
   an exact integer multiple of the sequence's `frameDuration`. Write them as
   rationals (`1001/30000s`), never decimals. The generator does all its math
   in integer frames and only renders strings at the end, which is the only
   way to keep this true across an hour of timeline.

3. **Anchored offsets are in the parent's timebase.** A connected clip's
   `offset` is measured from the parent's `start` value, not from the start of
   the sequence. A title at 1.5 s into a clip whose `start="10s"` gets
   `offset="11.5s"`. This is the bug that makes everything land in roughly the
   right place but nothing land exactly right.

   `offset_child = parent.start + (t_absolute − parent.offset)`

4. **Dangling refs.** Every `ref=` must name an `id` that exists in
   `<resources>`. Exception: `<text-style ref="…">` points at a
   `<text-style-def id="…">` inside the same title, not at a resource.

5. **Bad `file://` paths.** FCP matches media by path. A path that doesn't
   exist on that Mac imports as a red Missing Media clip. Percent-encode
   spaces (`scripts/retarget.py` fixes a whole file at once).

## Element notes

**`<format>`** — a custom size like vertical 1080×1920 has no stock Apple
name; `name="FFVideoFormatRateUndefined"` plus explicit width/height is
accepted. Video formats get `colorSpace="1-1-1 (Rec. 709)"`; still-image
formats get `colorSpace="1-13-1"` and no frameDuration.

**`<asset>`** — `uid` is optional and omitted here on purpose; letting FCP
assign one avoids collisions with media already in the library. The
`<media-rep kind="original-media" src="…">` child is required.

**Lanes** — positive lanes composite above the primary storyline, negative
lanes below (that's where audio goes). Lane numbering is per-parent. A
connected clip may run longer than the clip it's anchored to; that's how a
single narration track spans a whole timeline.

**`<gap>`** and `<title>` use `start="3600s"` — FCP's convention that
generators live on an internal timeline starting one hour in. Harmless, but
it means their children's offsets are computed off 3600 s too (rule 3).

**`<title>`** uses the stock Basic Title Motion template:

```
uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti"
```

Child order inside a title matters: all `adjust-*` elements first, then
`<text>`, then `<text-style-def>`. Position comes from `<adjust-transform
position="x y"/>` rather than the Motion `<param name="Position" key="9999/…">`
form, because the transform is version-stable and the magic key paths are not.

**Transitions** sit *between* two clips in the spine and overlap both:
`offset = cut_point − duration/2`. The neighbouring clips keep their own
offsets and durations — the transition borrows handles from the source media,
which means both sides need spare media beyond the cut. The generator warns
when a handle isn't there. Duration is forced to an even frame count so the
two halves are equal. Stills have infinite handles, so image-to-image
dissolves are always safe.

**`<adjust-transform>`** — `position` is in FCP inspector units (pixels at the
sequence size, origin at centre); `scale` is `"1 1"` for 100%. Animate by
replacing the attribute with `<param name="position"><keyframeAnimation>…`.
Keyframe `time` values are in the clip's own start-based timebase, so they
begin at the clip's `start`, not at zero.

**`<adjust-blend>`** is opacity (`amount` 0–1). Fades are expressed as opacity
keyframes rather than `<fade-in>` elements — same result, fewer version
assumptions.

**`<adjust-volume>`** — constant gain is `amount="-6dB"`. Ducking is the
keyframed form, where values are plain dB numbers:

```xml
<adjust-volume>
  <param name="amount">
    <keyframeAnimation>
      <keyframe time="…" value="-18"/>
      <keyframe time="…" value="0"/>
    </keyframeAnimation>
  </param>
</adjust-volume>
```

## Confidence

Structure, times, lanes, stills-vs-clips, titles, transforms and volume are
the well-trodden parts of the format and are what the generator leans on.
Two constructs are worth watching on the first real import, because they are
the ones where sources disagree:

- the Cross Dissolve effect `uid` (`FFTransition_CrossDissolve`)
- keyframed `adjust-volume` (constant `amount="…dB"` is certain; the
  keyframed form is the less-documented path)

If either misbehaves, the fix is local: drop `transition_out` from the story,
or replace `ducking` with `volume_db`, and everything else still imports.
The fastest way to settle both permanently is to build the shape by hand in
FCP once, export FCPXML, and diff it against what the generator writes.

## Validating without Final Cut

`xmllint --noout --dtdvalid FCPXMLv1_x.dtd file.fcpxml` if a DTD is at hand —
they ship inside Final Cut Pro at
`/Applications/Final Cut Pro.app/Contents/Frameworks/Flexo.framework/Resources/`
and are mirrored in the CommandPost repo. `scripts/validate.py` covers the
semantic checks a DTD can't (frame alignment, timebase math, handles,
still-vs-clip mismatches) and runs with or without a DTD.


## 6. A '/' or newline in any name (added 2026-08-27)

Final Cut refuses the import dialog outright — "You may not use '/' or the
return key in names" — when the PROJECT name or any clip/event/title name
contains a slash or newline. It fires BEFORE media resolution, so it looks
like a corrupt file rather than a naming problem. Real case: a project named
"… (drone / aural suffering / fyi)" was rejected before a single path was
checked. Permanent fix: `fcpxml.py` sanitizes every `name` attribute in
`El.set()` (`/` -> `·`, newlines stripped), so no story.json can produce an
unimportable file. If this error appears, the file came from an old generator.
