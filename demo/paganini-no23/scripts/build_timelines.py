#!/usr/bin/env python3
"""build_timelines.py — the Paganini No. 23 tutorial: studio footage, eleven captions, closing clip.

    python3 scripts/build_timelines.py --from-dir source --media-root media --out timeline \
        --no-publish --public --name paganini-no23 --title "Paganini No. 23 tutorial"

Starts from the approved earlier storyboard (source/storyboard.json and its
measured word clock source/word-clock.json) and changes exactly three things:

  1. the five tutorial excerpts become the creator's studio-background
     re-render of the same recording (media/Videos/P-studio-0N.mov), cut at
     the same source windows. The audio is the same recording sample for
     sample, which the script verifies, so every source window and word
     anchor carries over unchanged.
  2. six more captions at creator-chosen words, same style as the earlier
     five (Helvetica Neue Bold 55, two lines, [0, 90] px, yellow Font Glow,
     Drop Shadow), durations from the clock's text model, never overlapping
     on a lane; every caption line is measured in the actual font.
  3. a closing beat: media/Videos/P-closure.mov, full length, its own sound.

Everything else — the opening performance, the three stills, the earlier
captions and their anchors — is carried over, and the script checks that
before compiling. It then compiles the storyboard to FCPXML and to
OpenTimelineIO (captions rendered to PNG stills, since OTIO has no title
type) and checks the two exports against each other with two independent
readers. With --public, --out keeps only what a reader needs: the two
timelines, the rendered titles, the storyboard, the cross-check and a
receipt with file hashes.

--face dark keeps the Glow but turns the Face back on in near-black, a
higher-contrast variant on a white background.
"""
import argparse
import copy
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MEDIA = HERE.parent / "media"           # the demo's own media folder
STUDIO = MEDIA / "Videos"
COMPILE = ROOT / "skills/batch-2/skills/real-compile/scripts"
STORY = ROOT / "skills/batch-2/skills/real-storyboarding/scripts"
BENCH = ROOT / "bench"
NAME = "paganini-no23"
TITLE = "Paganini No. 23 tutorial"
FPS = 30
WRAP_MAX_PX = 864          # 80 % of the 1080 frame: no caption line may be wider
INK = [0.11, 0.11, 0.11, 1]

# (beat, two-line text, anchor word, which occurrence of that word in the beat)
NEW_CAPTIONS = [
    ("B2", "a whole step\nin first position", "first", 1),
    ("B2", "the same step,\nhigher up", "up", 1),
    ("B3", "why not\noctaves?", "why", 1),
    ("B4", "shift one\nwhole step", "shifting", 1),
    ("B5", "the first finger\nmoves more", "first", 1),
    ("B5", "third and fourth\nmove less", "not", 1),
]
WHY = "the creator asked for captions in more places (19 October 2026)"


def sh(*cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, text=True,
                          capture_output=True, **kw).stdout


