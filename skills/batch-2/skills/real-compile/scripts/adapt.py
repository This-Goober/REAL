#!/usr/bin/env python3
"""
adapt.py — reel.json (the contract) -> story.json (the internal intermediate).

    python3 adapt.py reel.json -o story.json [options]

      --assets-root-local PATH   where the media is reachable from HERE
                                 (overrides reel.json's assets_root_local)
      --stub-dir DIR             where placeholder files get written
                                 (default: the local assets root)
      --no-stubs                 don't create placeholder files
      --no-markers               don't emit beat markers / notes into the build
      --quiet                    only print problems

reel.json is written by /real-storyboarding and is the only input this step
accepts. story.json is nobody's document — it is the shape the verified FCPXML
generator eats, and it is regenerated from reel.json every time. Never hand-edit
it; edit the reel and re-adapt.

WHAT THIS SCRIPT WILL NOT DO
----------------------------
It will not compute a time. Not a duration, not a start, not a total. The clock
belongs to /real-storyboarding and exactly one implementation of it exists. A
reel.json missing times is a REFUSAL, not a thing to estimate — a second
estimator produces timings that look coherent and are wrong, which reads as an
editorial problem rather than a measurement fault. That mistake has already cost
one 59-second error and a page of unnecessary cut-list.

It will not silently fill in a default either. Everything it decides that the
reel did not state is printed as a numbered note, and anything it cannot decide
is a numbered refusal.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fcpxml import FRAME_DURATIONS  # noqa: E402

VISUAL_KINDS = ("video", "image", "text")

# The audio lane enum. `source` means "this asset's own sound" — a demo clip
# played for what it sounds like, which is the whole point of a demo beat.
AUDIO_KINDS = ("narration", "source", "bed", "sfx")
AUDIO_ALIASES = {"voice": "narration", "vo": "narration",
                 "music": "bed", "effects": "sfx", "audio": "source"}
AUDIO_LANES = {"narration": -1, "source": -2, "bed": -3, "sfx": -4}
AUDIO_ROLES = {"narration": "dialogue", "source": "effects",
               "bed": "music", "sfx": "effects"}

SILENCE_FILE = "stubs/unvoiced-narration.wav"
SILENCE_RATE = 48000

# Text styles. A layer may override any of these inline; anything unrecognised
# falls back to "caption" WITH A NOTE — never silently.
STYLES = {
    "caption": dict(font_size=96, position=[0, -620], font_face="Bold",
                    stroke_color=[0, 0, 0, 1], stroke_width=8, shadow=True),
    "title": dict(font_size=132, position=[0, 0], font_face="Bold",
                  stroke_color=[0, 0, 0, 1], stroke_width=10, shadow=True),
    "lower-third": dict(font_size=72, position=[0, -760], font_face="Bold",
                        stroke_color=[0, 0, 0, 1], stroke_width=6, shadow=True),
    "kicker": dict(font_size=64, position=[0, 720], font_face="Regular",
                   shadow=True),
    "word": dict(font_size=110, position=[0, 0], font_face="Bold",
                 stroke_color=[0, 0, 0, 1], stroke_width=8, shadow=True),
    # subtitle: small, bottom-anchored, regular weight — spoken-word transcript
    # text, visually distinct from a caption (editorial emphasis) and a title.
    "subtitle": dict(font_size=58, position=[0, -830], font_face="Regular",
                     stroke_color=[0, 0, 0, 1], stroke_width=4, shadow=True),
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
VIDEO_EXTS = {".mov", ".mp4", ".m4v"}


class Refusal(Exception):
    pass


# --------------------------------------------------------------------------
# frame-exact time
# --------------------------------------------------------------------------

class Frames:
    """Snap every boundary to a whole frame HERE, in one place.

    The generator lays the primary storyline out sequentially, so if each beat
    rounded on its own the spine would drift away from the audio, which is
    placed at absolute offsets. Snapping every boundary once, up front, means
    beat n's start on the timeline is exactly the sum of what came before it.
    """

    def __init__(self, fps_key):
        self.key = fps_key
        self.num, self.den = FRAME_DURATIONS[fps_key]

    def f(self, seconds):
        return int(round(float(seconds) * self.den / self.num))

    def s(self, frames):
        return round(frames * self.num / self.den, 6)

    @property
    def one(self):
        return self.s(1)


def fps_key(value, problems):
    """Map a number from reel.json onto a frame rate the generator supports."""
    if value is None:
        problems.append("reel.fps is missing. The sequence frame rate is not "
                        "something this step may pick.")
        return None
    txt = str(value)
    if txt in FRAME_DURATIONS:
        return txt
    try:
        v = float(value)
    except (TypeError, ValueError):
        problems.append("reel.fps is %r, which is not a number." % value)
        return None
    for k, (n, d) in FRAME_DURATIONS.items():
        if abs(d / n - v) < 0.01:
            return k
    problems.append(
        "reel.fps is %s, which is not a frame rate Final Cut takes. Supported: "
        "%s." % (value, ", ".join(sorted(FRAME_DURATIONS, key=float))))
    return None


# --------------------------------------------------------------------------
# validation — everything wrong, numbered, at once
# --------------------------------------------------------------------------

def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check(reel, local_root):
    """Return (problems, notes). Non-empty problems means refuse."""
    P, N = [], []

    if not isinstance(reel, dict):
        return ["the file is not a JSON object"], N
    if reel.get("version") is None:
        N.append("no top-level \"version\" — assuming the 1.0 schema.")

    r = reel.get("reel")
    if not isinstance(r, dict):
        P.append("no \"reel\" block — the title, size and fps live there.")
        r = {}
    for k in ("width", "height"):
        if not _num(r.get(k)):
            P.append("reel.%s is missing or not a number. Frame size is the "
                     "storyboard's decision, not this step's." % k)
    if not r.get("title"):
        N.append("reel.title is empty — the Final Cut project will be named "
                 "after the input file.")
    fk = fps_key(r.get("fps"), P)

    clock = reel.get("clock")
    if not isinstance(clock, dict):
        P.append("no \"clock\" block. /real-storyboarding owns the clock; this "
                 "step will not compute one. Re-run /real-storyboarding.")
        clock = {}
    elif not _num(clock.get("total_s")) or clock.get("total_s") <= 0:
        P.append("clock.total_s is missing or not a positive number. Runtime is "
                 "not recoverable by summing beats — real silence lives between "
                 "them — and this step does not estimate. Go back to "
                 "/real-storyboarding.")
    if clock.get("mode") not in (None, "estimated", "measured"):
        P.append("clock.mode is %r; expected \"estimated\" or \"measured\"."
                 % clock.get("mode"))
    if clock.get("mode") is None and isinstance(clock, dict) and clock:
        N.append("clock.mode is unset — treating the times as given, without "
                 "claiming they are measured.")
    total_s = clock.get("total_s") if _num(clock.get("total_s")) else None

    if not reel.get("assets_root"):
        P.append("assets_root is missing. It is the folder path AS THE MAC "
                 "RUNNING FINAL CUT SEES IT, and it is baked into every clip; "
                 "getting it wrong is the one mistake that makes an import look "
                 "fine and then show red Missing Media.")
    if not reel.get("assets_root_local") and not local_root:
        N.append("no assets_root_local — media will not be probed. Fine when "
                 "the footage only exists on the Mac; the declared dur_s / w / h "
                 "are used instead.")

    assets = reel.get("assets")
    by_id = {}
    if not isinstance(assets, list):
        P.append("no \"assets\" array.")
        assets = []
    for i, a in enumerate(assets):
        where = "assets[%d]" % i
        if not isinstance(a, dict) or not a.get("id"):
            P.append("%s has no id." % where)
            continue
        aid = a["id"]
        if aid in by_id:
            P.append("two assets share the id %r." % aid)
        by_id[aid] = a
        if not a.get("file"):
            P.append("asset %s has no \"file\"." % aid)
        if a.get("kind") not in ("video", "image", "audio", "text"):
            P.append("asset %s has kind %r; expected video, image, audio or "
                     "text." % (aid, a.get("kind")))
        if a.get("kind") in ("video", "audio") and (
                not _num(a.get("dur_s")) or a.get("dur_s") <= 0):
            P.append("asset %s (%s) has no dur_s. A timed asset with no "
                     "duration cannot be laid on a timeline, and this step does "
                     "not measure files it was handed metadata for."
                     % (aid, a.get("file")))
        if local_root and a.get("file") and not os.path.isabs(a["file"]):
            if not os.path.exists(os.path.join(local_root, a["file"])):
                N.append("asset %s: %s not found under the local root (fine if "
                         "it only exists on the Mac)." % (aid, a["file"]))

    beats = reel.get("beats")
    if not isinstance(beats, list) or not beats:
        P.append("no \"beats\". A reel with no beats is not a reel; if "
                 "/real-storyboarding has not run, run it — this step never "
                 "decides what goes where.")
        beats = []

    seen_beat = set()
    prev_end, prev_id = None, None
    for i, b in enumerate(beats):
        where = "beats[%d]" % i
        if not isinstance(b, dict):
            P.append("%s is not an object." % where)
            continue
        bid = b.get("id") or where
        if not b.get("id"):
            P.append("%s has no id." % where)
        if bid in seen_beat:
            P.append("two beats share the id %r." % bid)
        seen_beat.add(bid)
        if not b.get("name"):
            N.append("beat %s has no name — it will read as an anonymous block "
                     "in Final Cut." % bid)

        if not _num(b.get("t0")) or not _num(b.get("t1")):
            P.append("beat %s has no t0/t1. Times are not optional here and are "
                     "not re-derived: /real-storyboarding computes them from "
                     "anchor_word plus the clock, and this step only reads them."
                     % bid)
            continue
        if b["t1"] <= b["t0"]:
            P.append("beat %s ends at or before it starts (%.3f -> %.3f)."
                     % (bid, b["t0"], b["t1"]))
        if prev_end is not None and b["t0"] < prev_end - 1e-6:
            P.append("beat %s starts at %.3fs, inside beat %s which runs to "
                     "%.3fs. Beats on the primary storyline cannot overlap."
                     % (bid, b["t0"], prev_id, prev_end))
        if total_s is not None and b["t1"] > total_s + 1e-6:
            P.append("beat %s ends at %.3fs, past clock.total_s (%.3fs)."
                     % (bid, b["t1"], total_s))
        prev_end, prev_id = b["t1"], bid

        layers = b.get("layers")
        if layers is None:
            N.append("beat %s has no layers — it becomes a named blank." % bid)
            layers = []
        if not isinstance(layers, list):
            P.append("beat %s: \"layers\" is not an array." % bid)
            layers = []
        zs = {}
        for j, l in enumerate(layers):
            lid = (l.get("id") if isinstance(l, dict) else None) or \
                  "%s.layers[%d]" % (bid, j)
            if not isinstance(l, dict):
                P.append("%s is not an object." % lid)
                continue
            kind = l.get("kind")
            if kind == "audio":
                P.append("layer %s has kind \"audio\". Sound belongs in the "
                         "beat's \"audio\" array, not in \"layers\"." % lid)
                continue
            if kind not in VISUAL_KINDS:
                P.append("layer %s has kind %r; expected video, image or text."
                         % (lid, kind))
                continue
            if not _num(l.get("z")):
                P.append("layer %s has no z. z is bottom-first and decides what "
                         "backs the beat and what sits over it." % lid)
            else:
                zs.setdefault(l["z"], []).append(lid)
            if l.get("anchor_word") is None:
                N.append("layer %s carries no anchor_word — it will re-time "
                         "correctly today but not survive a clock swap." % lid)
            if not _num(l.get("t0")) or not _num(l.get("t1")):
                P.append("layer %s has no t0/t1. This step reads times; it does "
                         "not compute them." % lid)
                continue
            if l["t1"] <= l["t0"]:
                P.append("layer %s ends at or before it starts." % lid)
                continue
            if _num(b.get("t0")) and (l["t0"] < b["t0"] - 1e-6
                                      or l["t1"] > b["t1"] + 1e-6):
                P.append("layer %s runs %.3f–%.3fs but its beat %s is "
                         "%.3f–%.3fs. A layer cannot outlive its beat."
                         % (lid, l["t0"], l["t1"], bid, b["t0"], b["t1"]))
            dur = l["t1"] - l["t0"]

            if kind == "text":
                if not str(l.get("content") or "").strip():
                    P.append("layer %s is text with no content." % lid)
                if not l.get("style"):
                    P.append("layer %s is text with no style. /real-storyboarding "
                             "classifies every text element — title, caption or "
                             "subtitle (lower-third, kicker and word also "
                             "accepted) — and this step never infers the type."
                             % lid)
                elif l["style"] not in STYLES:
                    P.append("layer %s asks for style %r, which is not one of "
                             "%s. An unclassified or misclassified text element "
                             "would export as the wrong kind of thing; go back "
                             "to the tracks page and classify it."
                             % (lid, l["style"], ", ".join(sorted(STYLES))))
                continue

            aid = l.get("asset")
            if aid is None:
                stub = l.get("stub")
                if not isinstance(stub, dict):
                    P.append("layer %s has no asset and no stub. A slot with "
                             "nothing in it is a hole in the export; "
                             "/real-storyboarding must emit a stub spec for it."
                             % lid)
                elif not stub.get("file"):
                    P.append("layer %s has a stub with no \"file\" — the "
                             "placeholder needs a filename so the real render "
                             "can drop in later without re-sequencing." % lid)
                elif not stub.get("spec"):
                    N.append("layer %s: stub has no spec text; the placeholder "
                             "will not say what it is waiting for." % lid)
                continue
            a = by_id.get(aid)
            if a is None:
                P.append("layer %s references asset %r, which is not in the "
                         "assets array." % (lid, aid))
                continue
            if a.get("kind") == "audio":
                P.append("layer %s (visual) references audio asset %s."
                         % (lid, aid))
                continue
            if a.get("kind") == "text":
                P.append("layer %s references text asset %s. A text asset is a "
                         "source of words, not a picture — put the words in a "
                         "text layer's \"content\"." % (lid, aid))
                continue
            if kind != a.get("kind"):
                P.append("layer %s is kind %r but asset %s is %r. Stills and "
                         "movies are different element types in FCPXML and "
                         "crossing them over is a hard rejection, not a warning."
                         % (lid, kind, aid, a.get("kind")))
                continue
            if kind == "video" and _num(a.get("dur_s")) \
                    and dur > a["dur_s"] + 1e-3:
                P.append("layer %s asks for %.2fs of %s but the file is only "
                         "%.2fs long." % (lid, dur, a.get("file"), a["dur_s"]))
        for z, ids in zs.items():
            if len(ids) > 1:
                N.append("beat %s: %s share z=%s — stacking them in the order "
                         "they appear." % (bid, ", ".join(ids), z))

    # audio, beat-level and global
    unvoiced = 0
    for entry, where in _all_audio(reel):
        eid = entry.get("id") or where
        raw_kind = entry.get("kind")
        if raw_kind is None:
            P.append("audio %s has no kind (%s)."
                     % (eid, " / ".join(AUDIO_KINDS)))
        if not _num(entry.get("t0")) or not _num(entry.get("t1")):
            P.append("audio %s has no t0/t1." % eid)
            continue
        if entry["t1"] <= entry["t0"]:
            P.append("audio %s ends at or before it starts." % eid)
        if total_s is not None and entry["t1"] > total_s + 1e-6:
            P.append("audio %s ends at %.3fs, past clock.total_s (%.3fs)."
                     % (eid, entry["t1"], total_s))
        if entry.get("duck_db") is not None and not _num(entry["duck_db"]):
            P.append("audio %s has a non-numeric duck_db." % eid)

        aid = entry.get("asset")
        if not aid:
            # A narration lane with no take yet is the NORMAL state before a
            # recording exists. The whole two-clock design is that the reel is
            # sequenced on the estimated clock first and the voice refines it
            # later; refusing here would mean nothing can be compiled until
            # the voice exists, which is backwards — the point of compiling
            # early is finding out a 60s reel is 34s over BEFORE recording.
            kind, _n = norm_audio_kind(raw_kind)
            if kind == "narration" and str(entry.get("text") or "").strip():
                unvoiced += 1
                continue
            if kind == "narration":
                P.append("audio %s is an unvoiced narration lane with no "
                         "\"text\" either — there is no take and no line, so "
                         "there is nothing to hold the window open with."
                         % eid)
            else:
                P.append("audio %s is a %s lane with no asset. Only narration "
                         "may be empty (it stands in for a take not yet "
                         "recorded); a %s lane with nothing in it is a hole."
                         % (eid, kind, kind))
            continue
        a = by_id.get(aid)
        if a is None:
            P.append("audio %s references asset %r, which is not in the assets "
                     "array." % (eid, aid))
            continue
        if a.get("kind") in ("image", "text"):
            P.append("audio %s references %s, which is an asset of kind %r. A "
                     "still and a block of text have no sound."
                     % (eid, aid, a.get("kind")))
            continue
        kind, note = norm_audio_kind(raw_kind, a)
        if note:
            N.append("audio %s: %s" % (eid, note))
        if kind not in AUDIO_KINDS:
            N.append("audio %s has kind %r, which is outside the enum (%s) — "
                     "giving it a lane of its own."
                     % (eid, raw_kind, " / ".join(AUDIO_KINDS)))
    if unvoiced:
        N.append("%d narration lane(s) have no take yet. Each becomes a silent "
                 "placeholder of exactly its window, and the export is badged "
                 "UNVOICED. The timing is real — it is estimated, not measured."
                 % unvoiced)

    op = reel.get("open") or {}
    for q in op.get("questions") or []:
        N.append("open question %s (beat %s): %s"
                 % (q.get("id", "?"), q.get("beat", "?"), q.get("msg", "")))
    for lid in op.get("unbound_layers") or []:
        N.append("open.unbound_layers still lists %s — it has nothing bound to "
                 "it upstream." % lid)

    return P, N


def norm_audio_kind(raw, asset=None):
    """Normalise an audio lane's kind. Returns (kind, note or None).

    A `bed` pointing at a movie is not a music bed — it is that clip's own
    sound, which is what `source` means. Say so rather than putting a demo take
    on the music lane.
    """
    kind = AUDIO_ALIASES.get(raw, raw)
    if asset is not None and asset.get("kind") == "video" and kind == "bed":
        return "source", ("kind \"bed\" on the video asset %s means that "
                          "clip's own sound — normalised to \"source\"."
                          % asset.get("id"))
    return kind, None


def _all_audio(reel):
    out = []
    for i, b in enumerate(reel.get("beats") or []):
        if not isinstance(b, dict):
            continue
        for j, e in enumerate(b.get("audio") or []):
            if isinstance(e, dict):
                out.append((e, "beats[%d].audio[%d]" % (i, j)))
    for i, e in enumerate(reel.get("connected") or []):
        if isinstance(e, dict) and e.get("kind") not in ("video", "image",
                                                         "text"):
            out.append((e, "connected[%d]" % i))
    return out


# --------------------------------------------------------------------------
# stubs — real placeholder files, so the import has grey holes not red ones
# --------------------------------------------------------------------------

def make_stub(path, w, h, label, spec_text, seconds, fps_k, notes):
    """Write a placeholder file. Returns the path actually written, or None."""
    if os.path.exists(path):
        notes.append("stub %s already exists — leaving it alone (that is how "
                     "the real render drops in: same filename)."
                     % os.path.basename(path))
        return path
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    ext = os.path.splitext(path)[1].lower()
    png = path if ext in IMAGE_EXTS else os.path.splitext(path)[0] + ".png"
    if not _png(png, w, h, label, spec_text, seconds):
        notes.append("could not write stub %s (no PIL and no ffmpeg) — that "
                     "layer will import as red Missing Media."
                     % os.path.basename(path))
        return None
    if ext in VIDEO_EXTS:
        if _stub_video(png, path, seconds, fps_k):
            os.remove(png)
            return path
        notes.append("no ffmpeg — wrote %s as a still instead of a movie."
                     % os.path.basename(png))
        return png
    return png


def _png(path, w, h, label, spec_text, seconds):
    # ASCII only: this is drawn with PIL's built-in font, which has no dashes.
    caption = "%s\n\nSTUB: %s\n%s" % (label, spec_text or "unspecified",
                                      "%.2fs" % seconds)
    caption = caption.replace("—", "-").replace("’", "'")
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (int(w), int(h)), (52, 53, 60))
        d = ImageDraw.Draw(img)
        d.rectangle([8, 8, int(w) - 9, int(h) - 9], outline=(120, 122, 135),
                    width=4)
        size = max(18, int(min(w, h) / 26))
        try:
            font = ImageFont.load_default(size=size)
        except TypeError:
            font = ImageFont.load_default()
        per_line = max(12, int(w / (size * 0.62)))
        lines = []
        for para in caption.split("\n"):
            line = ""
            for word in para.split():
                if len(line) + len(word) + 1 > per_line:
                    lines.append(line)
                    line = word
                else:
                    line = (line + " " + word).strip()
            lines.append(line)
        step = int(size * 1.5)
        y = int(h / 2 - step * len(lines) / 2)
        for line in lines:
            d.text((int(w / 2), y), line, fill=(206, 208, 220), font=font,
                   anchor="ma")
            y += step
        img.save(path)
        return True
    except Exception:
        pass
    try:  # PIL absent: a flat grey card is still better than red media
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             "color=c=0x34353C:s=%dx%d" % (int(w), int(h)), "-frames:v", "1",
             path], check=True, capture_output=True)
        return True
    except Exception:
        return False


def make_silence(path, seconds, notes):
    """A real silent WAV, so an unvoiced narration lane is a visible, editable,
    correctly-timed clip in the narration lane rather than an absence.

    Written with the stdlib — no ffmpeg, no PIL, nothing to be missing. One
    file serves every unvoiced line; each clip reads its own window out of it.
    """
    import wave as wavelib
    need = int(seconds * SILENCE_RATE) + SILENCE_RATE
    if os.path.exists(path):
        try:
            with wavelib.open(path) as w:
                if w.getnframes() >= need and w.getframerate() == SILENCE_RATE:
                    return path, w.getnframes() / float(w.getframerate())
        except Exception:
            pass
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    try:
        with wavelib.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SILENCE_RATE)
            w.writeframes(b"\0\0" * need)
        return path, need / float(SILENCE_RATE)
    except Exception as e:
        notes.append("could not write the silent placeholder %s (%s) — the "
                     "unvoiced narration lines will not appear in the timeline "
                     "at all." % (path, e))
        return None, 0


def _stub_video(png, out, seconds, fps_k):
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", png,
             "-t", "%.3f" % seconds, "-r", str(round(float(fps_k))),
             "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
             out], check=True, capture_output=True)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# reel -> story
# --------------------------------------------------------------------------

def adapt(reel, opts, notes):
    r = reel["reel"]
    fk = fps_key(r.get("fps"), [])
    F = Frames(fk)
    W, H = int(r["width"]), int(r["height"])
    total_f = F.f(reel["clock"]["total_s"])
    by_id = {a["id"]: a for a in reel["assets"]}
    local_root = opts["local_root"]
    stub_dir = opts["stub_dir"] or local_root or "."

    story = {
        "project": r.get("title") or opts["fallback_title"],
        "event": "REAL",
        "frame_rate": F.key,
        "width": W, "height": H,
        "assets_root": reel.get("assets_root", ""),
        "beats": [],
        "connected": [],
        "_generated_by": "adapt.py — regenerate from reel.json, never hand-edit",
        "_clock": {k: reel["clock"].get(k)
                   for k in ("mode", "total_s", "rate_wps", "rate_source",
                             "note")},
    }
    if local_root:
        story["assets_root_local"] = local_root

    muted = 0
    cursor = 0
    for b in reel["beats"]:
        b0, b1 = F.f(b["t0"]), F.f(b["t1"])
        if b0 > cursor:
            story["beats"].append({
                "type": "gap", "duration": F.s(b0 - cursor),
                "name": "blank — nothing scheduled before %s" % b["id"]})
            cursor = b0
        layers = [l for _i, l in sorted(
            enumerate(b.get("layers") or []),
            key=lambda t: (t[1].get("z", 0), t[0]))]
        specs = []
        for l in layers:
            spec, was_muted = layer_spec(l, b, by_id, F, W, H, opts, notes,
                                         stub_dir)
            muted += was_muted
            if spec is None:
                # A storyboard element that cannot be represented is a build
                # FAILURE, never a silent omission — the approved storyboard
                # and the exported timeline must not describe different videos.
                opts.setdefault("_dropped", []).append(
                    "%s / %s could not be represented (see notes above)"
                    % (b["id"], l.get("id")))
            specs.append((l, spec))

        backing = None
        if specs:
            l0, s0 = specs[0]
            if s0 is not None and F.f(l0["t0"]) == b0 and F.f(l0["t1"]) == b1:
                backing = s0
                specs = specs[1:]
        if backing is None:
            backing = {"type": "gap", "duration": F.s(b1 - b0)}
        else:
            backing["duration"] = F.s(b1 - b0)

        backing["name"] = ("%s %s" % (b["id"], b.get("name") or "")).strip()
        if opts["markers"]:
            note = beat_note(b)
            if note:
                backing["note"] = note
            if b.get("moment"):
                backing["markers"] = [{"t": 0, "value": b["moment"]}]

        lane = 1
        overlays = []
        for l, spec in specs:
            if spec is None:
                continue
            spec["lane"] = lane
            lane += 1
            spec["offset"] = F.s(F.f(l["t0"]) - b0)
            spec["duration"] = F.s(F.f(l["t1"]) - F.f(l["t0"]))
            overlays.append(spec)
        if overlays:
            backing["overlays"] = overlays
        story["beats"].append(backing)
        cursor = b1

    if total_f > cursor:
        story["beats"].append({
            "type": "gap", "duration": F.s(total_f - cursor),
            "name": "blank — tail to clock.total_s"})
    elif total_f < cursor:
        notes.append("the beats run %.2fs past clock.total_s; the timeline is "
                     "as long as the beats." % F.s(cursor - total_f))

    story["connected"] = audio_clips(reel, by_id, F, opts, notes)
    stubs = opts.get("_stubs") or []
    if stubs:
        notes.append("wrote %d placeholder file(s) into %s — grey holes, not "
                     "red media. Drop the real renders in later under the same "
                     "filenames and nothing needs re-sequencing."
                     % (len(stubs), os.path.dirname(stubs[0]) or "."))
        if local_root and os.path.abspath(local_root) != os.path.abspath(
                reel.get("assets_root", "")):
            notes.append("the placeholders live here, not on the Mac. They must "
                         "also exist under %s or those clips import red."
                         % reel.get("assets_root"))
    if muted:
        notes.append("%d video layer(s) carry their own sound. Picture and "
                     "sound are stated separately in a reel, so their audio is "
                     "set to -60 dB rather than removed — where the reel wants "
                     "a clip's own sound it says so with a \"source\" lane. "
                     "One click in Final Cut brings any of them back." % muted)
    if not story["connected"]:
        notes.append("no audio in the reel — the timeline is silent.")

    # ---- parity: every storyboard element accounted for ----
    layers_in = sum(len(b.get("layers") or []) for b in reel["beats"])
    # a gap backing is structure (a beat with no full-span layer, or real
    # silence between beats) — layer representations are the non-gap backings
    # plus every overlay. layer_spec never emits a gap for a real layer.
    elements_out = sum((0 if bt.get("type") == "gap" else 1)
                       + len(bt.get("overlays") or [])
                       for bt in story["beats"])
    audio_in = len(list(_all_audio(reel)))
    story["_parity"] = {
        "layers_in": layers_in, "visual_elements_out": elements_out,
        "audio_lanes_in": audio_in,
        "connected_out": len(story["connected"]),
        "dropped": list(opts.get("_dropped") or [])}

    unvoiced = opts.get("_unvoiced") or []
    if unvoiced:
        # The badge travels in the project name, so it survives into Final Cut
        # itself and into report.html without either of them having to be told.
        story["project"] += " [UNVOICED]"
        story["unvoiced"] = {
            "lines": len(unvoiced),
            "seconds": round(sum(u["duration"] for u in unvoiced), 3),
            "clock_mode": reel["clock"].get("mode"),
            "windows": unvoiced,
            "note": ("no voice takes yet — every narration line is a silent "
                     "placeholder of its planned length. The timing is "
                     "estimated, not measured."),
        }
    return story


def badge_text(uv):
    """The UNVOICED badge, worded the same everywhere it appears."""
    return (
        "UNVOICED — %d narration line(s), %.1fs of speech, have no take yet.\n"
        "Each one is a silent placeholder holding its planned window open, so "
        "the\ntiming is real and visible in Final Cut — but it is ESTIMATED, "
        "not measured.\nRecord the voice, then `voice.py measure` and the clock "
        "swap in\n/real-storyboarding is what turns this into a measured cut."
        % (uv["lines"], uv["seconds"]))


def beat_note(b):
    bits = []
    if b.get("narration"):
        bits.append("narration: " + b["narration"])
    if b.get("moment"):
        bits.append("moment: " + b["moment"])
    src = b.get("source") or {}
    if src:
        bits.append("from %s" % "/".join(str(v) for v in src.values() if v))
    if _num(b.get("w0")) and _num(b.get("w1")):
        bits.append("words %s–%s" % (b["w0"], b["w1"]))
    for f in b.get("flags") or []:
        bits.append("flag %s: %s" % (f.get("code", "?"), f.get("msg", "")))
    return "  |  ".join(bits)


def layer_spec(l, b, by_id, F, W, H, opts, notes, stub_dir):
    """One reel layer -> one story element. Returns (spec|None, muted_count)."""
    kind = l["kind"]
    dur = F.s(F.f(l["t1"]) - F.f(l["t0"]))

    if kind == "text":
        # check() has already refused a missing/unknown style; the direct
        # lookup here means a silent mis-styling can never reappear.
        style = STYLES[l["style"]]
        spec = dict(style)
        spec["text"] = l["content"]
        spec["name"] = "%s — %s" % (l["id"], l["content"][:32])
        for k_reel, k_story in (("font_size", "font_size"),
                                ("position", "position"),
                                ("color", "color"), ("align", "align")):
            if l.get(k_reel) is not None:
                spec[k_story] = l[k_reel]
        return spec, 0

    asset = by_id.get(l.get("asset")) if l.get("asset") else None
    if asset is None:
        stub = l["stub"]
        w = int(stub.get("w") or W)
        h = int(stub.get("h") or H)
        if not stub.get("w"):
            notes.append("stub for %s declares no size — using the sequence "
                         "size %dx%d." % (l["id"], W, H))
        rel = stub["file"]
        # A movie stub gets half a second of handle so a later dissolve or a
        # two-frame hold has something to borrow. A still has infinite handles
        # already, so it gets exactly the window.
        want_video = os.path.splitext(rel)[1].lower() in VIDEO_EXTS
        length = dur + (0.5 if want_video else 0)
        if opts["stubs"]:
            written = make_stub(os.path.join(stub_dir, rel), w, h, l["id"],
                                stub.get("spec"), length, F.key, notes)
            if written is None:
                return None, 0
            root = opts["local_root"]
            if os.path.isabs(rel) or not root or \
                    os.path.abspath(stub_dir) != os.path.abspath(root):
                # written somewhere the assets_root doesn't cover: the only
                # honest src is the absolute path.
                rel = os.path.abspath(written)
            else:
                rel = os.path.relpath(written, root)
            opts.setdefault("_stubs", []).append(written)
        else:
            notes.append("--no-stubs: %s is referenced but not created. That "
                         "clip WILL import as red Missing Media." % rel)
        is_video = os.path.splitext(rel)[1].lower() in VIDEO_EXTS
        spec = {"type": "video" if is_video else "image", "src": rel,
                "name": "%s — STUB" % l["id"]}
        if is_video:
            spec["asset_duration"] = length
        else:
            spec["width"], spec["height"] = w, h
        return spec, 0

    src = asset["file"]
    name = "%s — %s" % (l["id"], (asset.get("catalog") or {}).get(
        "role", os.path.basename(src)))
    if kind == "image":
        spec = {"type": "image", "src": src, "name": name}
        if _num(asset.get("w")) and _num(asset.get("h")):
            spec["width"], spec["height"] = int(asset["w"]), int(asset["h"])
        else:
            notes.append("asset %s declares no w/h — Final Cut will be told it "
                         "is the sequence size %dx%d, and it will scale wrong "
                         "if it isn't." % (asset["id"], W, H))
    else:
        # A video layer is picture. The reel's "audio" array is the complete
        # statement of what is heard, so the clip's own sound is turned down
        # rather than left to double whatever the audio lanes already say —
        # when the reel does want a clip's own sound it says so with a
        # `source` lane pointing at that asset. -60 dB, not removed: one click
        # in Final Cut brings it back.
        spec = {"type": "video", "src": src, "name": name, "start": 0,
                "asset_duration": asset["dur_s"], "role": "effects",
                "volume_db": -60}
        muted = 1
    fit = l.get("fit")
    if fit == "fill" and _num(asset.get("w")) and _num(asset.get("h")) \
            and asset["h"]:
        # Final Cut conforms a mismatched still or clip to FIT by default.
        # Cover the frame instead by scaling out the difference in aspect.
        ratio = (asset["w"] / asset["h"]) / (W / H)
        extra = max(ratio, 1 / ratio)
        if abs(extra - 1) > 0.01:
            spec["transform"] = {"scale": round(extra, 4)}
    if l.get("chosen_by") == "claude" and opts["markers"]:
        spec["note"] = "picked by claude (confidence: %s)%s" % (
            l.get("confidence", "unstated"),
            "; also considered " + ", ".join(l["candidates"])
            if l.get("candidates") else "")
    return spec, (muted if kind == "video" else 0)


def unvoiced_clips(entries, F, opts, notes):
    """Narration lanes with no take yet -> silent placeholders.

    This is the normal pre-recording state, not an error. The creator sequences
    the whole reel on the estimated clock and records afterwards, so the export
    has to be buildable with no voice in it at all — that is the only way they
    find out a 60-second reel is 34 seconds over before spending an afternoon
    reading it aloud.

    Each line gets a real, silent, correctly-timed clip in the narration lane,
    named with the words that belong there. The timing is honest and visible in
    Final Cut; it is estimated, and the export says so.
    """
    if not entries:
        return []
    longest = max(F.s(F.f(e["t1"]) - F.f(e["t0"])) for e in entries)
    stub_dir = opts["stub_dir"] or opts["local_root"] or "."
    path, total = make_silence(os.path.join(stub_dir, SILENCE_FILE),
                               longest, notes)
    if path is None:
        return []
    root = opts["local_root"]
    if not root or os.path.abspath(stub_dir) != os.path.abspath(root):
        src = os.path.abspath(path)
    else:
        src = os.path.relpath(path, root)
    opts.setdefault("_stubs", []).append(path)
    out = []
    for e in sorted(entries, key=lambda x: x["t0"]):
        t0, t1 = F.f(e["t0"]), F.f(e["t1"])
        line = str(e.get("text") or "").strip()
        clip = {"type": "audio", "src": src, "lane": AUDIO_LANES["narration"],
                "role": AUDIO_ROLES["narration"], "offset": F.s(t0),
                "duration": F.s(t1 - t0), "start": 0,
                "asset_duration": total,
                "name": "%s — UNVOICED: %s" % (e.get("id", "narration"),
                                               line[:48])}
        if opts["markers"]:
            clip["note"] = "UNVOICED — no take covers this line yet: " + line
        out.append(clip)
        opts.setdefault("_unvoiced", []).append(
            {"id": e.get("id"), "t0": F.s(t0), "t1": F.s(t1),
             "duration": F.s(t1 - t0), "text": line})
    return out


def audio_clips(reel, by_id, F, opts, notes):
    """Every audio entry -> connected clips, merged per source, with ducking.

    Consecutive windows on the same asset are one clip reading continuously,
    not several: a narration master cut into per-beat windows would otherwise
    arrive as a pile of splices nobody asked for. Where the duck level changes
    across a merged clip, it becomes a stepped volume envelope on one clip —
    still one editable element, still one handle to drag.

    Narration lanes with no take yet are NOT merged and NOT skipped: each one
    becomes its own silent placeholder holding its own window open, named with
    the line that is meant to go there.
    """
    groups, unvoiced = {}, []
    for e, where in _all_audio(reel):
        # scope 0 = declared globally in "connected", 1 = declared on a beat.
        # At the same instant the beat's level wins: it is the more specific
        # statement about what that moment sounds like.
        scope = 0 if where.startswith("connected") else 1
        aid = e.get("asset")
        if not aid:
            unvoiced.append(e)
            continue
        kind, _n = norm_audio_kind(e.get("kind"), by_id.get(aid))
        groups.setdefault((aid, kind), []).append((scope, e))

    out = unvoiced_clips(unvoiced, F, opts, notes)
    lane_of, next_free = {}, -5
    for (aid, kind), pairs in groups.items():
        pairs.sort(key=lambda p: (p[1]["t0"], p[0]))
        entries = [e for _s, e in pairs]
        asset = by_id[aid]
        lane = AUDIO_LANES.get(kind)
        if lane is None:
            if kind not in lane_of:
                lane_of[kind] = next_free
                next_free -= 1
                notes.append("audio kind %r has no standard lane — putting it "
                             "on lane %d." % (kind, lane_of[kind]))
            lane = lane_of[kind]
        role = AUDIO_ROLES.get(kind, "dialogue")

        runs, cur, cur_end = [], None, None
        for e in entries:
            if cur is not None and F.f(e["t0"]) <= cur_end + 1:
                cur.append(e)
                cur_end = max(cur_end, F.f(e["t1"]))
            else:
                cur = [e]
                cur_end = F.f(e["t1"])
                runs.append(cur)
        base = F.f(runs[0][0]["t0"])
        for run in runs:
            r0 = F.f(run[0]["t0"])
            r1 = max(F.f(e["t1"]) for e in run)
            src_in = F.s(r0 - base)
            dur = F.s(r1 - r0)
            if src_in + dur > asset["dur_s"] + 0.05:
                raise Refusal(
                    "audio %s reads %.2f–%.2fs of %s but that file is only "
                    "%.2fs long. Windows on one asset are read continuously "
                    "from its first use; if this asset is meant to restart, "
                    "give the entry an explicit \"src_in\"."
                    % (run[0].get("id", aid), src_in, src_in + dur,
                       asset["file"], asset["dur_s"]))
            if run[0].get("src_in") is not None:
                src_in = float(run[0]["src_in"])
            clip = {"src": asset["file"], "lane": lane, "role": role,
                    "offset": F.s(r0), "duration": dur, "start": src_in,
                    "asset_duration": asset["dur_s"],
                    "name": "%s — %s" % (kind, os.path.basename(asset["file"]))}
            if asset.get("kind") == "video":
                # the sound of a movie, not a second copy of its picture
                clip["type"] = "video"
                clip["src_enable"] = "audio"
                clip["name"] += " (audio only)"
            note = run[0].get("note") or run[0].get("why")
            if note and opts["markers"]:
                clip["note"] = note
            steps = {}
            for e in run:  # later entry at the same frame wins (see above)
                steps[F.f(e["t0"])] = float(e.get("duck_db") or 0)
            levels = []
            for f, v in sorted(steps.items()):
                if not levels or levels[-1][1] != v:
                    levels.append((f, v))
            if len(levels) == 1:
                if levels[0][1]:
                    clip["volume_db"] = levels[0][1]
            else:
                kfs, prev = [], None
                for f, v in levels:
                    t = F.s(f - r0)
                    if prev is not None:
                        kfs.append({"t": max(0, round(t - F.one, 6)),
                                    "value": prev})
                    kfs.append({"t": t, "value": v})
                    prev = v
                clip["ducking"] = kfs
            out.append(clip)
    out.sort(key=lambda c: (-c["lane"], c["offset"]))
    return out


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    reel_path = argv[1]
    out_path = argv[argv.index("-o") + 1] if "-o" in argv else "story.json"
    opts = {
        "stubs": "--no-stubs" not in argv,
        "markers": "--no-markers" not in argv,
        "local_root": (argv[argv.index("--assets-root-local") + 1]
                       if "--assets-root-local" in argv else None),
        "stub_dir": (argv[argv.index("--stub-dir") + 1]
                     if "--stub-dir" in argv else None),
        "fallback_title": os.path.splitext(os.path.basename(reel_path))[0],
    }
    quiet = "--quiet" in argv

    try:
        reel = json.load(open(reel_path))
    except Exception as e:
        print("REFUSED — could not read %s: %s" % (reel_path, e))
        return 2
    if opts["local_root"] is None:
        opts["local_root"] = reel.get("assets_root_local") if isinstance(
            reel, dict) else None
    if opts["local_root"] and not os.path.isdir(opts["local_root"]):
        if os.path.isdir(reel.get("assets_root") or ""):
            opts["local_root"] = reel["assets_root"]
        else:
            opts["local_root"] = None

    problems, notes = check(reel, opts["local_root"])
    if problems:
        print("REFUSED — %s cannot be compiled as it stands. %d problem%s:\n"
              % (os.path.basename(reel_path), len(problems),
                 "" if len(problems) == 1 else "s"))
        for i, p in enumerate(problems, 1):
            print(_wrap(i, p))
        print("\nNothing was written. These are storyboarding decisions: fix "
              "them in /real-storyboarding and re-run. This step does not "
              "invent times, assets or placements.")
        return 2

    try:
        story = adapt(reel, opts, notes)
    except Refusal as e:
        print("REFUSED — %s cannot be compiled as it stands. 1 problem:\n"
              % os.path.basename(reel_path))
        print(_wrap(1, str(e)))
        print("\nNothing was written.")
        return 2

    with open(out_path, "w") as f:
        json.dump(story, f, indent=2)
    if not quiet:
        n_beats = len(story["beats"])
        print("wrote %s — %d spine item(s), %d connected clip(s), %.2fs @ %s fps"
              % (out_path, n_beats, len(story["connected"]),
                 reel["clock"]["total_s"], story["frame_rate"]))
        if story.get("unvoiced"):
            print("\n" + badge_text(story["unvoiced"]))
        par = story.get("_parity") or {}
        print("parity: %d layer(s) in -> %d visual element(s) out · "
              "%d audio lane(s) in -> %d connected clip(s) out"
              % (par.get("layers_in", 0), par.get("visual_elements_out", 0),
                 par.get("audio_lanes_in", 0), par.get("connected_out", 0)))
        if par.get("dropped"):
            for d in par["dropped"]:
                print("ERROR dropped: " + d)
            print("REFUSING — the storyboard and this timeline would describe "
                  "different videos. Fix the causes above and re-run.")
            return 1
        if notes:
            print("\n%d thing%s worth knowing:\n"
                  % (len(notes), "" if len(notes) == 1 else "s"))
            for i, n in enumerate(notes, 1):
                print(_wrap(i, n))
    return 0


def _wrap(i, text, width=78):
    import textwrap
    head = "  %2d. " % i
    return textwrap.fill(" ".join(str(text).split()), width=width,
                         initial_indent=head,
                         subsequent_indent=" " * len(head))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
