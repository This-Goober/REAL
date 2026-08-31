#!/usr/bin/env python3
"""
fcpxml.py — build a Final Cut Pro FCPXML timeline from a story JSON.

Usage:
    python3 fcpxml.py build story.json out.fcpxml [--probe]
    python3 fcpxml.py probe /path/to/media            # print probed media info
    python3 fcpxml.py schema                          # print the story schema

Design notes (why things are the way they are) live in
references/fcpxml-notes.md. The short version:

  * ALL timeline math is done in integer FRAMES and only rendered to FCPXML
    rational strings at the very end. Never float seconds. Frame drift is the
    #1 cause of an import that "works" but sits a frame off everywhere.
  * Images become <video> elements referencing an asset with duration="0s"
    and a format WITHOUT frameDuration. Videos become <asset-clip> elements
    referencing an asset with a real duration and a format WITH frameDuration.
    Using the wrong element type is the #1 cause of a hard FCP rejection.
  * A child (connected/anchored) element's `offset` is expressed in its
    PARENT's local timebase, which begins at the parent's `start` value —
    not in sequence time. Everything here goes through `_child_offset`.
"""

import json
import math
import os
import subprocess
import sys
from fractions import Fraction
from xml.sax.saxutils import escape, quoteattr

FCPXML_VERSION = "1.13"

# name -> (frameDuration numerator, denominator)
FRAME_DURATIONS = {
    "23.976": (1001, 24000),
    "24": (100, 2400),
    "25": (100, 2500),
    "29.97": (1001, 30000),
    "30": (100, 3000),
    "50": (100, 5000),
    "59.94": (1001, 60000),
    "60": (100, 6000),
}

BASIC_TITLE_UID = (
    ".../Titles.localized/Bumper:Opener.localized/"
    "Basic Title.localized/Basic Title.moti"
)
CROSS_DISSOLVE_UID = "FFTransition_CrossDissolve"

# FCP's own convention: generators/titles/gaps live on an internal timeline
# that starts one hour in. Harmless for assets, expected for these.
GENERATOR_START_FRAMES_SECONDS = 3600


class BuildError(Exception):
    pass


# --------------------------------------------------------------------------
# time
# --------------------------------------------------------------------------

class Clock:
    """Integer-frame time, rendered to FCPXML rational strings."""

    def __init__(self, fps_key):
        if fps_key not in FRAME_DURATIONS:
            raise BuildError(
                "frame_rate %r not supported; use one of %s"
                % (fps_key, ", ".join(sorted(FRAME_DURATIONS)))
            )
        self.key = fps_key
        self.num, self.den = FRAME_DURATIONS[fps_key]
        # exact frames per second as a Fraction
        self.fps = Fraction(self.den, self.num)

    def frames(self, seconds):
        """Seconds (float/int/str) -> nearest whole frame. Half-up."""
        if seconds is None:
            return None
        f = Fraction(str(seconds)) * self.fps
        return int(math.floor(f + Fraction(1, 2)))

    def ceil_frames(self, seconds):
        f = Fraction(str(seconds)) * self.fps
        return int(math.ceil(f))

    def t(self, frames):
        """Frames -> '<n>/<d>s' (or '<k>s' when it lands on whole seconds)."""
        if frames == 0:
            return "0s"
        n = frames * self.num
        d = self.den
        g = math.gcd(n, d) if n >= 0 else math.gcd(-n, d)
        n //= g
        d //= g
        if d == 1:
            return "%ds" % n
        return "%d/%ds" % (n, d)

    def seconds(self, frames):
        return float(Fraction(frames * self.num, self.den))

    def frame_duration_str(self):
        return "%d/%ds" % (self.num, self.den)


# --------------------------------------------------------------------------
# media probing
# --------------------------------------------------------------------------

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff", ".gif", ".bmp", ".webp"}
AUDIO_EXTS = {".wav", ".aif", ".aiff", ".m4a", ".mp3", ".caf", ".flac"}


def guess_kind(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in AUDIO_EXTS:
        return "audio"
    return "video"


def probe(path):
    """ffprobe -> dict. Returns {} if the file isn't reachable from here."""
    if not os.path.exists(path):
        return {}
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=60,
        )
        data = json.loads(out.stdout or "{}")
    except Exception:
        return {}
    info = {"probed": True}
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if v:
        info["width"] = int(v.get("width") or 0)
        info["height"] = int(v.get("height") or 0)
        rate = v.get("r_frame_rate") or "0/1"
        try:
            info["fps"] = float(Fraction(rate))
        except Exception:
            info["fps"] = 0.0
    if a:
        info["has_audio"] = True
        info["audio_channels"] = int(a.get("channels") or 2)
        info["audio_rate"] = int(a.get("sample_rate") or 48000)
    dur = (data.get("format") or {}).get("duration")
    if dur:
        info["duration"] = float(dur)
    return info


