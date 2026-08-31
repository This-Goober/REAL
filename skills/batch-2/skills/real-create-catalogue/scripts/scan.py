#!/usr/bin/env python3
"""
scan.py — inventory an asset folder and build the cheap visual proxies a
catalog needs. Runs WHERE THE MEDIA LIVES so nothing large ever moves.

    python3 scan.py <assets_root> <work_dir> [--budget 35] [--only SUBSTR]
                    [--frames 16] [--force]

Four asset kinds are inventoried: video, image, audio and text (scripts,
caption lists, transcripts, .srt/.vtt subtitle files — they are assets too and
/real-storyboarding binds to them exactly like anything else).

Produces, inside <work_dir>:
    inventory.json      every file with ffprobe specs (text files get
                        bytes/lines/words plus a leading excerpt)
    skeleton.json       catalog_data.json with the judgement fields blank
    thumbs/*_sheet.jpg  16-frame contact sheet per video, timestamps burned in
    thumbs/IMAGES_page*.jpg   labelled 12-up grids of every image
    audio16k/*.wav      16 kHz mono copies, small enough to ship for ASR

INCREMENTAL AND TIME-BUDGETED. Remote shell calls are typically capped around
45 s; a full decode of a 250 MB HEVC file blows straight through that. So:
  * frames are pulled with `ffmpeg -ss T -i file -frames:v 1` (seek, no full
    decode) — roughly 0.3-1 s per frame instead of minutes per file;
  * work already done is skipped, so you just call this again until it prints
    ALL DONE.

Exit line is either "ALL DONE" or "MORE WORK REMAINS — run again".
"""
import argparse, json, os, subprocess, sys, time

VID = {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".webm"}
IMG = {".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff", ".gif", ".webp", ".bmp"}
AUD = {".wav", ".aif", ".aiff", ".m4a", ".mp3", ".caf", ".flac", ".ogg"}
TXT = {".txt", ".md", ".markdown", ".srt", ".vtt", ".rtf", ".text"}
SKIP_DIRS = {"cache", "renders", "autosave", "__pycache__", ".git"}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EXCERPT_CHARS = 600


def kind(p):
    e = os.path.splitext(p)[1].lower()
    return ("video" if e in VID else "image" if e in IMG else "audio" if e in AUD
            else "text" if e in TXT else "other")


def parse_ts(t):
    """'90', '1:30', '1:30.5' -> seconds."""
    t = str(t).strip()
    if ":" in t:
        parts = t.split(":")
        return float(parts[-1]) + 60 * float(parts[-2]) + \
            (3600 * float(parts[-3]) if len(parts) > 2 else 0)
    return float(t)


def parse_windows(specs):
    """--window 'RELSUBSTR=MM:SS-MM:SS' (repeatable) -> {relsubstr: (t0, t1)}.
    The creator says which stretch of a big clip matters, in natural times —
    'the useful part is 0:10–0:20' — and only that stretch is sampled."""
    out = {}
    for spec in specs or []:
        try:
            name, rng = spec.rsplit("=", 1)
            t0, t1 = rng.split("-")
            out[name.strip()] = (parse_ts(t0), parse_ts(t1))
        except Exception:
            print("bad --window %r — expected NAME=START-END (e.g. clip.mov=0:10-0:20)"
                  % spec, file=sys.stderr)
    return out


def window_for(rel, windows):
    for name, w in windows.items():
        if name.lower() in rel.lower():
            return w
    return None


def dhash64(im):
    """64-bit perceptual difference hash of a PIL image."""
    g = im.convert("L").resize((9, 8))
    px = list(g.getdata())
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | (1 if px[r * 9 + c] > px[r * 9 + c + 1] else 0)
    return bits


def hamming(a, b):
    return bin(a ^ b).count("1")


# Measured on real footage (Drone_Part 1): two takes of one setup land at
# Hamming ~7; genuinely different setups from the same shoot at 25+. Nothing
# was observed in between, so the bands sit in empty space — but footage
# varies, so the middle band exists precisely to avoid false certainty.
SAME_MAX = 10        # <= this: near-identical setup, group confidently
UNCERTAIN_MAX = 20   # <= this: ambiguous — ASK THE CREATOR, never assert