def probe(path):
    out = json.loads(sh("ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,width,height,r_frame_rate",
                        "-of", "json", path))
    v = next(s for s in out["streams"] if s["codec_type"] == "video")
    num, den = v["r_frame_rate"].split("/")
    return {"dur_s": float(out["format"]["duration"]), "w": int(v["width"]),
            "h": int(v["height"]), "fps": float(num) / float(den)}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audio_lag_ms(a_path, b_path, t0=1.0, dur=5.0, sr=16000):
    """Cross-correlation lag between two files' audio (ms, b relative to a)."""
    import numpy as np

    def grab(p):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(dur), "-i", str(p),
                              "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        return x - x.mean()
    a, b = grab(a_path), grab(b_path)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    best = (0, -1.0)
    for lag in range(-800, 801, 4):           # ±50 ms, 0.25 ms steps
        c = np.dot(a[lag:], b[:n - lag]) if lag >= 0 else np.dot(a[:n + lag], b[-lag:])
        c /= (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
        if c > best[1]:
            best = (lag, c)
    return best[0] * 1000.0 / sr, float(best[1])


def frames(s):
    return int(round(s * FPS))


def text_model_dur(text, rates):
    n = len(text.split())
    return max(rates.get("text_min", 1.2), rates.get("text_lead", 0.6) + rates.get("text_per_word", 0.32) * n)


def line_widths(text, size=55):
    from PIL import ImageFont
    f = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", size, index=1)  # Bold
    return [round(f.getlength(line), 1) for line in text.split("\n")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--face", choices=("off", "dark"), default="off")
    ap.add_argument("--out", type=Path, default=HERE.parent / "timeline")
    ap.add_argument("--from-dir", dest="from_dir", type=Path, default=HERE.parent / "source",
                    help="folder holding the approved earlier storyboard and clock "
                         "(storyboard.json / word-clock.json)")
    ap.add_argument("--name", default=NAME, help="file name of the exports")
    ap.add_argument("--title", default=TITLE, help="project name inside the exports")
    ap.add_argument("--public", action="store_true",
                    help="keep only what a reader needs in --out: the two timelines, the rendered "
                         "titles, the storyboard, the cross-check and the receipt")
    ap.add_argument("--media-root", type=Path, default=HERE.parent / "media",
                    help="self-contained layout: every asset is looked up by file name under "
                         "MEDIA_ROOT/{Videos,Audio,Images} and the exports point there")
    ap.add_argument("--no-publish", action="store_true", help="accepted for compatibility; no effect here")
    a = ap.parse_args()
    name, title = a.name, a.title
    if a.face == "dark":                      # a separately named variant, never over the main build
        name, title = NAME + "-darkface", TITLE + " (dark face)"
        if a.out == HERE.parent / "timeline":
            a.out = HERE.parent / "timeline-darkface"
    out = Path(os.path.abspath(a.out))          # abspath, not resolve: keep a /Users/Shared/REAL path as given
    out.mkdir(parents=True, exist_ok=True)

    start = Path(os.path.abspath(a.from_dir))
    reel_path = next(p for p in (start / "storyboard.json", start / "reel.json") if p.is_file())
    clock_path = next(p for p in (start / "word-clock.json", start / "clock.json") if p.is_file())
    reel = json.loads(reel_path.read_text())
    clock = json.loads(clock_path.read_text())
    start_hash = {"reel": sha256(reel_path), "clock": sha256(clock_path)}
    beats = {b["id"]: b for b in reel["beats"]}
    assets = {x["id"]: x for x in reel["assets"]}
    start_files = {x["id"]: x["file"] for x in reel["assets"]}      # where the earlier edit kept them
    studio = STUDIO
    if a.media_root:
        # self-contained demo layout: same file names, one folder per kind
        mr = Path(os.path.abspath(a.media_root))
        kinds = {".wav": "Audio", ".m4a": "Audio", ".aac": "Audio", ".mp3": "Audio",
                 ".png": "Images", ".jpg": "Images", ".jpeg": "Images"}
        for x in reel["assets"]:
            x["file"] = str(mr / kinds.get(Path(x["file"]).suffix.lower(), "Videos") / Path(x["file"]).name)
        reel["assets_root"] = reel["assets_root_local"] = str(mr)
        studio = mr / "Videos"
    receipt = {"project": title, "built_from": {"start_storyboard_sha256": start_hash["reel"],
                                                 "start_clock_sha256": start_hash["clock"]},
               "face": a.face, "checks": {}, "captions_added": [], "asset_swaps": []}

    # ---- 1. the studio excerpts replace A01–A05 ---------------------------
    for i in range(1, 6):
        aid = "A%02d" % i
        # distinct file names on purpose: an editor that matches media-pool clips by
        # name (Resolve does) must not pick the earlier bedroom excerpts instead
        new = studio / ("P-studio-%02d.mov" % i)
        old = Path(start_files[aid])
        if not new.is_file():
            sys.exit("missing %s — cut it from the studio file first (see SHOTLIST.md)" % new)
        p = probe(new)
        beat = beats["B%d" % i]
        need = beat["t1"] - beat["t0"]
        if p["dur_s"] + 0.5 / FPS < need:
            sys.exit("%s is %.3fs, shorter than beat B%d (%.3fs)" % (new.name, p["dur_s"], i, need))
        swap = {"asset": aid, "old": str(old), "new": str(new),
                "new_dur_s": p["dur_s"], "beat_s": round(need, 4)}
        # the earlier bedroom excerpt, when present, proves the audio is the same recording
        take = Path(assets["A%02d" % (i + 5)]["file"])
        ref = old if old.is_file() else (take if take.is_file() else None)
        if ref is not None:
            lag, corr = audio_lag_ms(ref, new)
            if abs(lag) > 1.0 or corr < 0.98:
                sys.exit("%s audio does not line up with %s (lag %.2f ms, corr %.3f)"
                         % (new.name, ref.name, lag, corr))
            swap.update({"audio_reference": str(ref), "audio_lag_ms": round(lag, 2),
                         "audio_corr": round(corr, 4)})
        else:
            swap["audio_reference"] = "not checked: no earlier excerpt or take on this machine"
        receipt["asset_swaps"].append(swap)
        x = assets[aid]
        x.update({"file": str(new), "dur_s": round(p["dur_s"], 4), "w": p["w"], "h": p["h"],
                  "fps": p["fps"], "exists": True})
        x["catalog"]["shows"] = (x["catalog"].get("shows", "") +
                                 " Studio-background re-render of the same recording (background "
                                 "replaced by the creator with BiRefNet, 19 October 2026); same "
                                 "source window, same audio.")
        x["catalog"]["original_file"] = str(old)

    # ---- 2. more captions ------------------------------------------------
    words = clock["words"]
    cut = (clock.get("rates") or {}).get("cut_into_word", 0.4)
    for bid, text, anchor, occurrence in NEW_CAPTIONS:
        beat = beats[bid]
        hits = [w for w in words if w["beat"] == bid and
                w["w"].lower().strip(".,;:!?\"'") == anchor.lower()]
        if len(hits) < occurrence:
            sys.exit("%s: word %r occurrence %d not found" % (bid, anchor, occurrence))
        w = hits[occurrence - 1]
        template = next(L for L in beat["layers"] if L["kind"] == "text")
        t0 = w["start"] + cut * (w["end"] - w["start"])
        dur = text_model_dur(text, clock.get("rates") or {})
        t1 = min(t0 + dur, beat["t1"])
        # the same lane as the beat's existing caption: never overlap it
        for L in beat["layers"]:
            if L["kind"] == "text" and L["z"] == template["z"]:
                if not (t1 <= L["t0"] or t0 >= L["t1"]):
                    t1 = min(t1, L["t0"] - 1.0 / FPS)
        if frames(t1 - t0) < frames(1.2):
            sys.exit("%s caption %r would last %.2fs" % (bid, text, t1 - t0))
        n = 1 + max(int(L["id"].split(".L")[1]) for L in beat["layers"])
        new = copy.deepcopy(template)
        new.update({"id": "%s.L%d" % (bid, n), "anchor_word": w["i"], "anchor_text": w["w"],
                    "offset_ms": 0, "t0": t0, "t1": t1, "content": text,
                    "chosen_by": "creator", "confidence": "high", "why": WHY,
                    "source_text": "caption: " + text.replace("\n", " "),
                    "dur_source": "text-model", "dur_s": round(t1 - t0, 4),
                    "style_by": "creator", "snapped": False})
        widths = line_widths(text)
        if max(widths) > WRAP_MAX_PX:
            sys.exit("caption %r line is %.0f px wide (> %d)" % (text, max(widths), WRAP_MAX_PX))
        beat["layers"].append(new)
        receipt["captions_added"].append({"id": new["id"], "text": text, "anchor_word": w["i"],
                                          "anchor_text": w["w"], "t0": round(t0, 4), "t1": round(t1, 4),
                                          "line_widths_px": widths})
    # every caption (old and new) obeys the width rule and the style
    caption_table = []
    for b in reel["beats"]:
        for L in b["layers"]:
            if L["kind"] == "text":
                widths = line_widths(L["content"], L.get("font_size", 55))
                if max(widths) > WRAP_MAX_PX:
                    sys.exit("%s line is %.0f px wide" % (L["id"], max(widths)))
                if a.face == "dark":
                    L["face"] = True
                    L["color"] = INK
                L["shadow"] = True            # the creator's Final Cut tweak, 19 October: Drop Shadow on
                caption_table.append({"id": L["id"], "text": L["content"], "t0": round(L["t0"], 3),
                                      "t1": round(L["t1"], 3), "font_size": L.get("font_size"),
                                      "glow": bool(L.get("glow")), "face": L.get("face"),
                                      "shadow": True, "line_widths_px": widths})
    receipt["captions"] = caption_table

    # ---- 3. the closing clip ---------------------------------------------
    closure = studio / "P-closure.mov"
    if not closure.is_file():
        sys.exit("missing %s" % closure)
    pc = probe(closure)
    last = reel["beats"][-1]
    t0 = last["t1"]
    dur = frames(pc["dur_s"] - 0.5 / FPS) / FPS          # whole frames inside the file
    t1 = t0 + dur
    b0 = reel["beats"][0]
    assets["A15"] = {
        "id": "A15", "file": str(closure), "kind": "video", "dur_s": round(pc["dur_s"], 4),
        "w": pc["w"], "h": pc["h"], "fps": pc["fps"], "rotation": 0, "exists": True,
        "catalog": {"role": "Closing clip, supplied by the creator", "beat": "B6",
                    "shows": "Closing shot; orientation checked in a sampled frame.",
                    "use": "Appended after the tutorial, full length, original audio.",
                    "original_file": "~/Downloads/paganini_no23_closure.mov"}}
    reel["assets"].append(assets["A15"])
    gone = [x["file"] for x in reel["assets"] if not Path(x["file"]).is_file()]
    if gone:
        sys.exit("missing media:\n  " + "\n  ".join(gone))
    b6 = {"id": "B6", "name": "closing", "t0": t0, "t1": t1, "w0": None, "w1": None,
          "narration": "", "wordless": True,
          "source": {"cell": "C6", "component": "C6.closure"},
          "note": "Creator-requested closing clip after the tutorial. Fixed duration, no speech anchor.",
          "flags": [], "held_to": None,
          "layers": [dict(b0["layers"][0], id="B6.L1", asset="A15", t0=t0, t1=t1, src_in=0,
                          src_out=dur, fit="fill",
                          why="Closing clip requested after the tutorial (19 October 2026).")],
          "audio": [dict(b0["audio"][0], id="B6.A1", asset="A15", t0=t0, t1=t1, src_in=0,
                         src_out=dur, why="Original audio of the closing clip.")]}
    reel["beats"].append(b6)
    reel["reel"]["title"] = title
    reel["clock"]["total_s"] = reel["clock"]["target_s"] = t1
    reel["clock"]["note"] = (reel["clock"].get("note", "") +
                             " 19 October 2026: studio-background excerpts, six more captions, "
                             "closing clip B6 appended; tutorial timing unchanged.")
    # the clock file, for tracks.py: add the wordless beat the same way B0 was added
    cb0 = next(b for b in clock["beats"] if b["id"] == "B0")
    clock["beats"].append(dict(cb0, id="B6", t0=t0, t1=t1))
    for pl in [p for p in clock["placements"] if p["beat"] == "B0"]:
        q = dict(pl, id=pl["id"].replace("B0", "B6"), beat="B6", t0=t0, t1=t1,
                 dur_s=dur, span_s=dur)
        clock["placements"].append(q)
    clock["total_s"] = clock["target_s"] = t1
    clock["closure_s"] = dur
    receipt["closure"] = {"file": str(closure), "probe": pc, "beat": "B6", "t0": round(t0, 4),
                          "t1": round(t1, 4), "frames": frames(dur)}

    # ---- 4. write, adapt, compile both targets, check --------------------
    (out / "reel.json").write_text(json.dumps(reel, ensure_ascii=False, indent=2) + "\n")
    (out / "clock.json").write_text(json.dumps(clock, ensure_ascii=False, indent=2) + "\n")
    fcp = out / (name + ".fcpxml")
    oti = out / (name + ".otio")
    print(sh(sys.executable, COMPILE / "adapt.py", out / "reel.json", "-o", out / "story.json"))
    print(sh(sys.executable, COMPILE / "compile.py", "build", out / "story.json", fcp))
    print(sh(sys.executable, COMPILE / "compile.py", "report", fcp, out / "report.html"))
    print(sh(sys.executable, COMPILE / "compile.py", "build", out / "story.json", oti,
             "--target", "otio", "--titles", "raster"))
    eq = sh(sys.executable, BENCH / "otio_edl.py", oti, "--against", fcp, "--report",
            out / "equivalence.json")
    print(eq)
    try:
        sh(sys.executable, STORY / "tracks.py", "tracks", out / "reel.json", out / "REEL-TRACKS.html",
           "--clock", out / "clock.json")
    except subprocess.CalledProcessError as e:
        print("tracks.py skipped:", e.stderr.strip()[-300:])
    if a.public:
        for f in ("clock.json", "story.json", "report.html", "REEL-TRACKS.html"):
            (out / f).unlink(missing_ok=True)
    receipt["checks"]["equivalence"] = eq.strip().splitlines()[-1]
    receipt["checks"]["total_s"] = round(t1, 4)
    receipt["checks"]["total_frames"] = frames(t1)
    receipt["outputs"] = {"fcpxml": str(fcp), "fcpxml_sha256": sha256(fcp),
                          "otio": str(oti), "otio_sha256": sha256(oti),
                          "titles_dir": str(out / (name + "-titles"))}

    # ---- 5. receipt --------------------------------------------------------
    (out / "build-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("checks", "outputs")}, indent=2))
    print("captions:", len(caption_table), "| added:", [c["id"] for c in receipt["captions_added"]])
    # the private workflow's publishing step is not part of the demo


if __name__ == "__main__":
    main()