# --------------------------------------------------------------------------
# XML writing (tiny hand-rolled emitter — order of children matters in FCPXML)
# --------------------------------------------------------------------------

# FCP validates imports against its DTD and the content models are SEQUENCES,
# not choices — children in the wrong order are a hard rejection, not a
# warning. This table is the canonical order, taken from the DTD's own error
# text for <title>:
#
#   (param*, text*, text-style-def*, note?,
#    (object-tracker?, adjust-crop?, adjust-corners?, adjust-conform?,
#     adjust-transform?, adjust-blend?, adjust-stabilization?,
#     adjust-rollingShutter?, adjust-360-transform?, adjust-reorient?,
#     adjust-orientation?, adjust-cinematic?, adjust-colorConform?,
#     adjust-stereo-3D?),
#    (audio|video|clip|title|caption|mc-clip|ref-clip|sync-clip|asset-clip|
#     audition|spine|live-drawing)*, marker*, …)
#
# Same shape applies to asset-clip / video / clip. Ties keep insertion order
# (the sort is stable), so spine order and lane order are untouched.
CHILD_RANK = {
    "media-rep": 5, "metadata": 6, "bookmark": 7,
    "conform-rate": 10, "timeMap": 11,
    "param": 20,
    "text": 30, "text-style-def": 31, "note": 32,
    "object-tracker": 40,
    "adjust-crop": 41, "adjust-corners": 42, "adjust-conform": 43,
    "adjust-transform": 44, "adjust-blend": 45, "adjust-stabilization": 46,
    "adjust-rollingShutter": 47, "adjust-360-transform": 48,
    "adjust-reorient": 49, "adjust-orientation": 50, "adjust-cinematic": 51,
    "adjust-colorConform": 52, "adjust-stereo-3D": 53,
    "adjust-volume": 60, "adjust-panner": 61,
    "filter-video": 70, "filter-video-mask": 71, "filter-audio": 72,
    "audio": 100, "video": 100, "clip": 100, "title": 100, "caption": 100,
    "mc-clip": 100, "ref-clip": 100, "sync-clip": 100, "asset-clip": 100,
    "audition": 100, "spine": 100, "gap": 100, "transition": 100,
    "live-drawing": 100,
    "marker": 200, "chapter-marker": 201, "rating": 202, "keyword": 203,
    "analysis-marker": 204,
}
UNRANKED = 99  # anything unlisted keeps its place, ahead of anchored items


def order_children(el):
    """Recursively put every element's children in DTD order. Stable."""
    if isinstance(el, str):
        return
    el.children.sort(
        key=lambda c: CHILD_RANK.get(getattr(c, "tag", ""), UNRANKED)
        if not isinstance(c, str) else UNRANKED)
    for c in el.children:
        order_children(c)

class El:
    def __init__(self, tag, **attrs):
        self.tag = tag
        self.attrs = []
        self.children = []
        self.set(**attrs)

    def set(self, **attrs):
        for k, v in attrs.items():
            if v is None:
                continue
            key = k.rstrip("_").replace("__", "-")
            val = str(v)
            if key == "name":
                # Final Cut refuses the entire import if any project/event/clip
                # name contains '/' or a newline ("You may not use '/' or the
                # return key in names") — and the error fires BEFORE media
                # resolution, so it masquerades as a corrupt file. Sanitize
                # centrally so no story.json can produce an unimportable file.
                val = val.replace("/", "\u00b7").replace("\n", " ").replace("\r", " ")
            self.attrs.append((key, val))
        return self

    def add(self, child):
        if child is not None:
            self.children.append(child)
        return child

    def render(self, indent=0):
        pad = "    " * indent
        a = "".join(" %s=%s" % (k, quoteattr(v)) for k, v in self.attrs)
        if not self.children:
            return "%s<%s%s/>" % (pad, self.tag, a)
        if len(self.children) == 1 and isinstance(self.children[0], str):
            return "%s<%s%s>%s</%s>" % (
                pad, self.tag, a, escape(self.children[0]), self.tag)
        parts = ["%s<%s%s>" % (pad, self.tag, a)]
        for c in self.children:
            if isinstance(c, str):
                parts.append("    " * (indent + 1) + escape(c))
            else:
                parts.append(c.render(indent + 1))
        parts.append("%s</%s>" % (pad, self.tag))
        return "\n".join(parts)


