#!/usr/bin/env python3
"""build.py — assemble reel.json, the one canonical description of the reel.

    python3 build.py build notebook.json clock.json bindings.json -o reel.json \
        [--assets-root "/Users/…/Reel Project"] [--stubs-dir stubs] [--fps 30]
    python3 build.py retime reel.json clock.json -o reel.json
    python3 build.py validate reel.json

`build` merges the parse (what the creator wrote), the clock (when each word
happens and what each component anchors to) and the bindings (which real file,
or which stub) into `references/reel-schema.md`. `retime` re-derives seconds
after the clock changes — anchors do not move, so re-timing never re-plans.

Stub placeholder files are written with PIL when `--stubs-dir` is given: a real
image at the exact duration and resolution, with a stable filename, so the
export imports a complete timeline with visible grey holes instead of red
missing media, and the real render drops in later without re-sequencing.

Stdlib + PIL only.
"""

from real_core import read_json, write_json
from real_core import transition_problems, transition_overlap  # noqa: E402
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from real_core import refit_beat, words_of  # noqa: E402
from real_core import settle_holds  # noqa: E402

ASPECTS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080),
           "4:5": (1080, 1350), "5:4": (1350, 1080), "2:3": (1080, 1620),
           "3:2": (1620, 1080), "4:3": (1440, 1080), "3:4": (1080, 1440)}

MOMENT_RE = re.compile(r"[^.!?]*\b(must|has to|have to|needs to|cannot|can't|"
                       r"do not|don't)\b[^.!?]*[.!?]", re.I)


def dims(aspect):
    if aspect in ASPECTS:
        return ASPECTS[aspect]
    m = re.match(r"^\s*(\d+)\s*[:x]\s*(\d+)\s*$", str(aspect or ""))
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a and b:
            base = 1080
            return (base, int(round(base * b / a))) if a <= b else (int(round(base * a / b)), base)
    return ASPECTS["9:16"]


def word_text_of(C, i):
    """The textual identity of anchor word i. The word/phrase is the anchor's
    real identity; the timestamp is derived from the best available timing
    evidence and may change — the text never silently does."""
    if i is None:
        return None
    for w in C.get("words", []):
        if w.get("i") == i:
            return w.get("w")
    return None


def moment_of(note):
    m = MOMENT_RE.search(note or "")
    return m.group(0).strip() if m else None


AUDIO_KINDS = ("narration", "source", "bed", "sfx")


def audio_kind(comp_text, hint=None, own_sound=False):
    """narration | source | bed | sfx.

    `source` is an asset's OWN audio — a video clip played for its sound, which
    is what an `<audio of …>` parallel to the video it describes means. It is a
    different thing from a bed: a bed is music or ambience laid *under* the
    narration and ducks; a source lane is the point of the shot and does not.
    """
    if hint in AUDIO_KINDS:
        return hint
    if own_sound:
        return "source"
    t = (comp_text or "").lower()
    if any(k in t for k in ("music", "theme", "bed", "score", "ambience", "under")):
        return "bed"
    return "sfx"


def is_connected(comp):
    t = (comp.get("text") or "").lower()
    tags = [x.lower() for x in comp.get("tags") or []]
    return ("bed" in tags or "throughout" in t or "under the whole" in t
            or "whole reel" in t or "across the reel" in t)


def index_components(nb):
    out = {}
    for cell in nb.get("cells", []):
        for g in cell.get("groups", []):
            for c in g["components"]:
                out[c["id"]] = (cell, g, c)
    return out


def render_silence(path, dur_s, rate=48000):
    """A sound that has to be made still needs a file of the right length, so
    the export lands a silent clip of exactly that duration rather than a hole."""
    import wave
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    n = max(1, int(rate * max(0.01, dur_s)))
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(b"\x00\x00" * n)
    return True


