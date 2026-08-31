#!/usr/bin/env python3
"""draft.json -> story.json for fcpxml-sequencer (Module 3).

    python3 to_story.py draft.json media.json story.json \\
        --assets-root "/path/to/assets/Project Name"

The point of generating this rather than hand-writing it: the storyboard the
director approved and the Final Cut timeline are then provably the same edit.
If they can drift, they will.

Anchors become times here. Up to this point every placement is expressed as
"on the word X" precisely so the estimated clock can be swapped for a measured
one without re-planning; this is where words finally collapse into seconds, at
the last possible moment.
"""
import argparse, json, sys

CUT_INTO_WORD = 0.40   # a cut on a word boundary lands on the breath
SNAP = 0.30            # cues closer than this read as one event

def clean_name(s):
    """Final Cut refuses any import whose project/event/clip names contain '/'
    or a newline, and the error fires before media resolution. Sanitize at the
    source too (fcpxml.py also sanitizes centrally — defense in depth)."""
    return str(s).replace("/", "\u00b7").replace("\n", " ").replace("\r", " ")

def cover_scale(mw, mh, W, H):
    """Extra scale beyond FCP's conform-fit needed for a cover crop.
    e.g. 2064x2752 into 1080x1920 -> 1.334; 1080x1080 (square) -> 1.778."""
    if not (mw and mh and W and H):
        return None
    rw, rh = W / mw, H / mh
    return round(max(rw, rh) / min(rw, rh), 3)

def anchor_time(scene, anchor):
    """Seconds from scene start where an anchor word falls.

    Words are distributed across the scene by length, which is a rough proxy for
    speech duration but — more importantly — is monotonic, so the *order* of
    cues is always right even when the spacing isn't. If Module 1 supplied real
    per-word times in `word_times`, those are used instead and this guess never
    runs.
    """
    words = (scene.get("words") or "").split()
    if not words or not anchor:
        return 0.0
    target = anchor.strip().lower().strip(".,;:!?\"'")
    idx = next((i for i, w in enumerate(words)
                if w.lower().strip(".,;:!?\"'—…") == target), None)
    if idx is None:
        return 0.0
    wt = scene.get("word_times")
    if wt and len(wt) == len(words):
        w0, w1 = wt[idx]
        return max(0.0, (w0 - scene.get("t0", 0)) + (w1 - w0) * CUT_INTO_WORD)
    weights = [len(w) + 1 for w in words]
    total = sum(weights)
    before = sum(weights[:idx])
    dur = scene.get("duration", 0)
    return max(0.0, dur * (before + weights[idx] * CUT_INTO_WORD) / total)