# --------------------------------------------------------------------------
# resources
# --------------------------------------------------------------------------

class Resources:
    def __init__(self, clock, opts):
        self.clock = clock
        self.opts = opts
        self._n = 0
        self.elements = []
        self._formats = {}
        self._assets = {}
        self._effects = {}

    def _id(self):
        self._n += 1
        return "r%d" % self._n

    def sequence_format(self, width, height):
        key = ("seqfmt", width, height, self.clock.key)
        if key not in self._formats:
            rid = self._id()
            el = El("format", id=rid,
                    name="FFVideoFormatRateUndefined",
                    frameDuration=self.clock.frame_duration_str(),
                    width=width, height=height,
                    colorSpace="1-1-1 (Rec. 709)")
            self.elements.append(el)
            self._formats[key] = rid
        return self._formats[key]

    def _video_format(self, width, height, fps_key):
        key = ("vidfmt", width, height, fps_key)
        if key not in self._formats:
            num, den = FRAME_DURATIONS[fps_key]
            rid = self._id()
            el = El("format", id=rid,
                    name="FFVideoFormatRateUndefined",
                    frameDuration="%d/%ds" % (num, den),
                    width=width, height=height,
                    colorSpace="1-1-1 (Rec. 709)")
            self.elements.append(el)
            self._formats[key] = rid
        return self._formats[key]

    def _image_format(self, width, height):
        key = ("imgfmt", width, height)
        if key not in self._formats:
            rid = self._id()
            # NOTE: deliberately no frameDuration — an image format must not
            # declare one, or FCP treats the still as timed media.
            el = El("format", id=rid,
                    name="FFVideoFormatRateUndefined",
                    width=width, height=height,
                    colorSpace="1-13-1")
            self.elements.append(el)
            self._formats[key] = rid
        return self._formats[key]

    def asset(self, media):
        """media: resolved dict from Story._resolve_media."""
        src = media["url"]
        if src in self._assets:
            return self._assets[src]
        rid = self._id()
        kind = media["kind"]
        name = media["name"]
        attrs = dict(id=rid, name=name, start="0s",
                     hasVideo=None, hasAudio=None)
        if kind == "image":
            fmt = self._image_format(media.get("width") or self.opts["width"],
                                     media.get("height") or self.opts["height"])
            attrs.update(duration="0s", hasVideo="1", format=fmt,
                         videoSources="1")
        elif kind == "audio":
            dur_f = media["asset_frames"]
            attrs.update(duration=self.clock.t(dur_f), hasAudio="1",
                         audioSources="1",
                         audioChannels=media.get("audio_channels", 2),
                         audioRate=media.get("audio_rate", 48000))
        else:  # video
            fmt = self._video_format(media.get("width") or self.opts["width"],
                                     media.get("height") or self.opts["height"],
                                     media.get("fps_key") or self.clock.key)
            dur_f = media["asset_frames"]
            attrs.update(duration=self.clock.t(dur_f), hasVideo="1",
                         format=fmt, videoSources="1")
            if media.get("has_audio"):
                attrs.update(hasAudio="1", audioSources="1",
                             audioChannels=media.get("audio_channels", 2),
                             audioRate=media.get("audio_rate", 48000))
        el = El("asset", **attrs)
        el.add(El("media-rep", kind="original-media", src=src))
        self.elements.append(el)
        self._assets[src] = rid
        return rid

    def effect(self, name, uid):
        if uid not in self._effects:
            rid = self._id()
            self.elements.append(El("effect", id=rid, name=name, uid=uid))
            self._effects[uid] = rid
        return self._effects[uid]


# --------------------------------------------------------------------------
# adjustments
# --------------------------------------------------------------------------

def _keyframe_param(name, keyframes, clock, base_frames):
    """keyframes: list of {t: seconds-within-clip, value: str}."""
    p = El("param", name=name)
    anim = El("keyframeAnimation")
    for kf in keyframes:
        f = base_frames + clock.frames(kf["t"])
        attrs = {"time": clock.t(f), "value": str(kf["value"])}
        if kf.get("curve"):
            attrs["curve"] = kf["curve"]
        if kf.get("interp"):
            attrs["interp"] = kf["interp"]
        anim.add(El("keyframe", **attrs))
    p.add(anim)
    return p


