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
                if L.get("transform"):
                    o["transform"] = L["transform"]
            out.append(o)
        return out

    beats = []
    for sc in draft["scenes"]:
        dur = sc.get("duration") or (sc.get("t1", 0) - sc.get("t0", 0))
        base = next((L for L in sc.get("layers", []) if L.get("lane", 0) == 0), None)
        beat = None

        if sc.get("kind") == "blank" or (base is None and not sc.get("stub")):
            beat = {"type": "gap", "duration": round(dur, 3),
                    "name": sc.get("notes") or f"{sc['id']} — blank"}

        elif base is None and sc.get("stub"):
            st = sc["stub"]
            if st.get("status") == "rendered":
                beat = {"type": "image", "src": st["filename"], "duration": round(dur, 3),
                        "name": f"{sc['id']} — {st.get('spec','')[:40]}"}
            else:
                beat = {"type": "gap", "duration": round(dur, 3),
                        "name": f"{sc['id']} MAKE — {st.get('spec','')}"}
                warn.append(f"{sc['id']}: stub not rendered; imports as a named gap")

        else:
            m = media.get(base.get("id"))
            if m is None:
                warn.append(f"{sc['id']}: media id '{base.get('id')}' is not in media.json — "
                            f"emitted as a named gap so the import stays valid")
                beat = {"type": "gap", "duration": round(dur, 3),
                        "name": f"{sc['id']} MISSING {base.get('id')}"}
            else:
                beat = {"type": "video" if m["kind"] == "video" else "image",
                        "src": m["file"],
                        "duration": round(base.get("duration", dur), 3),
                        "name": f"{sc['id']} — {m['id']}"}
                if base.get("in"):
                    beat["start"] = round(base["in"], 3)
                if m.get("duration"):
                    beat["asset_duration"] = m["duration"]
                if base.get("transform"):
                    beat["transform"] = base["transform"]

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

                # only video has a real playback length to run past — a still
                # holds for however long the beat asks, and some JPEGs report
                # a spurious sub-second "duration" from ffprobe that would
                # otherwise false-positive here
                src_len = m.get("duration") if m["kind"] == "video" else None
                if src_len and (base.get("in") or 0) + beat["duration"] > src_len + 0.05:
                    warn.append(f"{sc['id']}: in-point {base.get('in', 0)}s + "
                                f"{beat['duration']}s runs past {m['file']} ({src_len}s) — "
                                f"Final Cut will refuse this")

        ov = overlays_for(sc)
        if ov:
            beat["overlays"] = ov
        beats.append(beat)

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