def build(draft, mediafile, assets_root=None, event="Sequenced"):
    media = {m["id"]: m for m in mediafile.get("media", [])}
    warn = []

    if draft.get("clock") == "unclocked":
        warn.append("draft is UNCLOCKED — durations are guesses, not Module 1 output. "
                    "Do not lock this into Final Cut.")

    def overlays_for(sc):
        """Every non-base layer, resolved to a time.

        This runs for gap and stub beats too. A caption over a black beat is a
        normal thing to want, and dropping it silently would be the worst kind
        of bug — invisible in the JSON, obvious only once it's in Final Cut.
        """
        out, times = [], []
        for L in sorted(sc.get("layers", []), key=lambda L: L.get("lane", 0)):
            if L.get("lane", 0) == 0:
                continue
            t = anchor_time(sc, L.get("anchor")) + L.get("offset_ms", 0) / 1000.0
            if not L.get("stagger"):
                for prev in times:
                    if abs(t - prev) < SNAP:
                        t = min(t, prev)
                        break
            times.append(t)
            o = {"lane": L.get("lane", 1), "offset": round(max(0.0, t), 3)}
            if L.get("duration"):
                o["duration"] = round(L["duration"], 3)
            if L.get("kind") == "text":
                o.update({"text": L["text"],
                          "font_size": 54 if L.get("style") == "sub" else 96,
                          "font_face": "Bold", "color": [1, 1, 1, 1], "align": "center",
                          "position": [0, -620], "stroke_color": [0, 0, 0, 1],
                          "stroke_width": 8, "shadow": True})
            else:
                om = media.get(L.get("id"))
                if om is None:
                    warn.append(f"{sc['id']} L{L.get('lane')}: media id "
                                f"'{L.get('id')}' unknown — overlay dropped")
                    continue
                o.update({"type": "image" if om["kind"] == "image" else "video",
                          "src": om["file"], "fade_in": 0.15})
                if L.get("in") is not None and L.get("in") != 0:
                    o["start"] = round(L["in"], 3)
                if om.get("duration"):
                    o["asset_duration"] = om["duration"]
                if om["kind"] == "image":
                    if om.get("width"):  o["width"]  = om["width"]
                    if om.get("height"): o["height"] = om["height"]
                if L.get("transform"):
                    o["transform"] = L["transform"]
            out.append(o)
        return out

    W = draft.get("width", 1080); H = draft.get("height", 1920)

    def media_beat(sc, L, dur):
        """One lane-0 layer -> one beat. All the per-clip logic lives here."""
        m = media.get(L.get("id"))
        if m is None:
            warn.append(f"{sc['id']}: media id '{L.get('id')}' is not in media.json — "
                        f"emitted as a named gap so the import stays valid")
            return {"type": "gap", "duration": round(dur, 3),
                    "name": clean_name(f"{sc['id']} MISSING {L.get('id')}")}
        beat = {"type": "video" if m["kind"] == "video" else "image",
                "src": m["file"],
                "duration": round(dur, 3),
                "name": clean_name(f"{sc['id']} — {m['id']}")}
        # in == 0.0 is a real in-point, not "absent" (the falsy-zero bug)
        if L.get("in") is not None and L.get("in") != 0:
            beat["start"] = round(L["in"], 3)
        if m.get("duration"):
            beat["asset_duration"] = m["duration"]
        # stills exported without their pixel size mis-scale in Final Cut
        if m["kind"] == "image":
            if m.get("width"):  beat["width"]  = m["width"]
            if m.get("height"): beat["height"] = m["height"]
        if L.get("transform"):
            beat["transform"] = L["transform"]
        elif L.get("fit") == "cover":
            s = cover_scale(m.get("width"), m.get("height"), W, H)
            if s and abs(s - 1.0) > 0.01:
                beat["transform"] = {"scale": s}
                warn.append(f"{sc['id']}: fit:cover translated to a {s}x transform "
                            f"({m.get('width')}x{m.get('height')} in {W}x{H})")
            elif s is None:
                warn.append(f"{sc['id']}: fit:cover on {m['id']} but its dimensions "
                            f"are unknown — will letterbox; probe the file or set "
                            f"a transform by hand")

        aud = sc.get("audio") or {}
        if m["kind"] == "video" and aud.get("db") is not None:
            beat["volume_db"] = aud["db"]
            if aud.get("swell_to") is not None:
                beat["ducking"] = [{"t": 0, "value": aud["db"]},
                                   {"t": round(dur * 0.75, 3), "value": aud["db"]},
                                   {"t": round(dur, 3), "value": aud["swell_to"]}]
        elif m["kind"] == "video":
            # b-roll under narration is silent unless the draft asks otherwise
            beat["volume_db"] = -60

        src_len = m.get("duration") if m["kind"] == "video" else None
        if src_len and (L.get("in") or 0) + beat["duration"] > src_len + 0.05:
            warn.append(f"{sc['id']}: in-point {L.get('in', 0)}s + "
                        f"{beat['duration']}s runs past {m['file']} ({src_len}s) — "
                        f"Final Cut will refuse this")
        return beat

    beats = []
    for sc in draft["scenes"]:
        dur = sc.get("duration") or (sc.get("t1", 0) - sc.get("t0", 0))
        lane0 = [L for L in sc.get("layers", []) if L.get("lane", 0) == 0]

        if not lane0 and (sc.get("kind") == "blank" or not sc.get("stub")):
            beat = {"type": "gap", "duration": round(dur, 3),
                    "name": clean_name(sc.get("notes") or f"{sc['id']} — blank")}
            ov = overlays_for(sc)
            if ov: beat["overlays"] = ov
            beats.append(beat)
            continue

        if not lane0 and sc.get("stub"):
            st = sc["stub"]
            if st.get("status") == "rendered":
                beat = {"type": "image", "src": st["filename"], "duration": round(dur, 3),
                        "name": clean_name(f"{sc['id']} — {st.get('spec','')[:40]}")}
            else:
                beat = {"type": "gap", "duration": round(dur, 3),
                        "name": clean_name(f"{sc['id']} MAKE — {st.get('spec','')}")}
                warn.append(f"{sc['id']}: stub not rendered; imports as a named gap")
            ov = overlays_for(sc)
            if ov: beat["overlays"] = ov
            beats.append(beat)
            continue

        # --- one beat per lane-0 layer, never just the first ---------------
        # The old code took only the FIRST lane-0 layer; every further lane-0
        # layer was silently dropped (neither beat nor overlay). A 99s scene
        # with 23 lane-0 placements became one 99s shot while the storyboard
        # still showed all 23 — the exact draft/timeline disagreement the
        # single-canonical-draft design exists to prevent.
        starts = []
        for L in lane0:
            t = anchor_time(sc, L.get("anchor")) + L.get("offset_ms", 0) / 1000.0
            starts.append(max(0.0, t))
        order = sorted(range(len(lane0)), key=lambda i: starts[i])
        lane0 = [lane0[i] for i in order]
        starts = [starts[i] for i in order]
        starts[0] = 0.0  # the spine starts at scene start; no leading hole

        if len(lane0) > 1:
            warn.append(f"{sc['id']}: {len(lane0)} lane-0 layers — emitting "
                        f"{len(lane0)} beats (spine made continuous, residue "
                        f"absorbed by each preceding clip)")

        windows = []
        for i in range(len(lane0)):
            t0 = starts[i]
            t1 = starts[i + 1] if i + 1 < len(lane0) else dur
            if t1 <= t0:
                warn.append(f"{sc['id']}: lane-0 layer {i} resolves to a "
                            f"non-positive window ({t0:.2f}->{t1:.2f}); check its anchor")
                t1 = t0 + 0.1
            windows.append((t0, t1))

        scene_beats = []
        for L, (t0, t1) in zip(lane0, windows):
            b = media_beat(sc, L, t1 - t0)
            want = L.get("duration")
            if want and abs(want - (t1 - t0)) > 0.05:
                warn.append(f"{sc['id']}: layer asked {want}s but its window is "
                            f"{t1 - t0:.2f}s — window wins (spine must be continuous)")
            scene_beats.append((t0, t1, b))

        # overlays attach to the beat whose window contains them,
        # offset re-based to that beat's start
        for o in overlays_for(sc):
            t = o.get("offset", 0.0)
            for t0, t1, b in scene_beats:
                if t0 <= t < t1 or (t >= dur and (t0, t1) == (scene_beats[-1][0], scene_beats[-1][1])):
                    o["offset"] = round(t - t0, 3)
                    b.setdefault("overlays", []).append(o)
                    break
            else:
                t0, t1, b = scene_beats[-1]
                o["offset"] = round(max(0.0, t - t0), 3)
                b.setdefault("overlays", []).append(o)
                warn.append(f"{sc['id']}: overlay at {t:.2f}s fell outside every "
                            f"beat window — attached to the last beat")
        beats.extend(b for _, _, b in scene_beats)

    story = {"project": draft.get("project", "Untitled"),
             "event": event,
             "frame_rate": draft.get("frame_rate", "30"),
             "width": draft.get("width", 1080),
             "height": draft.get("height", 1920),
             "assets_root": assets_root or draft.get("assets_root") or "",
             "beats": beats}
    if draft.get("connected"):
        story["connected"] = draft["connected"]

    if not story["assets_root"]:
        warn.append("assets_root is empty — set it to the folder path as the editing "
                    "machine sees it, or every clip imports as red Missing Media")

    return story, warn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft"); ap.add_argument("media"); ap.add_argument("out")
    ap.add_argument("--assets-root", default=None)
    ap.add_argument("--event", default="Sequenced")
    a = ap.parse_args()

    story, warn = build(json.load(open(a.draft)), json.load(open(a.media)),
                        a.assets_root, a.event)
    json.dump(story, open(a.out, "w"), indent=1)
    print(f"{len(story['beats'])} beats -> {a.out}")
    for w in warn:
        print("  ! " + w, file=sys.stderr)

if __name__ == "__main__":
    main()