def build_transform(spec, clock, base_frames):
    """spec: {'from': {...}, 'to': {...}, 'duration': s} or a static dict."""
    if not spec:
        return None
    if "from" in spec or "to" in spec:
        a = spec.get("from", {})
        b = spec.get("to", {})
        dur = spec.get("duration")
        if dur is None:
            raise BuildError("kenburns/transform animation needs a 'duration'")
        el = El("adjust-transform")
        for key, param in (("position", "position"), ("scale", "scale"),
                           ("rotation", "rotation"), ("anchor", "anchor")):
            if key not in a and key not in b:
                continue
            va = a.get(key, b.get(key))
            vb = b.get(key, a.get(key))
            el.add(_keyframe_param(
                param,
                [{"t": 0, "value": _vec(va)},
                 {"t": dur, "value": _vec(vb), "curve": "smooth"}],
                clock, base_frames))
        return el
    attrs = {}
    for key in ("position", "scale", "anchor"):
        if key in spec:
            attrs[key] = _vec(spec[key])
    if "rotation" in spec:
        attrs["rotation"] = str(spec["rotation"])
    return El("adjust-transform", **attrs) if attrs else None


def _vec(v):
    if isinstance(v, (list, tuple)):
        return " ".join(_num(x) for x in v)
    if isinstance(v, (int, float)):
        return "%s %s" % (_num(v), _num(v))
    return str(v)


def _num(x):
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return str(x)


def build_volume(item, clock, base_frames):
    """Constant gain, or a ducking envelope, or an audio fade."""
    duck = item.get("volume_keyframes") or item.get("ducking")
    if duck:
        el = El("adjust-volume")
        el.add(_keyframe_param("amount", duck, clock, base_frames))
        return el
    if item.get("volume_db") is not None:
        return El("adjust-volume", amount="%sdB" % _num(item["volume_db"]))
    return None


def build_blend(item, clock, base_frames, dur_frames):
    """Opacity: a constant, or fade in/out expressed as opacity keyframes."""
    fi = item.get("fade_in")
    fo = item.get("fade_out")
    kfs = item.get("opacity_keyframes")
    if kfs:
        el = El("adjust-blend")
        el.add(_keyframe_param("amount", kfs, clock, base_frames))
        return el
    if fi or fo:
        total = clock.seconds(dur_frames)
        pts = []
        if fi:
            pts += [{"t": 0, "value": 0}, {"t": fi, "value": 1, "curve": "smooth"}]
        else:
            pts += [{"t": 0, "value": 1}]
        if fo:
            pts += [{"t": max(0, total - fo), "value": 1},
                    {"t": total, "value": 0, "curve": "smooth"}]
        el = El("adjust-blend")
        el.add(_keyframe_param("amount", pts, clock, base_frames))
        return el
    if item.get("opacity") is not None:
        return El("adjust-blend", amount=_num(item["opacity"]))
    return None


# --------------------------------------------------------------------------
# story -> fcpxml
# --------------------------------------------------------------------------

