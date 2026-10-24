#!/usr/bin/env python3
"""The `otio` target — OpenTimelineIO (.otio), the pipeline's second export format.

DaVinci Resolve (18.5 and later, including the free edition) and Premiere Pro
(25.6 and later) import .otio timelines natively; many other tools read it
through the OpenTimelineIO adapters. This target exists so the same
`story.json` can be checked in a second editor that shares no code with Final
Cut, and so the two exports can be compared mechanically
(`bench/otio_edl.py --against timeline.fcpxml`).

Mapping, chosen to mirror the FCPXML target element for element:

    story beats, in order        -> video track V1 (a `gap` beat is an OTIO Gap)
    overlay on lane n (n >= 1)   -> video track V{n+1}; Gaps fill the space between
    connected clip on lane -n    -> audio track A{n} (A1 narration, A2 source,
                                    A3 bed, A4 sfx — adapt.py's fixed lanes)
    text overlay                 -> Clip whose media is a GeneratorReference of
                                    kind "REAL.title": OTIO has no title schema,
                                    so the words, font, size, colour, alignment
                                    and pixel position travel as generator
                                    parameters and the timing is a real clip
                                    (titles="native", the default). With
                                    titles="raster" the same text is drawn to a
                                    transparent PNG at the sequence size and the
                                    clip references that file, so an editor with
                                    no title importer (DaVinci Resolve) shows it;
                                    the parameters stay in metadata["REAL"]["title"]
    note, markers                -> clip metadata["REAL"]["note"], OTIO Markers
    transform, opacity, fades,
    volume, ducking, transitions -> metadata["REAL"] (NOT interpreted by OTIO
                                    readers; reported as one warning per build)

Every time is an integer number of frames at the sequence rate, expressed as
RationalTime(frames, rate). Nothing is rounded here: story.json is already
frame-exact and the FCPXML target does its arithmetic the same way, so a
placement lands on the same frame in both files or the cross-check says so.

Media facts (duration, size, file URL) come from the same resolver the FCPXML
target uses (fcpxml.Story._resolve_media), so a probe-or-declared duration can
not differ between the two exports. Paths written into the file are the
target machine's (`assets_root`), as absolute file URLs.
"""

import json
import os
import sys
from urllib.parse import unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import opentimelineio as otio  # noqa: E402  — missing library => target UNAVAILABLE
from opentimelineio import opentime  # noqa: E402

import fcpxml  # noqa: E402
from real_core import FRAME_DURATIONS  # noqa: E402

from . import BuildResult, ValidateResult  # noqa: E402
from . import title_raster  # noqa: E402

GENERATOR_KIND = "REAL.title"
TITLE_MODES = ("native", "raster")
META = "REAL"
# Story fields OTIO cannot express. They are copied into metadata so nothing is
# lost, and the build says once that the importing editor will not apply them.
PASSTHROUGH = ("transform", "kenburns", "opacity", "fade_in", "fade_out",
               "volume_db", "ducking", "volume_keyframes", "video_role")
TEXT_FIELDS = ("font", "font_size", "font_face", "color", "align", "position",
               "stroke_color", "stroke_width", "shadow", "shadow_color",
               "shadow_offset", "shadow_blur", "line_spacing", "face", "style",
               "glow", "wrap_width")
TEXT_DEFAULTS = {"font": "Helvetica Neue", "font_size": 40, "font_face": "Bold",
                 "color": [1, 1, 1, 1], "align": "center"}


class OTIOBuildError(Exception):
    pass


def rate_of(fps_key):
    num, den = FRAME_DURATIONS[fps_key]
    return den / num


def _plain(v):
    """JSON-safe copy for OTIO metadata (tuples -> lists)."""
    return json.loads(json.dumps(v))