def shot_groups(hashes):
    """hashes: {rel: [int, ...]} -> (group_of {rel: 'G#'}, verdicts, review).
    Union-find over confident edges only; ambiguous pairs go to `review` for
    the creator to check — the goal is preventing false certainty, in both
    directions."""
    rels = sorted(hashes)
    parent = {r: r for r in rels}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    review, nearest = [], {}
    for i, r1 in enumerate(rels):
        for r2 in rels[i + 1:]:
            d = min(hamming(h1, h2) for h1 in hashes[r1] for h2 in hashes[r2])
            for r in (r1, r2):
                other = r2 if r == r1 else r1
                if r not in nearest or d < nearest[r][1]:
                    nearest[r] = (other, d)
            if d <= SAME_MAX:
                parent[find(r1)] = find(r2)
            elif d <= UNCERTAIN_MAX:
                review.append({"a": r1, "b": r2, "distance": d})
    roots, group_of, verdict = {}, {}, {}
    n = 0
    for r in rels:
        root = find(r)
        if root not in roots:
            n += 1
            roots[root] = "G%d" % n
    for r in rels:
        gid = roots[find(r)]
        members = sum(1 for x in rels if roots[find(x)] == gid)
        if members > 1:
            group_of[r] = gid
            verdict[r] = "same-setup"
        elif any(r in (pr["a"], pr["b"]) for pr in review):
            group_of[r] = gid
            verdict[r] = "uncertain"
    return group_of, verdict, review, nearest


def probe_text(p):
    """Cheap stats + a leading excerpt for a text asset. Never raises."""
    o = {}
    try:
        o["bytes"] = os.path.getsize(p)
        o["mb"] = round(o["bytes"] / 1e6, 3)
    except Exception:
        return o
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            body = fh.read(400_000)
    except Exception:
        return o
    o["lines"] = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    o["words"] = len(body.split())
    ex = body[:EXCERPT_CHARS].strip()
    o["excerpt"] = ex + ("…" if len(body) > EXCERPT_CHARS else "")
    return o


def probe(p):
    try:
        d = json.loads(subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format",
             "-show_streams", p], capture_output=True, text=True, timeout=60).stdout or "{}")
    except Exception:
        return {}
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), None)
    a = next((s for s in d.get("streams", []) if s["codec_type"] == "audio"), None)
    fm = d.get("format", {})
    o = {"dur": round(float(fm.get("duration", 0) or 0), 2),
         "mb": round(int(fm.get("size", 0) or 0) / 1e6, 1),
         "created": (fm.get("tags", {}) or {}).get("creation_time", "")}
    if v:
        rot = ""
        for sd in (v.get("side_data_list") or []):
            if "rotation" in sd:
                rot = f" rot{sd['rotation']}"
        try:
            n, dd = v.get("r_frame_rate", "0/1").split("/")
            fps = float(n) / float(dd) if float(dd) else 0
        except Exception:
            fps = 0
        o["v"] = f'{v["width"]}x{v["height"]} {v.get("codec_name")} {fps:.0f}fps{rot}'
        o["w"], o["h"] = v.get("width"), v.get("height")
    if a:
        o["a"] = (f'{a.get("codec_name")} {a.get("channels")}ch '
                  f'{int(a.get("sample_rate", 0)) // 1000}k')
    return o


def walk(root, skip_abs=()):
    """Every catalogable file under root. `skip_abs` holds absolute directories
    to stay out of — normally the work dir, so generated contact sheets and
    16 kHz copies never get catalogued as if they were source assets."""
    skip_abs = {os.path.abspath(s) for s in skip_abs}
    out = []
    for dp, dirs, files in os.walk(root):
        if os.path.abspath(dp) in skip_abs:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")
                   and os.path.abspath(os.path.join(dp, d)) not in skip_abs]
        for fn in sorted(files):
            if fn.startswith("."):
                continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, root)
            k = kind(fn)
            if k != "other":
                out.append((rel, full, k))
    return out