class Story:
    def __init__(self, story, base_dir=".", do_probe=True):
        self.raw = story
        self.base_dir = base_dir
        self.do_probe = do_probe
        self.warnings = []

        fr = str(story.get("frame_rate", "30"))
        self.clock = Clock(fr)
        self.width = int(story.get("width", 1080))
        self.height = int(story.get("height", 1920))
        self.opts = {"width": self.width, "height": self.height}

        # where the files are, as Final Cut on the Mac will see them
        self.mac_root = story.get("assets_root") or story.get("assets_root_mac") or ""
        # where the files are, as THIS machine sees them (for probing only)
        self.local_root = story.get("assets_root_local") or self.mac_root

        self.res = Resources(self.clock, self.opts)
        self._media_cache = {}
        self._name_index = None

    # ---- media -----------------------------------------------------------

    def _resolve_rel(self, rel):
        """Return the on-disk relative path for `rel`.

        macOS screenshot filenames contain U+202F (narrow no-break space)
        before AM/PM. A story that spells it with an ordinary space would
        otherwise probe nothing AND write a file:// URL that Final Cut cannot
        find — five red Missing Media clips and no error. Match on a
        whitespace-normalised key against what is actually on disk.
        """
        if os.path.isabs(rel) or not self.local_root:
            return rel
        if os.path.exists(os.path.join(self.local_root, rel)):
            return rel
        if self._name_index is None:
            self._name_index = {}
            for dp, _dirs, files in os.walk(self.local_root):
                for fn in files:
                    r = os.path.relpath(os.path.join(dp, fn), self.local_root)
                    self._name_index["".join(" " if c.isspace() else c for c in r)] = r
        key = "".join(" " if c.isspace() else c for c in rel)
        hit = self._name_index.get(key)
        if hit and hit != rel:
            self.warnings.append(
                "resolved %r -> %r (filename contains a non-breaking space)"
                % (rel, hit))
            return hit
        return rel


    def _resolve_media(self, src, declared_kind=None, declared_duration=None,
                       declared_size=None):
        key = (src, declared_kind)
        if key in self._media_cache:
            return self._media_cache[key]

        src = self._resolve_rel(src)
        if os.path.isabs(src):
            mac_path = src
            local_path = src
        else:
            mac_path = os.path.join(self.mac_root, src) if self.mac_root else src
            local_path = os.path.join(self.local_root, src) if self.local_root else src

        kind = declared_kind or guess_kind(mac_path)
        info = probe(local_path) if self.do_probe else {}
        if not info and self.do_probe:
            self.warnings.append(
                "could not probe %s — using declared values (fine when the "
                "media only exists on the Mac)" % src)

        dur = declared_duration if declared_duration is not None else info.get("duration")
        if kind != "image" and dur is None:
            raise BuildError(
                "no duration for %r. Either make the file reachable for probing "
                "or give it 'asset_duration' in the story." % src)

        fps_key = self.clock.key
        if info.get("fps"):
            best = min(FRAME_DURATIONS,
                       key=lambda k: abs(Fraction(*reversed(FRAME_DURATIONS[k])) - Fraction(str(round(info["fps"], 3)))))
            fps_key = best

        w = info.get("width") or (declared_size or [None, None])[0]
        h = info.get("height") or (declared_size or [None, None])[1]
        if kind == "image" and not w:
            self.warnings.append(
                "%s: image size unknown, declaring the sequence size (%dx%d). "
                "If the still isn't that size it will scale wrong in FCP — add "
                "\"width\"/\"height\" to that beat."
                % (src, self.width, self.height))

        media = {
            "url": _file_url(mac_path),
            "local": local_path,
            "name": os.path.splitext(os.path.basename(mac_path))[0],
            "kind": kind,
            "width": w,
            "height": h,
            "fps_key": fps_key,
            "has_audio": info.get("has_audio", kind in ("audio",)),
            "audio_channels": info.get("audio_channels", 2),
            "audio_rate": info.get("audio_rate", 48000),
            "asset_frames": self.clock.ceil_frames(dur) if dur is not None else 0,
            "asset_seconds": dur,
            "exists_locally": os.path.exists(local_path),
        }
        if kind == "video" and info.get("has_audio") is None:
            media["has_audio"] = True  # assume; FCP tolerates the claim
        self._media_cache[key] = media
        return media

    # ---- helpers ---------------------------------------------------------

    def _child_offset(self, parent_start_f, parent_offset_f, child_abs_f):
        """Anchored children are addressed in the parent's local timebase."""
        return parent_start_f + (child_abs_f - parent_offset_f)

    def _make_item(self, spec, offset_f, dur_f, lane=None,
                   parent_start_f=0, parent_offset_f=0, absolute=True):
        """Build one story element (spine item or anchored child)."""
        kind = spec.get("type")
        if kind in (None, "auto"):
            kind = guess_kind(spec.get("src", "")) if spec.get("src") else "gap"
        if spec.get("text") is not None and kind not in ("title",):
            kind = "title"

        if lane is not None and not absolute:
            off_f = self._child_offset(parent_start_f, parent_offset_f, offset_f)
        else:
            off_f = offset_f

        common = dict(offset=self.clock.t(off_f),
                      duration=self.clock.t(dur_f))
        if lane is not None:
            common["lane"] = lane

        if kind == "title":
            el = self._title(spec, common, dur_f)
            start_f = self.clock.frames(GENERATOR_START_FRAMES_SECONDS)
        elif kind == "gap":
            start_f = self.clock.frames(GENERATOR_START_FRAMES_SECONDS)
            el = El("gap", name=spec.get("name", "Gap"),
                    start=self.clock.t(start_f), **common)
        elif kind == "image":
            media = self._resolve_media(
                spec["src"], "image", None,
                [spec.get("width"), spec.get("height")])
            ref = self.res.asset(media)
            start_f = 0
            el = El("video", ref=ref, name=spec.get("name", media["name"]),
                    start="0s", **common)
        elif kind == "audio":
            media = self._resolve_media(spec["src"], "audio",
                                        spec.get("asset_duration"))
            ref = self.res.asset(media)
            start_f = self.clock.frames(spec.get("start", 0))
            el = El("asset-clip", ref=ref,
                    name=spec.get("name", media["name"]),
                    start=self.clock.t(start_f),
                    audioRole=spec.get("role", "dialogue"), **common)
        else:  # video
            media = self._resolve_media(spec["src"], "video",
                                        spec.get("asset_duration"))
            ref = self.res.asset(media)
            start_f = self.clock.frames(spec.get("start", 0))
            attrs = dict(ref=ref, name=spec.get("name", media["name"]),
                         start=self.clock.t(start_f))
            if media["has_audio"]:
                attrs["audioRole"] = spec.get("role", "dialogue")
            if spec.get("video_role"):
                attrs["videoRole"] = spec["video_role"]
            el = El("asset-clip", **attrs, **common)
            end_f = start_f + dur_f
            if media["asset_frames"] and end_f > media["asset_frames"]:
                self.warnings.append(
                    "%s: asks for %.2fs from %.2fs but the file is only %.2fs long"
                    % (spec.get("src"), self.clock.seconds(dur_f),
                       self.clock.seconds(start_f),
                       self.clock.seconds(media["asset_frames"])))

        # --- adjustments, in the order FCPXML expects ---
        if kind == "gap":
            return el, start_f, off_f
        t = build_transform(spec.get("kenburns") or spec.get("transform"),
                            self.clock, start_f)
        if t is not None:
            el.add(t)
        b = build_blend(spec, self.clock, start_f, dur_f)
        if b is not None:
            el.add(b)
        v = build_volume(spec, self.clock, start_f)
        if v is not None and kind in ("video", "audio"):
            el.add(v)

        # Child order is fixed up globally by order_children() at render time.
        return el, start_f, off_f

    def _title(self, spec, common, dur_f):
        eff = self.res.effect("Basic Title", BASIC_TITLE_UID)
        text = str(spec.get("text", ""))
        self._title_n = getattr(self, "_title_n", 0) + 1
        sid = "ts%d" % self._title_n  # deterministic: same story -> same file
        start_f = self.clock.frames(GENERATOR_START_FRAMES_SECONDS)
        el = El("title", ref=eff,
                name=spec.get("name", (text[:40] or "Title")),
                start=self.clock.t(start_f), **common)
        pos = spec.get("position")
        if pos is not None:
            el.add(El("adjust-transform", position=_vec(pos)))
        txt = El("text")
        txt.add(_text_style_ref(sid, text))
        el.add(txt)
        style = El("text-style",
                   font=spec.get("font", "Helvetica Neue"),
                   fontSize=spec.get("font_size", 96),
                   fontFace=spec.get("font_face", "Bold"),
                   fontColor=_color(spec.get("color", [1, 1, 1, 1])),
                   alignment=spec.get("align", "center"),
                   lineSpacing=spec.get("line_spacing"))
        if spec.get("stroke_color"):
            style.set(strokeColor=_color(spec["stroke_color"]),
                      strokeWidth=spec.get("stroke_width", 6))
        if spec.get("shadow"):
            style.set(shadowColor=_color(spec.get("shadow_color", [0, 0, 0, 0.75])),
                      shadowOffset=spec.get("shadow_offset", "8 315"),
                      shadowBlurRadius=spec.get("shadow_blur", 12))
        sdef = El("text-style-def", id=sid)
        sdef.add(style)
        el.add(sdef)
        return el

    # ---- the build -------------------------------------------------------

    def build(self):
        clock = self.clock
        seq_fmt = self.res.sequence_format(self.width, self.height)
        spine = El("spine")

        beats = self.raw.get("beats") or self.raw.get("timeline") or []
        if not beats:
            raise BuildError("story has no 'beats'")

        # 1. lay the primary storyline out sequentially
        cursor = 0
        placed = []
        for i, beat in enumerate(beats):
            if beat.get("offset") is not None:
                cursor = clock.frames(beat["offset"])
            dur = beat.get("duration")
            if dur is None:
                if beat.get("type") == "video" or (
                        beat.get("src") and guess_kind(beat["src"]) == "video"):
                    m = self._resolve_media(beat["src"], None,
                                            beat.get("asset_duration"))
                    dur_f = m["asset_frames"] - clock.frames(beat.get("start", 0))
                else:
                    raise BuildError("beat %d needs a 'duration'" % (i + 1))
            else:
                dur_f = clock.frames(dur)
            if dur_f <= 0:
                raise BuildError("beat %d has a non-positive duration" % (i + 1))
            placed.append((beat, cursor, dur_f))
            cursor += dur_f
        total_f = cursor

        # 2. build each spine item plus its anchored children
        items = []
        for beat, off_f, dur_f in placed:
            el, start_f, _ = self._make_item(beat, off_f, dur_f)
            items.append((el, beat, off_f, dur_f, start_f))

        # 3. overlays anchored to their beat
        for el, beat, off_f, dur_f, start_f in items:
            for ov in beat.get("overlays", []) or []:
                ov_off_abs = off_f + clock.frames(ov.get("offset", 0))
                ov_dur = ov.get("duration")
                ov_dur_f = clock.frames(ov_dur) if ov_dur is not None else dur_f - (ov_off_abs - off_f)
                if ov_dur_f <= 0:
                    raise BuildError("overlay on beat at %s has non-positive duration"
                                     % clock.t(off_f))
                child, _, _ = self._make_item(
                    ov, ov_off_abs, ov_dur_f,
                    lane=int(ov.get("lane", 1)),
                    parent_start_f=start_f, parent_offset_f=off_f,
                    absolute=False)
                el.add(child)

        # 4. globals (narration, music, full-width captions) anchor to beat 1
        first_el, first_beat, first_off, first_dur, first_start = items[0]
        for g in (self.raw.get("connected") or []) + (self.raw.get("audio") or []):
            g_off_abs = clock.frames(g.get("offset", 0))
            g_dur = g.get("duration")
            if g_dur is None:
                m = self._resolve_media(g["src"], g.get("type"),
                                        g.get("asset_duration"))
                g_dur_f = m["asset_frames"] - clock.frames(g.get("start", 0))
            else:
                g_dur_f = clock.frames(g_dur)
            lane = int(g.get("lane", -1))
            child, _, _ = self._make_item(
                g, g_off_abs, g_dur_f, lane=lane,
                parent_start_f=first_start, parent_offset_f=first_off,
                absolute=False)
            first_el.add(child)
            if g_off_abs + g_dur_f > total_f:
                self.warnings.append(
                    "connected clip %s runs %.2fs past the end of the visual "
                    "timeline" % (g.get("src", g.get("text", "?")),
                                  clock.seconds(g_off_abs + g_dur_f - total_f)))

        # 5. spine, with transitions interleaved at the cuts
        for idx, (el, beat, off_f, dur_f, start_f) in enumerate(items):
            spine.add(el)
            tr = beat.get("transition_out") or (
                items[idx + 1][1].get("transition_in") if idx + 1 < len(items) else None)
            if tr and idx + 1 < len(items):
                spine.add(self._transition(tr, off_f + dur_f, items, idx))

        seq = El("sequence", format=seq_fmt,
                 duration=clock.t(total_f), tcStart="0s", tcFormat="NDF",
                 audioLayout=self.raw.get("audio_layout", "stereo"),
                 audioRate=self.raw.get("audio_rate", "48k"))
        seq.add(spine)

        proj = El("project", name=self.raw.get("project", "Untitled"))
        proj.add(seq)
        event = El("event", name=self.raw.get("event", "Sequenced"))
        event.add(proj)
        lib = El("library")
        lib.add(event)

        resources = El("resources")
        for r in self.res.elements:
            resources.add(r)

        root = El("fcpxml", version=FCPXML_VERSION)
        root.add(resources)
        root.add(lib)

        self.total_frames = total_f
        order_children(root)
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                "<!DOCTYPE fcpxml>\n" + root.render() + "\n")

    def _transition(self, tr, boundary_f, items, idx):
        clock = self.clock
        d_f = clock.frames(tr.get("duration", 0.5))
        if d_f % 2:
            d_f += 1
        half = d_f // 2
        name = tr.get("name", "Cross Dissolve")
        uid = tr.get("uid", CROSS_DISSOLVE_UID)
        eff = self.res.effect(name, uid)

        # handle check: both neighbours must have media to borrow
        left = items[idx]
        right = items[idx + 1]
        for side, (el, beat, off_f, dur_f, start_f) in (("left", left), ("right", right)):
            if beat.get("type") == "image" or (
                    beat.get("src") and guess_kind(beat.get("src", "")) == "image"):
                continue
            if beat.get("src") is None:
                continue
            m = self._resolve_media(beat["src"], None, beat.get("asset_duration"))
            if not m["asset_frames"]:
                continue
            if side == "left" and start_f + dur_f + half > m["asset_frames"]:
                self.warnings.append(
                    "transition at %s: not enough tail handle on %s (needs %.2fs "
                    "more media)" % (clock.t(boundary_f), beat["src"],
                                     clock.seconds(half)))
            if side == "right" and start_f - half < 0:
                self.warnings.append(
                    "transition at %s: not enough head handle on %s (start it "
                    "%.2fs later in the source)"
                    % (clock.t(boundary_f), beat["src"], clock.seconds(half)))

        el = El("transition", name=name,
                offset=clock.t(boundary_f - half), duration=clock.t(d_f))
        fv = El("filter-video", ref=eff, name=name)
        # No <param> children by default. FCP 11 imported the transition but
        # warned "Encountered an unexpected value" when Look/Amount were
        # supplied with guessed enum strings; with no params it uses its own
        # defaults, which is what we want anyway. Pass "params": [{"name":…,
        # "key":…, "value":…}] in the story only once a real FCP export has
        # confirmed the exact strings.
        for p in tr.get("params", []) or []:
            fv.add(El("param", name=p.get("name"), key=p.get("key"),
                      value=p.get("value")))
        el.add(fv)
        return el