def render_stub(path, w, h, title, spec, dur_s):
    """A real placeholder file at the exact size — grey, hatched, and legible,
    so a hole in the timeline announces itself instead of hiding."""
    if path.lower().endswith(".wav"):
        try:
            return render_silence(path, dur_s)
        except Exception as exc:
            sys.stderr.write("could not write %s (%s)\n" % (path, exc))
            return False
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:
        sys.stderr.write("PIL unavailable (%s); stub file not written: %s\n"
                         % (exc, path))
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img = Image.new("RGB", (w, h), (58, 60, 66))
    d = ImageDraw.Draw(img)
    step = max(24, w // 22)
    for x in range(-h, w, step * 2):
        d.line([(x, h), (x + h, 0)], fill=(70, 72, 79), width=step // 2)
    pad = max(24, w // 18)
    d.rectangle([pad, pad, w - pad, h - pad], outline=(150, 154, 162), width=3)

    def font(size):
        from PIL import ImageFont
        for cand in ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                     "/System/Library/Fonts/Helvetica.ttc",
                     "C:/Windows/Fonts/arialbd.ttf"):
            if os.path.exists(cand):
                try:
                    return ImageFont.truetype(cand, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    big, mid, small = font(max(28, w // 22)), font(max(22, w // 30)), font(max(18, w // 40))

    def wrap(text, per_line):
        words, lines, cur = str(text).split(), [], ""
        for word in words:
            if len(cur) + len(word) + 1 > per_line:
                lines.append(cur)
                cur = word
            else:
                cur = (cur + " " + word).strip()
        if cur:
            lines.append(cur)
        return lines

    step_y = max(26, w // 28)
    body = wrap(spec, 34)[:9]
    y = h // 2 - (len(body) * step_y) // 2 - 3 * step_y
    d.text((pad + 20, y), "TO BUILD", fill=(255, 214, 120), font=big)
    y += int(step_y * 1.5)
    d.text((pad + 20, y), title[:40], fill=(232, 236, 243), font=mid)
    y += int(step_y * 1.5)
    for line in body:
        d.text((pad + 20, y), line, fill=(206, 212, 222), font=mid)
        y += step_y
    y += step_y
    d.text((pad + 20, y), "%.2fs · %dx%d" % (dur_s, w, h),
           fill=(160, 166, 176), font=small)
    img.save(path)
    return True


def assemble(nb, C, BND, args):
    aspect = C.get("aspect") or nb.get("meta", {}).get("aspect") or "9:16"
    W, H = dims(aspect)
    comps = index_components(nb)
    bindings = BND.get("bindings", {})
    assets = {a["id"]: a for a in BND.get("assets", [])}
    placements = {}
    for p in C["placements"]:
        placements.setdefault(p["beat"], []).append(p)

    used_assets, questions, unbound, stub_files = set(), [], [], []

    reel_assets = []
    for a in BND.get("assets", []):
        reel_assets.append({
            "id": a["id"], "file": a["file"], "kind": a["kind"],
            "dur_s": a.get("dur"), "w": a.get("w"), "h": a.get("h"),
            "fps": a.get("fps"), "rotation": a.get("rotation", 0),
            "exists": a.get("exists", True),
            "catalog": {"role": a.get("role", ""), "beat": a.get("beat", ""),
                        "shows": a.get("shows", ""), "use": a.get("use", ""),
                        "binds_to": a.get("binds_to", ""),
                        "tags": a.get("tags", []),
                        "excerpt": a.get("excerpt", "")},
        })

    beats = []
    for b in C["beats"]:
        ps = sorted(placements.get(b["id"], []), key=lambda p: p["order"])
        layers, audio, flags = [], [], []
        zi, ai = 0, 0
        # Assets that appear in this beat as a moving picture. An audio lane
        # bound to one of them is that clip's OWN sound, not a second asset.
        beat_video_assets = {bindings.get(p["component"], {}).get("asset")
                             for p in ps if p["type"] == "video"} - {None}
        for p in ps:
            comp = comps.get(p["component"], (None, None, {}))[2]
            bind = bindings.get(p["component"], {})
            asset = bind.get("asset")
            if asset:
                used_assets.add(asset)

            if p["lane"] == "narration":
                ai += 1
                audio.append({
                    "id": "%s.A%d" % (b["id"], ai), "kind": "narration",
                    "asset": asset, "t0": p["t0"], "t1": p["t1"],
                    "anchor_word": p["anchor_word"],
                    "anchor_text": word_text_of(C, p["anchor_word"]), "offset_ms": p["offset_ms"],
                    "source_component": p["component"],
                    "text": comp.get("text", ""),
                    "chosen_by": "claude", "confidence": bind.get("confidence", "low"),
                    "candidates": [c["asset"] for c in bind.get("candidates", [])],
                    "why": bind.get("why", ""),
                })
                if not asset:
                    flags.append({"code": "no-take", "layer": None,
                                  "msg": "no voice take bound to this line — the "
                                         "clock is ESTIMATED here"})
                continue

            if p["lane"] == "audio":
                if is_connected(comp):
                    # audio that runs under the whole reel is one connected span
                    # (built below), not also a lane inside the beat it was written in
                    continue
                ai += 1
                own = bool(asset) and (assets.get(asset, {}).get("kind") == "video") \
                    and asset in beat_video_assets
                entry = {
                    "id": "%s.A%d" % (b["id"], ai),
                    "kind": audio_kind(comp.get("text"),
                                       hint=bind.get("audio_kind"),
                                       own_sound=own),
                    "asset": asset, "t0": p["t0"], "t1": p["t1"],
                    "anchor_word": p["anchor_word"],
                    "anchor_text": word_text_of(C, p["anchor_word"]), "offset_ms": p["offset_ms"],
                    "source_component": p["component"],
                    "note": comp.get("text", ""),
                    "chosen_by": bind.get("chosen_by", "claude"),
                    "confidence": bind.get("confidence", "low"),
                    "candidates": [c["asset"] for c in bind.get("candidates", [])],
                    "why": bind.get("why", ""),
                }
                for key in ("src_in", "src_out", "temporal_evidence", "source_video_component"):
                    if key in bind:
                        entry[key] = bind[key]
                if entry["kind"] == "bed":
                    entry["duck_db"] = -12
                elif entry["kind"] == "source":
                    # a demo's own sound is the argument; it does not duck under
                    # the narration unless the creator says so
                    entry["duck_db"] = 0
                if "full volume" in (comp.get("text") or "").lower():
                    entry["duck_db"] = 0
                if bind.get("stub"):
                    entry["stub"] = dict(bind["stub"],
                                         dur_s=round(p["t1"] - p["t0"], 3))
                    stub_files.append((entry["stub"], entry, b))
                    flags.append({"code": "stub", "layer": entry["id"],
                                  "msg": "sound that has to be made or found: %s"
                                         % comp.get("text", "")[:70]})
                    questions.append({
                        "beat": b["id"], "layer": entry["id"], "code": "make",
                        "msg": "no sound for %s — silent stub emitted at %.2fs "
                               "(%s, %.2fs). This is a numbered request: record "
                               "it, find it or make it."
                               % (comp.get("text", "")[:60], p["t0"],
                                  entry["stub"]["file"], entry["stub"]["dur_s"])})
                audio.append(entry)
                continue

            zi += 1
            lid = "%s.L%d" % (b["id"], zi)
            layer = {
                "id": lid, "z": zi - 1,
                "kind": comp.get("type", p["type"]),
                "asset": asset,
                "anchor_word": p["anchor_word"],
                "anchor_text": word_text_of(C, p["anchor_word"]), "offset_ms": p["offset_ms"],
                "t0": p["t0"], "t1": p["t1"],
                "fit": "fill" if p["base"] else "fit",
                "chosen_by": bind.get("chosen_by", "claude"),
                "confidence": bind.get("confidence", "low"),
                "candidates": [c["asset"] for c in bind.get("candidates", [])],
                "candidates_why": {c["asset"]: c["why"]
                                   for c in bind.get("candidates", [])},
                "why": bind.get("why", ""),
                "source_component": p["component"],
                "source_text": comp.get("text", ""),
                "placement": p["placement"],
                "dur_source": p["dur_source"],
                "essential": bool(comp.get("essential")),
                "unsure": bool(comp.get("unsure")),
                "base": p["base"],
                "snapped": p.get("snapped", False),
            }
            for key in ("src_in", "src_out", "temporal_evidence", "source_video_component"):
                if key in bind:
                    layer[key] = bind[key]
            source_candidates = [c for c in bind.get("candidates", [])
                                 if "source_in" in c and "source_out" in c]
            if source_candidates:
                layer["source_candidates"] = source_candidates
            if "src_out" in layer and layer["t1"] - layer["t0"] > layer["src_out"] - layer.get("src_in", 0) + 1e-6:
                flags.append({"code": "source-too-short", "layer": lid,
                              "msg": "the selected source event is shorter than this placement; shorten the placement or choose another event"})
            if p["dur_source"] == "explicit":
                # Keep the requested duration separately from its clipped span.
                layer["dur_s"] = p["dur_s"]
            if layer["kind"] == "text":
                layer["content"] = comp.get("content") or comp.get("text", "")
                if not asset:
                    # on-screen text IS its own content: no asset, and no stub
                    # either, so it must not read as an unbound layer
                    layer.pop("asset", None)
                # a text element must reach the handoff explicitly classified:
                # title | caption | subtitle (the export styles each differently
                # and refuses an unclassified one). The heuristic below is a
                # STARTING GUESS, flagged for the creator to confirm or change
                # in the tracks page — never a silent decision.
                layer["style"] = ("title" if len(layer["content"].split()) <= 4
                                  and layer["content"].isupper() else "caption")
                layer["style_by"] = "claude"
                flags.append({"code": "text-type", "layer": lid,
                              "msg": "classified as %r by heuristic — confirm "
                                     "title / caption / subtitle in the tracks "
                                     "page" % layer["style"]})
            if bind.get("stub"):
                st = dict(bind["stub"])
                st.update({"w": W, "h": H, "dur_s": round(p["t1"] - p["t0"], 3)})
                layer["stub"] = st
                layer["asset"] = None
                unbound.append(lid)
                stub_files.append((st, layer, b))
                questions.append({
                    "beat": b["id"], "layer": lid, "code": "make",
                    "msg": "no asset for %s — stub emitted at %.2fs (%s, %.2fs, "
                           "%dx%d). This is a numbered request: film it, find it "
                           "or build it." % (comp.get("text", "")[:60], p["t0"],
                                             st["file"], st["dur_s"], W, H)})
                flags.append({"code": "stub", "layer": lid,
                              "msg": "has to be built: %s" % st["spec"][:80]})
            elif not asset and layer["kind"] != "text":
                unbound.append(lid)
                flags.append({"code": "unbound", "layer": lid,
                              "msg": "nothing bound here"})

            if layer["confidence"] == "low" and layer["asset"]:
                n = len(layer["candidates"])
                flags.append({"code": "low-confidence", "layer": lid,
                              "msg": ("%d other assets could fit; picked %s — %s"
                                      % (n, layer["asset"], layer["why"][:90]))
                              if n else "one plausible asset, but the evidence is "
                                        "thin — confirm it"})
            if layer["unsure"]:
                flags.append({"code": "creator-unsure", "layer": lid,
                              "msg": "the creator marked this `?` — they want options"})
            if layer["snapped"]:
                flags.append({"code": "snapped", "layer": lid,
                              "msg": "landed within 0.3s of the cue before it, so "
                                     "both were snapped to the same frame"})
            if p["dur_source"] == "assumed":
                flags.append({"code": "assumed-duration", "layer": lid,
                              "msg": "no duration anywhere for this — %.1fs is an "
                                     "ASSUMPTION, not an estimate" % layer["t1"]})
            if layer["kind"] == "unknown":
                flags.append({"code": "unknown-type", "layer": lid,
                              "msg": "could not type this component: %s"
                                     % layer["source_text"][:70]})
            a = assets.get(asset or "")
            if a and a.get("w") and a.get("h") and layer["base"]:
                want, got = W / H, a["w"] / a["h"]
                if abs(want - got) / want > 0.25:
                    flags.append({"code": "aspect-mismatch", "layer": lid,
                                  "msg": "%s is %dx%d in a %s reel — it will be "
                                         "cropped or letterboxed"
                                         % (asset, a["w"], a["h"], aspect)})
            layers.append(layer)

        beat = {
            "id": b["id"], "name": b["name"],
            "t0": b["t0"], "t1": b["t1"], "w0": b["w0"], "w1": b["w1"],
            "narration": b["narration"],
            "source": {"cell": b["cell"], "component": b["component"]},
            "layers": layers, "audio": audio,
            "held_to": b.get("held_to"),
            "note": b.get("note", ""),
            "flags": flags,
        }
        mom = moment_of(b.get("note"))
        if mom:
            beat["moment"] = mom
        if not layers:
            beat["flags"].append({
                "code": "blank", "layer": None,
                "msg": "nothing on screen for this beat. A blank is deliberate or "
                       "it is a defect — give it a reason or fill it"})
        beats.append(beat)

    # connected spans: audio the creator described as running under the reel
    connected = []
    for cid, (cell, g, comp) in comps.items():
        if comp["type"] == "audio" and is_connected(comp):
            bnd = bindings.get(cid, {})
            # a span is one of the four audio kinds like any lane (the schema
            # has no fifth kind): music or ambience under the whole reel is a
            # bed and ducks; a clip's own sound running across the reel is a
            # source lane and does not
            kind = audio_kind(comp.get("text"), hint=bnd.get("audio_kind"))
            connected.append({
                "id": "X%d" % (len(connected) + 1), "kind": kind,
                "asset": bnd.get("asset"), "t0": 0.0, "t1": C["total_s"],
                "duck_db": 0 if kind == "source" else -14,
                "source_component": cid, "note": comp["text"]})
            if bnd.get("asset"):
                used_assets.add(bnd["asset"])

    if args.stubs_dir:
        for st, layer, b in stub_files:
            st["file"] = os.path.join(args.stubs_dir, os.path.basename(st["file"]))
            ok = render_stub(st["file"], W, H,
                             "%s %s" % (b["id"], layer["id"]),
                             st["spec"], st["dur_s"])
            st["status"] = "placeholder" if ok else "todo"

    # Unused is computed against what is actually IN the reel, not against what
    # the binder matched — a file bound only inside an unselected variant is not
    # in this reel, and saying otherwise hides it.
    alt_cells = {a["cell"] for a in C.get("alternates", [])}
    alt_bound = {}
    for cid, bnd in bindings.items():
        if bnd.get("asset") and bnd.get("cell") in alt_cells:
            alt_bound[bnd["asset"]] = bnd["cell"]
    unused = [a["id"] for a in BND.get("assets", []) if a["id"] not in used_assets]
    for a in unused:
        why = BND.get("unused_reasons", {}).get(a, "")
        if a in alt_bound:
            why = ("bound only inside the unselected variant (%s) — it comes "
                   "back if that variant is chosen" % alt_bound[a])
        questions.append({"beat": None, "layer": None, "code": "unused",
                          "msg": "%s (%s) is placed nowhere — %s"
                                 % (a, assets.get(a, {}).get("name", ""), why)})
    for w in C.get("warnings", []):
        questions.append({"beat": None, "layer": None, "code": "notebook",
                          "msg": str(w)})
    for w in BND.get("warnings", []):
        questions.append({"beat": None, "layer": None, "code": "binding",
                          "msg": str(w)})
    for i, q in enumerate(questions, 1):
        q["id"] = "Q%d" % i

    # ---- unresolved technical properties, surfaced in editorial language ----
    # The creator never needed to know fps/dimensions/rotation to storyboard;
    # now that the reel is concrete, anything still unknown is raised HERE,
    # before the handoff — /real-compile refuses to guess these.
    unresolved_specs = []
    used_ids = used_assets
    for a2 in reel_assets:
        if a2["id"] not in used_ids:
            continue
        miss = []
        if a2["kind"] in ("video", "audio") and not a2.get("dur_s"):
            miss.append("how long it runs")
        if a2["kind"] in ("video", "image") and not (a2.get("w") and a2.get("h")):
            miss.append("its frame size")
        if a2["kind"] == "video" and a2.get("rotation") is None:
            miss.append("whether it plays the right way up")
        if miss:
            unresolved_specs.append({"asset": a2["id"], "file": a2["file"],
                                     "missing": miss})
            questions.append({
                "beat": None, "layer": None, "code": "specs", "id": "Q%d" % (len(questions) + 1),
                "msg": "%s (%s): before compiling we still need to know %s — "
                       "probing the file settles it (no technical knowledge "
                       "needed from you)."
                       % (a2["id"], os.path.basename(a2["file"] or ""),
                          " and ".join(miss))})

    reel = {
        "version": "1.0",
        "reel": {"title": C.get("reel") or nb.get("meta", {}).get("reel", ""),
                 "aspect": aspect, "width": W, "height": H,
                 "fps": args.fps},
        "clock": {
            "pause_policy": C.get("pause_policy") or "blank",
            "mode": C.get("mode", "estimated"),
            "rate_wps": C.get("rate_wps"),
            "rate_source": C.get("rate_source"),
            "total_s": C.get("total_s"),
            "target_s": C.get("target_s"),
            "note": C.get("note"),
        },
        "assets_root": args.assets_root or BND.get("assets_root", ""),
        "assets_root_local": args.assets_root_local or BND.get("assets_root", ""),
        "assets": reel_assets,
        "beats": beats,
        "connected": connected,
        "alternates": C.get("alternates", []),
        "open": {
            "unbound_layers": unbound,
            "unused_assets": unused,
            "unresolved_specs": unresolved_specs,
            "questions": questions,
        },
    }
    if C.get("estimated_total_s"):
        reel["clock"]["estimated_total_s"] = C["estimated_total_s"]
    return reel


def clamp_held_cuts(reel):
    """Pause policy `hold`: a shot held through the pause cannot outlast its
    footage. When the base clip runs out before the planned cut, the cut moves
    earlier to where the footage ends, provided that is still after the line
    finishes; the next beat starts there. Each move is flagged. A clip too short
    to cover its own line is left alone, and /real-compile refuses it, because
    that one needs a person (journal 003)."""
    if (reel.get("clock") or {}).get("pause_policy") != "hold":
        return 0
    assets = {a["id"]: a for a in reel.get("assets", [])}
    beats = reel.get("beats", [])
    moved = 0
    for k, b in enumerate(beats):
        base = next((l for l in b.get("layers", []) if l.get("kind") == "video"
                     and l.get("base") and abs(l["t1"] - b["t1"]) < 1e-6), None)
        if not base or not base.get("asset"):
            continue
        dur = (assets.get(base["asset"]) or {}).get("dur_s")
        if dur:
            dur = min(dur, base.get("src_out", dur)) - base.get("src_in", 0)
        if not dur or dur <= 0 or base["t1"] - base["t0"] <= dur + 1e-6:
            continue
        narr = [a["t1"] for a in b.get("audio", []) if a.get("kind") == "narration"]
        line_end = max(narr) if narr else b["t0"]
        cut = round(base["t0"] + dur - 0.001, 3)   # stay strictly inside the file
        if cut < line_end:
            continue
        old = b["t1"]
        for l in b.get("layers", []) + b.get("audio", []):
            if l.get("kind") == "narration":
                continue
            if abs(l.get("t1", 0) - old) < 1e-6 or l.get("t1", 0) > cut:
                l["t1"] = cut
        b["t1"] = b["held_to"] = cut
        b.setdefault("flags", []).append({
            "code": "cut-moved", "layer": base["id"],
            "msg": "the footage ends %.3fs before the planned cut, so the cut moved "
                   "earlier to %.3fs (still after the line ends)" % (old - cut, cut)})
        if k + 1 < len(beats):
            nb = beats[k + 1]
            for l in nb.get("layers", []):
                if l.get("base") and abs(l["t0"] - nb["t0"]) < 1e-6:
                    l["t0"] = cut
            nb["t0"] = cut
        moved += 1
    return moved


# ------------------------------------------------------------------ retime

PRESERVE_FIELDS = ("asset", "anchor_word", "anchor_text", "offset_ms", "fit", "hold_to_next",
                   "style", "style_by", "content", "stagger", "transform", "opacity", "fade_in", "fade_out", "stroke_color", "shadow", "shadow_color", "shadow_offset", "shadow_blur", "font", "font_face", "stroke_width", "font_size", "position", "color", "align", "t0", "t1", "src_in", "src_out", "temporal_evidence", "source_video_component")


def preserve_creator(reel, old_reel):
    """Carry every creator-chosen placement from an earlier reel into a rebuilt
    one, matched by layer/audio id. A rebuild (new bindings, new notebook pass)
    must never silently rebind what the creator explicitly chose — Issue: a
    creator-selected placement is authoritative until the creator changes it.
    Conflicts (the chosen asset no longer exists in the new reel) are flagged
    ONCE as questions, and the creator decides."""
    by_id = {a["id"] for a in reel.get("assets", [])}
    new_items = {}
    for b in reel.get("beats", []):
        for it in (b.get("layers") or []) + (b.get("audio") or []):
            new_items[it["id"]] = (it, b)
    kept, conflicts = 0, []
    for b in old_reel.get("beats", []):
        for it in (b.get("layers") or []) + (b.get("audio") or []):
            if it.get("chosen_by") != "creator":
                continue
            tgt = new_items.get(it["id"])
            if tgt is None:
                conflicts.append("%s: creator-chosen %s no longer exists in the "
                                 "rebuilt reel" % (b.get("id"), it["id"]))
                continue
            t, tb = tgt
            if it.get("asset") and it["asset"] not in by_id:
                conflicts.append("%s: creator chose asset %s, which is not in "
                                 "the rebuilt catalogue — kept the new binding; "
                                 "your call" % (it["id"], it["asset"]))
                continue
            for key in ("src_in", "src_out", "temporal_evidence", "source_video_component"):
                if key not in it:
                    t.pop(key, None)
            for k in PRESERVE_FIELDS:
                if it.get(k) is not None:
                    t[k] = it[k]
            t["chosen_by"] = "creator"
            t["confidence"] = "high"
            t["why"] = it.get("why", "the creator chose this")
            t.pop("source_candidates", None)
            t.pop("candidates", None)
            t.pop("candidates_why", None)
            tb["flags"] = [f for f in tb.get("flags", [])
                           if f.get("layer") != t["id"]]
            kept += 1
    # a dissolve the creator asked for is a decision on the beat, not on a layer
    new_beats = {b["id"]: b for b in reel.get("beats", [])}
    for b in old_reel.get("beats", []):
        tr = b.get("transition_in")
        if tr and tr.get("chosen_by") == "creator":
            if b["id"] in new_beats:
                new_beats[b["id"]]["transition_in"] = dict(tr)
                kept += 1
            else:
                conflicts.append("%s: the creator's dissolve into this beat has no beat "
                                 "to land on in the rebuilt reel" % b["id"])
    qs = reel["open"]["questions"]
    for c in conflicts:
        qs.append({"beat": None, "layer": None, "code": "preserve",
                   "id": "Q%d" % (len(qs) + 1), "msg": c})
    return kept, conflicts


def retime(reel, C):
    """Seconds change, anchors do not. Layers the creator has since moved keep
    their own anchor and length; everything else takes the clock's derivation."""
    words = {w["i"]: w for w in C["words"]}
    cut = (C.get("rates") or {}).get("cut_into_word", 0.4)
    # Match a layer back to its plan by the notebook component it came from —
    # layer ids are renumbered per beat, component ids are content-addressed and
    # stable, so this is the join that survives revisions.
    byid = {(p["beat"], p["component"]): p for p in C["placements"]}
    bybeat = {b["id"]: b for b in C["beats"]}
    moved = 0

    def cut_point(i, beat):
        w = words.get(i)
        if not w:
            return None
        if i == beat.get("w0") and not beat.get("wordless"):
            return (w["start"])      # first word: start with the line
        return (w["start"] + cut * max(0.0, w["end"] - w["start"]))

    for beat in reel["beats"]:
        cb = bybeat.get(beat["id"])
        if cb:
            beat["t0"], beat["t1"] = cb["t0"], cb["t1"]
            beat["held_to"] = cb.get("held_to")
        for item in beat["layers"] + beat["audio"]:
            p = byid.get((beat["id"], item.get("source_component")))
            same = (p and p["anchor_word"] == item.get("anchor_word")
                    and (p.get("offset_ms") or 0) == (item.get("offset_ms") or 0))
            if same:
                item["t0"], item["t1"] = p["t0"], p["t1"]
            else:
                length = max(0.0, item.get("t1", 0) - item.get("t0", 0))
                t0 = cut_point(item.get("anchor_word", beat["w0"]), cb or beat)
                if t0 is None:
                    continue
                t0 = (t0 + (item.get("offset_ms") or 0) / 1000.0)
                # an explicit duration is the creator's number: keep it
                # rather than a length that an earlier clock may have clipped
                if p and p.get("dur_source") == "explicit" and p.get("dur_s"):
                    length = p["dur_s"]
                item["t0"] = t0
                item["t1"] = (min(t0 + length, beat["t1"]))
                moved += 1
        refit_beat(beat)
    for x in reel.get("connected", []):
        x["t1"] = C["total_s"]
    settle_holds(reel)                 # held captions follow the words to the new clock
    reel["clock"].update({"mode": C.get("mode"), "rate_wps": C.get("rate_wps"),
                          "rate_source": C.get("rate_source"),
                          "total_s": C.get("total_s"), "note": C.get("note")})
    if C.get("estimated_total_s"):
        reel["clock"]["estimated_total_s"] = C["estimated_total_s"]
    return reel, moved


# ---------------------------------------------------------------- validate

def validate(reel):
    """Every rule in references/reel-schema.md that a machine can check."""
    errs, warns = [], []
    for key in ("version", "reel", "clock", "assets", "beats", "open"):
        if key not in reel:
            errs.append("missing top-level `%s`" % key)
    if errs:
        return errs, warns
    ids = {a["id"] for a in reel["assets"]}
    assets_by_id = {a["id"]: a for a in reel["assets"]}
    if reel["clock"].get("mode") not in ("estimated", "measured"):
        errs.append("clock.mode must be estimated|measured")
    total = reel["clock"].get("total_s")
    seen = set()
    for b in reel["beats"]:
        for k in ("id", "name", "t0", "t1", "w0", "w1", "layers"):
            if k not in b:
                errs.append("%s: missing %s" % (b.get("id"), k))
        if b["id"] in seen:
            errs.append("duplicate beat id %s" % b["id"])
        seen.add(b["id"])
        if b["t1"] < b["t0"]:
            errs.append("%s: t1 < t0" % b["id"])
        if total and b["t1"] > total + 0.01:
            errs.append("%s: ends after clock.total_s" % b["id"])
        zs = [L.get("z") for L in b["layers"]]
        if sorted(zs) != list(range(len(zs))):
            warns.append("%s: z values are %s — expected 0..n bottom-first"
                         % (b["id"], zs))
        for L in b["layers"]:
            if "anchor_word" not in L:
                errs.append("%s: layer %s has no anchor_word (times must be "
                            "derived, never authored)" % (b["id"], L.get("id")))
            if L.get("asset") is None and L.get("kind") != "text" and not L.get("stub"):
                errs.append("%s: layer %s has asset: null and no stub"
                            % (b["id"], L.get("id")))
            if L.get("asset") and L["asset"] not in ids:
                errs.append("%s: layer %s binds unknown asset %s"
                            % (b["id"], L.get("id"), L["asset"]))
            if L.get("kind") == "text" and L.get("style") not in (
                    "title", "caption", "subtitle", "lower-third", "kicker",
                    "word"):
                errs.append("%s: text layer %s has style %r — classify it as "
                            "title, caption or subtitle before handoff (the "
                            "export refuses unclassified text)"
                            % (b.get("id"), L.get("id"), L.get("style")))
            if L.get("anchor_word") is not None and L.get("anchor_text"):
                words = words_of(b.get("narration"))
                i = L["anchor_word"] - b.get("w0", 0)
                if 0 <= i < len(words):
                    have = words[i].lower().strip(".,;:!?\"'")
                    want = str(L["anchor_text"]).lower().strip(".,;:!?\"'")
                    if have != want:
                        errs.append("%s: layer %s anchor_text %r does not match "
                                    "the word at index %d (%r) — the text is "
                                    "the anchor's identity; re-derive the index "
                                    "rather than shipping a mismatch"
                                    % (b.get("id"), L.get("id"),
                                       L["anchor_text"], L["anchor_word"],
                                       words[i]))
            if L.get("chosen_by") not in ("claude", "creator"):
                errs.append("%s: layer %s chosen_by must be claude|creator"
                            % (b["id"], L.get("id")))
            for c in L.get("candidates", []):
                if c not in ids:
                    warns.append("%s: layer %s lists unknown candidate %s"
                                 % (b["id"], L.get("id"), c))
            if L.get("t1", 0) < L.get("t0", 0):
                errs.append("%s: layer %s t1 < t0" % (b["id"], L.get("id")))
        if b.get("transition_in"):
            idx = reel["beats"].index(b)
            prev = reel["beats"][idx - 1] if idx else None
            for msg in transition_problems(b, prev, assets_by_id):
                errs.append("%s: transition in: %s" % (b["id"], msg))
            for L, side, over in transition_overlap(prev, b):
                errs.append("%s: transition in: %s %s the dissolve by %.2f s — %s"
                            % (b["id"], L.get("id"),
                               "runs into" if side == "before" else "starts inside",
                               over, "end it where the dissolve starts" if side == "before"
                               else "anchor it on a later word or shorten the dissolve"))
        for A in b.get("audio", []):
            if A.get("asset") and A["asset"] not in ids:
                errs.append("%s: audio %s binds unknown asset %s"
                            % (b["id"], A.get("id"), A["asset"]))
            if A.get("kind") not in AUDIO_KINDS:
                errs.append("%s: audio %s kind %r — must be one of %s"
                            % (b["id"], A.get("id"), A.get("kind"),
                               "|".join(AUDIO_KINDS)))
            src = assets_by_id.get(A.get("asset") or "")
            if (A.get("kind") == "bed" and src and src.get("kind") == "video"
                    and A["asset"] in {L.get("asset") for L in b["layers"]}):
                errs.append("%s: audio %s is a video's own sound but is typed "
                            "`bed` — that is a `source` lane; a bed is music or "
                            "ambience laid under the narration"
                            % (b["id"], A.get("id")))
    summed = sum(b["t1"] - b["t0"] for b in reel["beats"])
    if total and summed > total + 0.01:
        warns.append("beats sum to %.2fs but total_s is %.2fs — beats overlap "
                     "(fine) but never reconstruct runtime by summing them"
                     % (summed, total))
    return errs, warns


# --------------------------------------------------------------------- cli

def cmd_build(args):
    nb = read_json(args.notebook, "notebook")
    C = read_json(args.clock, "clock")
    BND = json.load(open(args.bindings))
    reel = assemble(nb, C, BND, args)
    if getattr(args, "preserve", None):
        old = read_json(args.preserve, "reel")
        kept, conflicts = preserve_creator(reel, old)
        print("preserved %d creator-chosen placement(s) from %s"
              % (kept, args.preserve))
        for c in conflicts:
            print("  CONFLICT " + c)
    n_moved = clamp_held_cuts(reel)
    write_json(args.out, reel, "reel")
    if n_moved:
        print("  %d held cut(s) moved earlier where the footage ran out "
              "(flagged cut-moved)" % n_moved)

    L = sum(len(b["layers"]) for b in reel["beats"])
    stubs = sum(1 for b in reel["beats"] for x in b["layers"] if x.get("stub"))
    low = sum(1 for b in reel["beats"] for x in b["layers"]
              if x.get("confidence") == "low" and x.get("asset"))
    print("%s — %d beats · %d layers (%d stubs, %d low-confidence) · "
          "%.2fs %s -> %s"
          % (reel["reel"]["title"], len(reel["beats"]), L, stubs, low,
             reel["clock"]["total_s"], reel["clock"]["mode"], args.out))
    if reel["clock"].get("target_s"):
        d = reel["clock"]["total_s"] - reel["clock"]["target_s"]
        print("  %+.1fs against a %.0fs target — reported, not enforced"
              % (d, reel["clock"]["target_s"]))
    if not reel["beats"]:
        print("  ! NOTHING TO STORYBOARD — this notebook produced no beats. "
              "Do not improvise one from a script; say what is missing and "
              "offer /real-brainstorm.", file=sys.stderr)
        raise SystemExit(1)
    errs, warns = validate(reel)
    for q in reel["open"]["questions"]:
        print("  %s [%s] %s" % (q["id"], q["code"], q["msg"][:110]))
    for w in warns:
        print("  ~ " + w)
    for e in errs:
        print("  ! SCHEMA: " + e, file=sys.stderr)
    if errs:
        raise SystemExit(1)


def cmd_retime(args):
    reel = read_json(args.reel, "reel")
    C = read_json(args.clock, "clock")
    before = reel["clock"].get("total_s")
    reel, moved = retime(reel, C)
    clamp_held_cuts(reel)
    write_json(args.out or args.reel, reel, "reel")
    print("re-timed %s: %.2fs -> %.2fs (%s clock). %d layers re-derived from "
          "their own anchor; every anchor unchanged."
          % (args.reel, before or 0.0, reel["clock"]["total_s"],
             reel["clock"]["mode"], moved))


def cmd_validate(args):
    reel = read_json(args.reel, "reel")
    errs, warns = validate(reel)
    for w in warns:
        print("  ~ " + w)
    for e in errs:
        print("  ! " + e)
    print("%s: %d errors, %d warnings" % (args.reel, len(errs), len(warns)))
    raise SystemExit(1 if errs else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("notebook")
    b.add_argument("clock")
    b.add_argument("bindings")
    b.add_argument("-o", "--out", default="reel.json")
    b.add_argument("--assets-root", default=None)
    b.add_argument("--assets-root-local", default=None)
    b.add_argument("--stubs-dir", default=None)
    b.add_argument("--fps", type=int, default=30)
    b.add_argument("--preserve", default=None, metavar="OLD_REEL",
                   help="an earlier reel.json whose creator-chosen placements "
                        "must survive this rebuild")
    r = sub.add_parser("retime")
    r.add_argument("reel")
    r.add_argument("clock")
    r.add_argument("-o", "--out", default=None)
    v = sub.add_parser("validate")
    v.add_argument("reel")
    args = ap.parse_args()
    {"build": cmd_build, "retime": cmd_retime, "validate": cmd_validate}[args.cmd](args)


if __name__ == "__main__":
    main()