class OTIOTarget:
    name = "otio"
    extension = ".otio"
    description = ("OpenTimelineIO timeline (.otio) — DaVinci Resolve: File > "
                   "Import > Timeline…; Premiere Pro 25.6+: File > Import")

    # ---- build -----------------------------------------------------------

    def build(self, story, out_path, base_dir=".", probe=True,
              titles="native", titles_dir=None):
        if titles not in TITLE_MODES:
            raise OTIOBuildError("titles must be one of %s, not %r"
                                 % ("/".join(TITLE_MODES), titles))
        self._titles = titles
        # rendered captions sit next to the timeline: <out>-titles/<slug>-<hash>.png
        self._titles_dir = (os.path.abspath(titles_dir) if titles_dir else
                            os.path.splitext(os.path.abspath(out_path))[0] + "-titles")
        self._rendered = []
        S = fcpxml.Story(story, base_dir=base_dir, do_probe=probe)
        F = S.clock
        rate = rate_of(F.key)
        warnings = []
        tally = {}

        def RT(f):
            return opentime.RationalTime(int(f), rate)

        def TR(f0, df):
            return opentime.TimeRange(RT(f0), RT(df))

        beats = story.get("beats") or story.get("timeline") or []
        if not beats:
            raise OTIOBuildError("story has no 'beats'")

        # 1. primary storyline, laid out sequentially — same arithmetic as
        #    fcpxml.Story.build so both files agree on every boundary.
        cursor, placed = 0, []
        for i, beat in enumerate(beats):
            if beat.get("offset") is not None:
                cursor = F.frames(beat["offset"])
            dur = beat.get("duration")
            if dur is None:
                if beat.get("type") == "video" or (
                        beat.get("src") and fcpxml.guess_kind(beat["src"]) == "video"):
                    m = S._resolve_media(beat["src"], None, beat.get("asset_duration"))
                    dur_f = m["asset_frames"] - F.frames(beat.get("start", 0))
                else:
                    raise OTIOBuildError("beat %d needs a 'duration'" % (i + 1))
            else:
                dur_f = F.frames(dur)
            if dur_f <= 0:
                raise OTIOBuildError("beat %d has a non-positive duration" % (i + 1))
            placed.append((beat, cursor, dur_f))
            cursor += dur_f
        total_f = cursor

        # 2. everything that is not on the storyline, keyed by lane
        lanes = {}
        for beat, off_f, dur_f in placed:
            for ov in beat.get("overlays") or []:
                ov_off = off_f + F.frames(ov.get("offset", 0))
                ov_dur = ov.get("duration")
                ov_dur_f = (F.frames(ov_dur) if ov_dur is not None
                            else dur_f - (ov_off - off_f))
                if ov_dur_f <= 0:
                    raise OTIOBuildError(
                        "overlay on beat at frame %d has a non-positive duration" % off_f)
                lanes.setdefault(int(ov.get("lane", 1)), []).append((ov_off, ov_dur_f, ov))
        for g in (story.get("connected") or []) + (story.get("audio") or []):
            g_off = F.frames(g.get("offset", 0))
            g_dur = g.get("duration")
            if g_dur is None:
                m = S._resolve_media(g["src"], g.get("type"), g.get("asset_duration"))
                g_dur_f = m["asset_frames"] - F.frames(g.get("start", 0))
            else:
                g_dur_f = F.frames(g_dur)
            if g_dur_f <= 0:
                raise OTIOBuildError("connected clip %s has a non-positive duration"
                                     % g.get("src", g.get("text", "?")))
            lanes.setdefault(int(g.get("lane", -1)), []).append((g_off, g_dur_f, g))
            if g_off + g_dur_f > total_f:
                warnings.append(
                    "connected clip %s runs %.2fs past the end of the visual timeline"
                    % (g.get("src", g.get("text", "?")),
                       F.seconds(g_off + g_dur_f - total_f)))

        # 3. tracks
        def fill(track, items, lane):
            at = 0
            for abs_f, d_f, spec in sorted(items, key=lambda x: (x[0], x[1])):
                if abs_f < at:
                    raise OTIOBuildError(
                        "two placements overlap on lane %d at frame %d (%s); the "
                        "FCPXML export would stack them on one lane too — give "
                        "them different lanes in the reel" % (lane, abs_f, spec.get(
                            "src", spec.get("text", "?"))))
                if abs_f > at:
                    track.append(otio.schema.Gap(source_range=TR(0, abs_f - at)))
                track.append(self._item(S, spec, d_f, RT, TR, warnings, tally))
                at = abs_f + d_f
            # Pad to the storyline's length so every track reports the same
            # duration: OTIO allows ragged tracks, but otiostat flags them and
            # some importers pad or truncate silently.
            if at < total_f:
                track.append(otio.schema.Gap(source_range=TR(0, total_f - at)))

        tracks = []
        v1 = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
        n_transitions = 0
        for i, (beat, off_f, dur_f) in enumerate(placed):
            v1.append(self._item(S, beat, dur_f, RT, TR, warnings, tally))
            tr = beat.get("transition_out") or (
                placed[i + 1][0].get("transition_in") if i + 1 < len(placed) else None)
            if tr and i + 1 < len(placed):
                v1.append(self._transition(S, tr, placed[i], placed[i + 1],
                                           off_f + dur_f, RT, warnings))
                n_transitions += 1
        tracks.append(v1)
        for lane in sorted(l for l in lanes if l > 0):
            tr = otio.schema.Track(name="V%d" % (lane + 1), kind=otio.schema.TrackKind.Video)
            fill(tr, lanes[lane], lane)
            tracks.append(tr)
        for lane in sorted((l for l in lanes if l < 0), reverse=True):
            tr = otio.schema.Track(name="A%d" % (-lane), kind=otio.schema.TrackKind.Audio)
            fill(tr, lanes[lane], lane)
            tracks.append(tr)

        tl = otio.schema.Timeline(name=story.get("project", "Untitled"), tracks=tracks,
                                  global_start_time=RT(0))
        tl.metadata[META] = _plain({
            "generator": "real-compile otio target",
            "event": story.get("event", "Sequenced"),
            "frame_rate": F.key, "rate": rate,
            "width": S.width, "height": S.height,
            "total_frames": total_f,
            "assets_root": S.mac_root,
            "lanes": {"V1": "primary storyline", "V2+": "overlay lanes 1+",
                      "A1": "narration", "A2": "source (a clip's own sound)",
                      "A3": "bed", "A4": "sfx"},
            "parity": story.get("_parity"),
            "titles": titles,
            "text": (("text overlays are %s generator clips: words, timing and "
                      "requested styling are in the parameters; the importing "
                      "editor shows them as generators, not as native titles"
                      % GENERATOR_KIND) if titles == "native" else
                     ("text overlays are rendered to transparent PNG stills "
                      "(metadata.REAL.kind == 'title'); the requested styling is "
                      "kept in metadata.REAL.title and the files live in %s"
                      % self._titles_dir)),
        })
        otio.adapters.write_to_file(tl, out_path)
        if titles == "raster" and titles_dir is None and os.path.isdir(self._titles_dir):
            # the default folder is ours: drop stills left by earlier builds
            keep = {os.path.basename(p) for p in self._rendered}
            for f in os.listdir(self._titles_dir):
                if f.endswith(".png") and f not in keep:
                    os.remove(os.path.join(self._titles_dir, f))

        warnings = list(S.warnings) + warnings
        if n_transitions:
            warnings.append(
                "%d transition(s) exported as OTIO SMPTE_Dissolve between V1 clips; the "
                "importing editor borrows the handles from the media" % n_transitions)
        if tally:
            warnings.append(
                "OTIO readers do not apply REAL's %s; the values travel in each "
                "clip's metadata['REAL'] and must be re-created in the editor"
                % ", ".join("%s (%d)" % (k, n) for k, n in sorted(tally.items())))
        n_text = sum(1 for t in tracks for c in t
                     if isinstance(c, otio.schema.Clip)
                     and isinstance(c.media_reference, otio.schema.GeneratorReference))
        if n_text:
            warnings.append(
                "%d text overlay(s) exported as %s generator clips — timing and "
                "words import; native title styling has to be re-applied"
                % (n_text, GENERATOR_KIND))
        if self._rendered:
            warnings.append(
                "%d text overlay(s) rendered to %d PNG still(s) under %s — they import "
                "as pictures with the requested look, not as editable titles; the "
                "styling is kept in metadata['REAL']['title']"
                % (len(self._rendered), len(set(self._rendered)), self._titles_dir))
        self.total_frames = total_f
        summary = ("%dx%d, %.2fs, %d frames @ %s fps, %d tracks"
                   % (S.width, S.height, F.seconds(total_f), total_f, F.key, len(tracks)))
        return BuildResult(out_path, warnings, summary)

    def _item(self, S, spec, dur_f, RT, TR, warnings, tally):
        F = S.clock
        kind = spec.get("type")
        if kind in (None, "auto"):
            kind = fcpxml.guess_kind(spec.get("src", "")) if spec.get("src") else "gap"
        if spec.get("text") is not None and kind != "title":
            kind = "title"

        meta = {}
        if spec.get("note"):
            meta["note"] = str(spec["note"])
        for k in PASSTHROUGH:
            if spec.get(k) is not None:
                meta[k] = _plain(spec[k])
                tally[k] = tally.get(k, 0) + 1
        if spec.get("role"):
            meta["role"] = spec["role"]
        if spec.get("src_enable"):
            meta["src_enable"] = spec["src_enable"]

        if kind == "gap":
            g = otio.schema.Gap(name=spec.get("name", "Gap"), source_range=TR(0, dur_f))
            if meta:
                g.metadata[META] = meta
            return g

        start_f = 0
        if kind == "title":
            text = str(spec.get("text", ""))
            params = dict(TEXT_DEFAULTS)
            for k in TEXT_FIELDS:
                if spec.get(k) is not None:
                    params[k] = _plain(spec[k])
            params["text"] = text
            if getattr(self, "_titles", "native") == "raster" and text.strip():
                png = title_raster.render(params, S.width, S.height, self._titles_dir,
                                          warnings=warnings)
                self._rendered.append(png)
                ref = otio.schema.ExternalReference(
                    target_url=title_raster.file_url(png), available_range=TR(0, dur_f))
                ref.metadata[META] = {"kind": "title", "rendered": "png",
                                      "width": S.width, "height": S.height,
                                      "title": params}
            else:
                ref = otio.schema.GeneratorReference(
                    name=text[:40] or "Title", generator_kind=GENERATOR_KIND,
                    available_range=TR(0, dur_f), parameters=params)
            clip = otio.schema.Clip(name=spec.get("name", text[:40] or "Title"),
                                    media_reference=ref, source_range=TR(0, dur_f))
        elif kind == "image":
            media = S._resolve_media(spec["src"], "image", None,
                                     [spec.get("width"), spec.get("height")])
            ref = otio.schema.ExternalReference(target_url=media["url"],
                                                available_range=TR(0, dur_f))
            ref.metadata[META] = {"kind": "image", "width": media["width"],
                                  "height": media["height"]}
            clip = otio.schema.Clip(name=spec.get("name", media["name"]),
                                    media_reference=ref, source_range=TR(0, dur_f))
        else:  # video or audio
            media = S._resolve_media(spec["src"], kind, spec.get("asset_duration"))
            start_f = F.frames(spec.get("start", 0))
            ref = otio.schema.ExternalReference(
                target_url=media["url"], available_range=TR(0, media["asset_frames"]))
            ref.metadata[META] = {"kind": kind, "width": media["width"],
                                  "height": media["height"],
                                  "has_audio": bool(media["has_audio"]),
                                  "asset_seconds": media["asset_seconds"]}
            clip = otio.schema.Clip(name=spec.get("name", media["name"]),
                                    media_reference=ref, source_range=TR(start_f, dur_f))
            if media["asset_frames"] and start_f + dur_f > media["asset_frames"]:
                warnings.append(
                    "%s: asks for %.2fs from %.2fs but the file is only %.2fs long"
                    % (spec.get("src"), F.seconds(dur_f), F.seconds(start_f),
                       F.seconds(media["asset_frames"])))

        for mk in spec.get("markers") or []:
            m_f = start_f + F.frames(mk.get("t", 0))
            d_f = max(1, F.frames(mk.get("duration", 0)))
            clip.markers.append(otio.schema.Marker(
                name=str(mk.get("value", "marker")), marked_range=TR(m_f, d_f),
                color=otio.schema.MarkerColor.GREEN))
        if meta:
            clip.metadata[META] = meta
        return clip

    def _transition(self, S, tr, left, right, boundary_f, RT, warnings):
        """A dissolve between two V1 clips, centred on the cut: the same even frame
        count and the same handle check as the FCPXML target."""
        F = S.clock
        d_f = F.frames(tr.get("duration", 0.5))
        if d_f % 2:
            d_f += 1
        half = d_f // 2
        name = tr.get("name", "Cross Dissolve")
        for side, (beat, off_f, dur_f) in (("left", left), ("right", right)):
            kind = beat.get("type") or (
                fcpxml.guess_kind(beat.get("src", "")) if beat.get("src") else "gap")
            if kind == "gap":
                warnings.append("transition at %.2fs: the %s side is a gap, there is "
                                "nothing to dissolve" % (F.seconds(boundary_f), side))
                continue
            if kind == "image" or not beat.get("src"):
                continue
            m = S._resolve_media(beat["src"], None, beat.get("asset_duration"))
            start_f = F.frames(beat.get("start", 0))
            if not m["asset_frames"]:
                continue
            if side == "left" and start_f + dur_f + half > m["asset_frames"]:
                warnings.append(
                    "transition at %.2fs: not enough tail handle on %s (needs %.2fs "
                    "more media)" % (F.seconds(boundary_f), beat["src"], F.seconds(half)))
            if side == "right" and start_f - half < 0:
                warnings.append(
                    "transition at %.2fs: not enough head handle on %s (start it "
                    "%.2fs later in the source)"
                    % (F.seconds(boundary_f), beat["src"], F.seconds(half)))
        t = otio.schema.Transition(
            name=name, transition_type=otio.schema.TransitionTypes.SMPTE_Dissolve,
            in_offset=RT(half), out_offset=RT(half))
        t.metadata[META] = _plain({"name": name, "duration_s": F.seconds(d_f),
                                   "uid": tr.get("uid", fcpxml.CROSS_DISSOLVE_UID)})
        return t

    # ---- validate --------------------------------------------------------

    def validate(self, path, local_root=None):
        errors, warns = [], []
        try:
            with open(path) as fh:
                raw = json.load(fh)
        except Exception as e:  # noqa: BLE001
            return ValidateResult(["not JSON: %s" % e], [])
        if not str(raw.get("OTIO_SCHEMA", "")).startswith("Timeline"):
            errors.append("top-level OTIO_SCHEMA is %r, not a Timeline" % raw.get("OTIO_SCHEMA"))
        try:
            tl = otio.adapters.read_from_file(path)
        except Exception as e:  # noqa: BLE001
            errors.append("the OpenTimelineIO library cannot read this file: %s: %s"
                          % (type(e).__name__, e))
            return ValidateResult(errors, warns)

        meta = dict(tl.metadata.get(META) or {})
        rate = float(meta.get("rate") or (tl.duration().rate if tl.duration() else 0))
        if not rate:
            errors.append("no frame rate recorded (metadata.REAL.rate)")
            return ValidateResult(errors, warns)
        root = meta.get("assets_root") or ""

        def on_grid(rt):
            return abs(rt.rate - rate) < 1e-9 and float(rt.value).is_integer()

        def local_path(url):
            p = unquote(urlparse(url).path)
            if local_root and root and p.startswith(root):
                return os.path.join(local_root, os.path.relpath(p, root))
            return p

        missing = []
        for tr in tl.tracks:
            items = list(tr)
            for idx, it in enumerate(items):
                label = "%s/%s" % (tr.name, it.name or type(it).__name__)
                if isinstance(it, otio.schema.Transition):
                    if not (on_grid(it.in_offset) and on_grid(it.out_offset)):
                        errors.append("%s: offsets are not on the %.6g fps frame grid"
                                      % (label, rate))
                    prev = items[idx - 1] if idx else None
                    nxt = items[idx + 1] if idx + 1 < len(items) else None
                    if not isinstance(prev, otio.schema.Clip) or not isinstance(nxt, otio.schema.Clip):
                        errors.append("%s needs a clip on both sides of the cut" % label)
                        continue
                    for side, clip, need in (("before", prev, it.in_offset.value),
                                             ("after", nxt, it.out_offset.value)):
                        mr = clip.media_reference
                        ar = getattr(mr, "available_range", None)
                        kind = (dict(mr.metadata.get(META) or {}) if mr is not None else {}).get("kind")
                        if ar is None or clip.source_range is None or kind in ("image", "title"):
                            continue
                        if side == "before":
                            spare = ar.end_time_exclusive().value - clip.source_range.end_time_exclusive().value
                        else:
                            spare = clip.source_range.start_time.value - ar.start_time.value
                        if spare + 1e-6 < need:
                            errors.append("%s: the clip %s the cut has %d frames of handle; "
                                          "the dissolve needs %d" % (label, side, spare, need))
                    continue
                sr = it.source_range
                if sr is None:
                    errors.append("%s has no source_range" % label)
                    continue
                if not (on_grid(sr.start_time) and on_grid(sr.duration)):
                    errors.append("%s is not on the %.6g fps frame grid (start %s, "
                                  "duration %s)" % (label, rate, sr.start_time, sr.duration))
                if sr.duration.value <= 0:
                    errors.append("%s has a non-positive duration" % label)
                if not isinstance(it, otio.schema.Clip):
                    continue
                mr = it.media_reference
                if isinstance(mr, otio.schema.ExternalReference):
                    url = mr.target_url or ""
                    if not url.startswith("file:///"):
                        errors.append("%s: media path %r is not an absolute file URL"
                                      % (label, url))
                    ar = mr.available_range
                    if ar is not None:
                        if (sr.start_time.value < ar.start_time.value
                                or sr.end_time_exclusive().value > ar.end_time_exclusive().value):
                            errors.append(
                                "%s reads past the end of its source (%s..%s of %s..%s frames)"
                                % (label, sr.start_time.value, sr.end_time_exclusive().value,
                                   ar.start_time.value, ar.end_time_exclusive().value))
                    if url.startswith("file:///") and not os.path.exists(local_path(url)):
                        missing.append(local_path(url))
                    rm = dict(mr.metadata.get(META) or {})
                    if rm.get("kind") == "title":
                        if not str((rm.get("title") or {}).get("text", "")).strip():
                            errors.append("%s is a rendered title with no text" % label)
                        lp = local_path(url)
                        if os.path.exists(lp):
                            size = title_raster.png_size(lp)
                            want = (int(meta.get("width") or rm.get("width") or 0),
                                    int(meta.get("height") or rm.get("height") or 0))
                            if size is None:
                                errors.append("%s: rendered title %s is not a readable image"
                                              % (label, lp))
                            elif want[0] and size != want:
                                errors.append("%s: rendered title is %dx%d, the sequence is %dx%d"
                                              % ((label,) + tuple(size) + want))
                elif isinstance(mr, otio.schema.GeneratorReference):
                    if mr.generator_kind == GENERATOR_KIND and not str(
                            mr.parameters.get("text", "")).strip():
                        errors.append("%s is a title clip with no text" % label)
                else:
                    errors.append("%s has no media reference" % label)

        vt = list(tl.video_tracks())
        if not vt:
            errors.append("no video track")
            return ValidateResult(errors, warns)
        total = vt[0].duration().value
        for tr in vt[1:]:
            if tr.duration().value > total:
                errors.append("overlay track %s runs past the end of the primary "
                              "storyline (%d > %d frames)" % (tr.name, tr.duration().value, total))
        for tr in tl.audio_tracks():
            if tr.duration().value > total:
                warns.append("audio track %s runs %.2fs past the end of the visual timeline"
                             % (tr.name, (tr.duration().value - total) / rate))
        if meta.get("total_frames") is not None and int(meta["total_frames"]) != int(total):
            errors.append("declared total_frames %s does not match V1 length %d"
                          % (meta["total_frames"], total))
        for p in sorted(set(missing)):
            warns.append("not found from here: %s (fine when the media only lives "
                         "on the machine that opens the timeline)" % p)
        return ValidateResult(errors, warns)


TARGET = OTIOTarget()