def _text_style_ref(sid, text):
    e = El("text-style", ref=sid)
    e.children.append(text)
    return e


def _color(c):
    if isinstance(c, str):
        return c
    vals = list(c) + [1] * (4 - len(c))
    return " ".join(_num(v) for v in vals[:4])


def _file_url(path):
    from urllib.parse import quote
    p = os.path.abspath(path) if not path.startswith("/") else path
    return "file://" + quote(p)


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

SCHEMA_DOC = """\
story.json
----------
{
  "project": "Drone Part 1",          # FCP project name
  "event":   "Reels",                 # FCP event name
  "frame_rate": "30",                 # 23.976 24 25 29.97 30 50 59.94 60
  "width": 1080, "height": 1920,      # sequence format
  "assets_root":       "/Volumes/Media/Reel1",   # path FCP will see
  "assets_root_local": "/mnt/media/Reel1",               # path for probing (optional)

  "beats": [                          # the primary storyline, in order
    {
      "type": "video|image|gap|title",     # optional, inferred from src
      "src": "Videos/take1.mov",
      "start": 2.0,                        # in-point in the SOURCE (video/audio)
      "duration": 4.5,                     # length on the TIMELINE (required for images)
      "asset_duration": 61.2,              # source length, if I can't probe the file
      "role": "dialogue",                  # audioRole
      "volume_db": -6,
      "ducking": [{"t":0,"value":0},{"t":0.4,"value":-15}],   # dB, t = s into the clip
      "fade_in": 0.3, "fade_out": 0.5,     # opacity fades
      "kenburns": {"from":{"scale":1.0,"position":[0,0]},
                   "to":{"scale":1.25,"position":[60,-40]},
                   "duration": 4.5},
      "transition_out": {"name":"Cross Dissolve","duration":0.6},
      "overlays": [                        # anchored to THIS beat
        {"type":"image","src":"Images/wave.png","lane":1,
         "offset":0.5,"duration":2.0,"fade_in":0.2,
         "transform":{"scale":0.6,"position":[0,300]}},
        {"text":"amplitude","lane":2,"offset":1.0,"duration":1.2,
         "font":"Helvetica Neue","font_size":110,"color":[1,1,1,1],
         "position":[0,-620],"align":"center"}
      ]
    }
  ],

  "connected": [                      # spans the whole video (narration, music, captions)
    {"src":"Audio/voice.wav","lane":-1,"offset":0,"role":"dialogue"},
    {"src":"Audio/bed.wav","lane":-2,"offset":0,"duration":58,"role":"music",
     "ducking":[{"t":0,"value":-18},{"t":57,"value":-18}]}
  ]
}

Times are seconds; everything is snapped to whole frames on the way out.
'offset' inside overlays/connected is measured from the start of the parent
beat (overlays) or the start of the timeline (connected).
"""


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "schema":
        print(SCHEMA_DOC)
        return 0
    if cmd == "probe":
        print(json.dumps(probe(argv[2]), indent=2))
        return 0
    if cmd == "build":
        story_path, out_path = argv[2], argv[3]
        do_probe = "--no-probe" not in argv
        story = json.load(open(story_path))
        s = Story(story, base_dir=os.path.dirname(os.path.abspath(story_path)),
                  do_probe=do_probe)
        xml = s.build()
        open(out_path, "w").write(xml)
        print("wrote %s  (%s, %.2fs, %d frames @ %s fps)"
              % (out_path, "%dx%d" % (s.width, s.height),
                 s.clock.seconds(s.total_frames), s.total_frames, s.clock.key))
        for w in s.warnings:
            print("  warning: " + w)
        return 0
    print("unknown command %r" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