def contact_sheet(src, dst, n, width=200, cols=4, window=None):
    """Returns None on failure, else {"times": [...], "hashes": [...],
    "t0": .., "t1": ..}. `window` restricts sampling to (t0, t1) — the
    creator-directed partial-inspection path for files too big or long to
    sample whole."""
    from PIL import Image, ImageDraw, ImageFont
    info = probe(src)
    dur = info.get("dur") or 0
    if dur <= 0:
        return None
    t_lo, t_hi = (0.0, dur)
    if window:
        t_lo = max(0.0, min(window[0], dur))
        t_hi = max(t_lo + 0.5, min(window[1], dur))
    span = t_hi - t_lo
    tmp = "/tmp/_cs.jpg"
    tiles, times, hashes = [], [], []
    for i in range(n):
        t = t_lo + span * (i + 0.5) / n
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", src,
                        "-frames:v", "1", "-vf", f"scale={width}:-1", "-q:v", "4", tmp],
                       capture_output=True, timeout=60)
        if not os.path.exists(tmp):
            continue
        im = Image.open(tmp).convert("RGB")
        d = ImageDraw.Draw(im)
        try: f = ImageFont.truetype(FONT, 15)
        except Exception: f = ImageFont.load_default()
        d.rectangle([0, 0, 56, 20], fill=(0, 0, 0))
        d.text((4, 2), f"{int(t // 60)}:{int(t % 60):02d}", fill=(255, 220, 0), font=f)
        tiles.append(im)
        times.append(round(t, 2))
        hashes.append(dhash64(im))
        os.remove(tmp)
    if not tiles:
        return None
    tw, th = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    sh = Image.new("RGB", (cols * tw, rows * th + 24), (20, 20, 24))
    for i, im in enumerate(tiles):
        sh.paste(im.resize((tw, th)), ((i % cols) * tw, (i // cols) * th + 24))
    d = ImageDraw.Draw(sh)
    try: f = ImageFont.truetype(FONT, 15)
    except Exception: f = ImageFont.load_default()
    d.text((6, 4), f"{os.path.basename(src)[:60]}   {dur:.1f}s"
           + (f"   [window {t_lo:.0f}-{t_hi:.0f}s]" if window else ""),
           fill=(255, 255, 255), font=f)
    sh.save(dst, quality=72)
    return {"times": times, "hashes": hashes, "t0": round(t_lo, 2),
            "t1": round(t_hi, 2), "dur": dur, "windowed": bool(window)}


def image_pages(root, files, outdir, per=12, cols=4, cell=300, lab=34):
    from PIL import Image, ImageDraw, ImageFont
    made = []
    for pg in range(0, len(files), per):
        dst = os.path.join(outdir, f"IMAGES_page{pg // per + 1}.jpg")
        chunk = files[pg:pg + per]
        rows = (len(chunk) + cols - 1) // cols
        sh = Image.new("RGB", (cols * cell, rows * (cell + lab)), (18, 18, 22))
        d = ImageDraw.Draw(sh)
        try: f = ImageFont.truetype(FONT, 13)
        except Exception: f = ImageFont.load_default()
        for i, (rel, full, _k) in enumerate(chunk):
            try:
                im = Image.open(full)
                try: im.seek(0)
                except Exception: pass
                im = im.convert("RGB")
            except Exception:
                continue
            im.thumbnail((cell - 8, cell - 8))
            x, y = (i % cols) * cell, (i // cols) * (cell + lab)
            sh.paste(im, (x + (cell - im.width) // 2, y + lab + (cell - lab - im.height) // 2 + 8))
            d.text((x + 5, y + 3), f"[{pg + i + 1}] {rel[:34]}", fill=(255, 235, 120), font=f)
            if rel[34:]:
                d.text((x + 5, y + 17), rel[34:68], fill=(190, 175, 90), font=f)
        sh.save(dst, quality=75)
        made.append(dst)
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("work")
    ap.add_argument("--budget", type=float, default=35.0)
    ap.add_argument("--only", default="")
    ap.add_argument("--frames", type=int, default=16)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--window", action="append", default=[],
                    help="NAME=START-END: sample only this stretch of a clip "
                         "(creator-directed partial inspection), e.g. "
                         "--window 'big-take.mov=0:10-0:20'. Repeatable.")
    A = ap.parse_args()
    t0 = time.time()
    root = os.path.abspath(A.root)
    work = os.path.abspath(A.work)
    thumbs = os.path.join(work, "thumbs"); a16 = os.path.join(work, "audio16k")
    for d in (work, thumbs, a16):
        os.makedirs(d, exist_ok=True)

    items = walk(root, skip_abs=[work])
    if A.only:
        items = [i for i in items if A.only.lower() in i[0].lower()]
    windows = parse_windows(A.window)

    # ---- canonical asset ids: stable across re-runs and renames ----
    # asset-ids.json maps rel path -> id and is only ever appended to. A
    # rename-map.json in the work dir or root ({old_rel: new_rel}, written by
    # the rename/organize step) carries an id across a rename, so the identity
    # of an asset never depends on what the file happens to be called today.
    ids_path = os.path.join(work, "asset-ids.json")
    ids = json.load(open(ids_path)) if os.path.exists(ids_path) else {}
    rmap = {}
    for cand in (os.path.join(work, "rename-map.json"),
                 os.path.join(root, "rename-map.json")):
        if os.path.exists(cand):
            try:
                rmap.update(json.load(open(cand)))
            except Exception:
                pass
    for old_rel, new_rel in rmap.items():
        if old_rel in ids and new_rel not in ids:
            ids[new_rel] = ids[old_rel]
    next_n = 1 + max([int(v[1:]) for v in ids.values()
                      if v[:1] == "A" and v[1:].isdigit()] or [0])
    for rel, _f, _k in items:
        if rel not in ids:
            ids[rel] = "A%02d" % next_n
            next_n += 1
    json.dump(ids, open(ids_path, "w"), indent=1)

    # ---- inventory (cheap, always fully refreshed) ----
    inv_path = os.path.join(work, "inventory.json")
    inv = json.load(open(inv_path)) if os.path.exists(inv_path) and not A.force else {}
    for rel, full, k in items:
        if rel not in inv:
            # text files have no streams; ffprobe would only waste a subprocess
            inv[rel] = {"kind": k, **(probe_text(full) if k == "text" else probe(full))}
    json.dump(inv, open(inv_path, "w"), indent=1)

    remaining = 0

    # ---- contact sheets, one file at a time, respecting the budget ----
    for rel, full, k in items:
        if k != "video":
            continue
        dst = os.path.join(thumbs, os.path.splitext(os.path.basename(rel))[0][:44] + "_sheet.jpg")
        if os.path.exists(dst) and not A.force:
            continue
        if time.time() - t0 > A.budget:
            remaining += 1
            continue
        res = contact_sheet(full, dst, A.frames, window=window_for(rel, windows))
        if res:
            inv[rel]["temporal"] = {
                "duration": res["dur"], "method": "seek-sample",
                "frames_sampled": len(res["times"]),
                "sampled_at": res["times"],
                "first_sampled_s": res["times"][0], "last_sampled_s": res["times"][-1]}
            inv[rel]["dhash"] = ["%016x" % h for h in res["hashes"]]
            inv[rel]["inspection"] = (
                {"level": "partial",
                 "windows": [{"t0": res["t0"], "t1": res["t1"], "by": "creator"}]}
                if res["windowed"] else {"level": "full"})
        print(("sheet  " if res else "FAILED ") + rel)

    # ---- image pages (fast; do them in one go once) ----
    imgs = [i for i in items if i[2] == "image"]
    for rel, full, _k in imgs:
        if "dhash" in inv[rel] and not A.force:
            continue
        try:
            from PIL import Image
            im = Image.open(full)
            try: im.seek(0)
            except Exception: pass
            inv[rel]["dhash"] = ["%016x" % dhash64(im.convert("RGB"))]
            inv[rel]["inspection"] = {"level": "full"}
        except Exception:
            pass
    if imgs and (A.force or not os.path.exists(os.path.join(thumbs, "IMAGES_page1.jpg"))):
        if time.time() - t0 <= A.budget:
            for p in image_pages(root, imgs, thumbs):
                print("pages  " + os.path.basename(p))
        else:
            remaining += 1

    # ---- audio downsample ----
    for rel, full, k in items:
        if k != "audio":
            continue
        dst = os.path.join(a16, os.path.splitext(os.path.basename(rel))[0] + ".wav")
        if os.path.exists(dst) and not A.force:
            continue
        if time.time() - t0 > A.budget:
            remaining += 1
            continue
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", full, "-ar", "16000",
                        "-ac", "1", "-c:a", "pcm_s16le", dst], capture_output=True, timeout=60)
        print("audio  " + rel)

    # ---- inspection level for anything never sampled ----
    for rel, _f, k in items:
        if "inspection" not in inv[rel]:
            inv[rel]["inspection"] = (
                {"level": "full"} if k in ("audio", "text") and inv[rel]
                else {"level": "unresolved"})
    # unknown technical properties are stated, never guessed
    for rel, _f, k in items:
        if k == "video" and not inv[rel].get("v"):
            inv[rel]["specs_unresolved"] = True

    # ---- shot groups: confident edges group, ambiguous edges go to review ----
    hashes = {rel: [int(h, 16) for h in inv[rel]["dhash"]]
              for rel, _f, _k in items if inv[rel].get("dhash")}
    review = []
    if len(hashes) > 1:
        group_of, verdict, review, nearest = shot_groups(hashes)
        for rel in hashes:
            if rel in group_of:
                inv[rel]["shot_group"] = group_of[rel]
                inv[rel]["shot_group_verdict"] = verdict[rel]
            if rel in nearest:
                inv[rel]["shot_group_nearest"] = {
                    "asset": ids.get(nearest[rel][0], nearest[rel][0]),
                    "distance": nearest[rel][1]}
        json.dump({"same_max": SAME_MAX, "uncertain_max": UNCERTAIN_MAX,
                   "review": review},
                  open(os.path.join(work, "shot-groups.json"), "w"), indent=1)
        for pr in review:
            print("ASK THE CREATOR — %s vs %s look related (distance %d): same "
                  "setup, or meaningfully different? Do not assert either way."
                  % (pr["a"], pr["b"], pr["distance"]))
    json.dump(inv, open(inv_path, "w"), indent=1)

    # ---- skeleton for the judgement pass ----
    # `use`, `beat` and `binds_to` are RECOMMENDATIONS — /real-storyboarding
    # owns the editorial decision. `shows` and everything from the probe are
    # facts. `temporal_notes` is where the judge writes what the frames show
    # over time (start state, end state, notable moments with rough times).
    skel = {"project": os.path.basename(root), "root": root,
            "generated": time.strftime("%Y-%m-%d"),
            "script_beats": [{"id": "B1", "take": "", "dur": 0, "gist": ""}],
            "assets": [{"id": ids[rel], "f": rel, "k": inv[rel]["kind"],
                        "role": "", "shows": "", "use": "", "beat": "",
                        "binds_to": "", "tags": [],
                        "inspection": inv[rel].get("inspection"),
                        "temporal": inv[rel].get("temporal"),
                        "temporal_notes": {"start_state": "", "end_state": "",
                                           "moments": []},
                        **({"shot_group": inv[rel]["shot_group"],
                            "shot_group_verdict": inv[rel]["shot_group_verdict"]}
                           if inv[rel].get("shot_group") else {})}
                       for rel, _f, _k in items]}
    sp = os.path.join(work, "skeleton.json")
    if not os.path.exists(sp) or A.force:
        json.dump(skel, open(sp, "w"), indent=1)
        print("skeleton " + sp)

    print(f"\n{len(items)} assets · {sum(1 for i in items if i[2]=='video')} video · "
          f"{sum(1 for i in items if i[2]=='image')} image · "
          f"{sum(1 for i in items if i[2]=='audio')} audio · "
          f"{sum(1 for i in items if i[2]=='text')} text · {time.time()-t0:.0f}s")
    print("MORE WORK REMAINS — run again" if remaining else "ALL DONE")


if __name__ == "__main__":
    main()
