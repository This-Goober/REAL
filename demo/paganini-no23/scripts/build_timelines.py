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

Before those three it applies the creator's revisions (source/revisions.json):
narration trims, where a beat's source window starts later or ends earlier,
the words outside it leave the clock, every other anchor is kept, and the
beats that follow move up by the time removed; and transitions, a cross
dissolve into a beat, which the compiler refuses unless both shots carry the
handles it borrows (the excerpts are cut with them).

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


def audio_lag_ms(a_path, b_path, t0=1.0, dur=5.0, sr=16000, b_t0=None):
    """Cross-correlation lag between two files' audio (ms, b relative to a).
    b_t0 reads b from a different offset, for a window that starts later in the same recording."""
    import numpy as np

    def grab(p, at):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(at), "-t", str(dur), "-i", str(p),
                              "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        return x - x.mean()
    a, b = grab(a_path, t0), grab(b_path, t0 if b_t0 is None else b_t0)
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


def audio_dur(path):
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path))


def apply_trims(reel, clock, trims):
    """The creator's narration trims. A beat's source window starts later or ends
    earlier. Seconds change, anchors do not: the words outside the window leave the
    clock and the rest are renumbered in order; every placement keeps its anchor
    word, except the beat's base shot and narration, which move to the new first
    word; the beats that follow move up by the time removed. Refuses a trim that is
    not a whole number of frames, that drops words other than the beat's first
    ones, or that would cut a word a caption or still is anchored to."""
    import re
    cbeats = {b["id"]: b for b in clock["beats"]}
    by_beat = {t["beat"]: t for t in trims}
    words = clock["words"]
    dropped, report, heads = set(), [], {}        # heads: beat -> (trim at the head, handle in the file)
    shift = 0.0                                    # seconds removed before this beat
    for b in reel["beats"]:
        bid, cb, t = b["id"], cbeats[b["id"]], by_beat.get(b["id"])
        head = tail = 0.0
        drops = []
        if t:
            head = t.get("src_in_s", t["was_src_in_s"]) - t["was_src_in_s"]
            tail = t["was_src_out_s"] - t.get("src_out_s", t["was_src_out_s"])
            for edge, v in (("start", head), ("end", tail)):
                if v < 0 or abs(v * FPS - round(v * FPS)) > 1e-3:
                    sys.exit("%s: the %s trim %.6f s is not a whole number of frames" % (bid, edge, v))
            head, tail = round(head * FPS) / FPS, round(tail * FPS) / FPS
            drops = list(t.get("drops", []))
        bw = [w for w in words if w["beat"] == bid]
        if [w["w"] for w in bw[:len(drops)]] != drops:
            sys.exit("%s: the words to drop %r are not the beat's first words %r"
                     % (bid, drops, [w["w"] for w in bw[:len(drops)]]))
        kept = bw[len(drops):]
        dropped.update(w["i"] for w in bw[:len(drops)])
        old_t0, old_t1 = b["t0"], b["t1"]
        new_t0, new_t1 = old_t0 - shift, old_t1 - shift - head - tail
        for w in kept:
            s0, e0 = w["start"] - shift - head, w["end"] - shift - head
            if s0 >= new_t1 - 1e-6:
                sys.exit("%s: word %r (#%d) falls outside the trimmed window" % (bid, w["w"], w["i"]))
            w["start"] = max(new_t0, s0)
            w["end"] = min(new_t1, max(w["start"], e0))
        first = kept[0] if kept else None
        for item in b["layers"] + b["audio"]:
            aw = item.get("anchor_word")
            spans = bool(item.get("base")) or item.get("kind") == "narration"
            if aw in dropped and not spans:
                sys.exit("%s: %s is anchored to a dropped word (#%s %r)" % (bid, item["id"], aw, item.get("anchor_text")))
            if spans:
                item["t0"], item["t1"] = new_t0, new_t1
                if aw is not None and first is not None and (aw in dropped or aw == b.get("w0")):
                    item["anchor_word"], item["anchor_text"] = first["i"], first["w"]
            else:
                length = item["t1"] - item["t0"]
                item["t0"] = item["t0"] - shift - head
                item["t1"] = min(item["t0"] + length, new_t1)
            if item.get("src_in") is not None and item.get("src_out") is not None:
                item["src_out"] = item["src_in"] + (item["t1"] - item["t0"])
        for p in clock.get("placements", []):
            if p["beat"] != bid:
                continue
            aw = p.get("anchor_word")
            if p.get("base") or p.get("dur_source") in ("narration", "to-next") or (aw is not None and aw in dropped):
                p["t0"], p["t1"] = new_t0, new_t1
                if aw is not None and first is not None and (aw in dropped or aw == b.get("w0")):
                    p["anchor_word"] = first["i"]
            else:
                length = p["t1"] - p["t0"]
                p["t0"] = p["t0"] - shift - head
                p["t1"] = min(p["t0"] + length, new_t1)
            p["span_s"] = round(p["t1"] - p["t0"], 4)
            if p.get("dur_source") in ("narration", "to-next"):
                p["dur_s"] = p["span_s"]
        b["t0"], b["t1"] = new_t0, new_t1
        cb["t0"], cb["t1"] = new_t0, new_t1
        head_handle = float((t or {}).get("head_handle_s") or 0)
        if head_handle:
            # the excerpt file carries picture before the window: the shot starts that far in
            shot = next((L for L in b["layers"] if L.get("base")), None)
            if shot is None:
                sys.exit("%s: a head handle needs a base shot to apply src_in to" % bid)
            shot["src_in"] = head_handle
        if drops:
            prefix = " ".join(drops)
            narr = b["narration"]
            if not narr.startswith(prefix):
                sys.exit("%s: narration does not start with %r" % (bid, prefix))
            narr = narr[len(prefix):].lstrip()
            narr = narr[:1].upper() + narr[1:]
            b["narration"] = cb["narration"] = narr
            for item in b["audio"]:
                if item.get("text"):
                    item["text"] = narr
        if t:
            win = (t.get("src_in_s", t["was_src_in_s"]), t.get("src_out_s", t["was_src_out_s"]))
            for holder in (b, cb):
                holder["note"] = re.sub(r"from [\d.]+ s to [\d.]+ s \([\d.]+ s\)",
                                        "from %.4g s to %.4g s (%.1f s)" % (win[0], win[1], win[1] - win[0]),
                                        holder.get("note", ""))
            for ew in clock.get("excerpt_windows", []):
                if ew["beat"] == bid:
                    ew.update({"start": new_t0, "end": new_t1, "duration": round(new_t1 - new_t0, 4),
                               "source_start": ew["source_start"] + head})
            heads[bid] = (head, head_handle)
            report.append({"beat": bid, "source_window_s": [round(win[0], 6), round(win[1], 6)],
                           "was_source_window_s": [t["was_src_in_s"], t["was_src_out_s"]],
                           "frames_removed": frames(head + tail), "dropped_words": drops,
                           "head_handle_s": head_handle, "tail_handle_s": float(t.get("tail_handle_s") or 0),
                           "beat_s": [round(new_t0, 4), round(new_t1, 4)], "why": t.get("why", "")})
        else:
            for ew in clock.get("excerpt_windows", []):
                if ew["beat"] == bid:
                    ew.update({"start": new_t0, "end": new_t1})
        shift += head + tail
    # renumber the words; every anchor follows its word
    kept_words = [w for w in words if w["i"] not in dropped]
    remap = {}
    for n, w in enumerate(kept_words):
        remap[w["i"]] = n
        w["i"] = n
    clock["words"] = kept_words
    by_new = {w["i"]: w for w in kept_words}
    for b in reel["beats"]:
        bw = [w for w in kept_words if w["beat"] == b["id"]]
        if bw:
            b["w0"], b["w1"] = bw[0]["i"], bw[-1]["i"]
            cbeats[b["id"]]["w0"], cbeats[b["id"]]["w1"] = b["w0"], b["w1"]
        for item in b["layers"] + b["audio"]:
            aw = item.get("anchor_word")
            if aw is None:
                continue
            item["anchor_word"] = remap[aw]
            if item.get("anchor_text") and by_new[item["anchor_word"]]["w"] != item["anchor_text"]:
                sys.exit("%s: anchor text %r is not word #%d %r"
                         % (item["id"], item["anchor_text"], item["anchor_word"], by_new[item["anchor_word"]]["w"]))
    for p in clock.get("placements", []):
        if p.get("anchor_word") is not None:
            p["anchor_word"] = remap[p["anchor_word"]]
    clock["total_words"] = len(kept_words)
    for k in ("narration_s", "audio_total_s", "total_s", "target_s"):
        if clock.get(k):
            clock[k] = round(clock[k] - shift, 6)
    reel["clock"]["total_s"] = reel["beats"][-1]["t1"]
    return report, heads


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

    # ---- 0. the creator's revisions: narration trims, then transitions ----
    rev_path = start / "revisions.json"
    heads, transitions = {}, []
    if rev_path.is_file():
        revisions = json.loads(rev_path.read_text())
        receipt["built_from"]["revisions_sha256"] = sha256(rev_path)
        receipt["narration_trims"], heads = apply_trims(reel, clock, revisions.get("trims") or [])
        transitions = revisions.get("transitions") or []

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
        head, head_handle = heads.get("B%d" % i, (0.0, 0.0))   # a trimmed window starts later; a handle is extra file before it
        need = beat["t1"] - beat["t0"] + head_handle
        if p["dur_s"] + 0.5 / FPS < need:
            sys.exit("%s is %.3fs, shorter than beat B%d needs (%.3fs)" % (new.name, p["dur_s"], i, need))
        swap = {"asset": aid, "old": str(old), "new": str(new),
                "new_dur_s": p["dur_s"], "beat_s": round(need, 4)}
        # the earlier bedroom excerpt, when present, proves the audio is the same recording
        take = Path(assets["A%02d" % (i + 5)]["file"])
        ref = old if old.is_file() else (take if take.is_file() else None)
        if ref is not None:
            lag, corr = audio_lag_ms(ref, new, t0=1.0 + head - head_handle, b_t0=1.0)
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
    for x in reel["assets"]:                      # the takes' durations follow their files
        if x.get("kind") == "audio" and Path(x["file"]).is_file():
            x["dur_s"] = round(audio_dur(x["file"]), 4)

    # ---- 0b. transitions: a dissolve into a beat, a decision on the beat ---
    receipt["transitions"] = []
    for t in transitions:
        beat = beats[t["beat"]]
        beat["transition_in"] = {"name": t.get("name", "Cross Dissolve"), "dur_s": float(t["dur_s"]),
                                 "chosen_by": "creator", "why": t.get("why", "the creator asked for a dissolve")}
        receipt["transitions"].append({"beat": t["beat"], "name": beat["transition_in"]["name"],
                                       "dur_s": beat["transition_in"]["dur_s"],
                                       "cut_s": round(beat["t0"], 4), "why": t.get("why", "")})

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
