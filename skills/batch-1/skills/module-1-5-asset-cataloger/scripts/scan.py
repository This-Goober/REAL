#!/usr/bin/env python3
"""
scan.py — inventory an asset folder and build the cheap visual proxies a
catalog needs. Runs WHERE THE MEDIA LIVES so nothing large ever moves.

    python3 scan.py <assets_root> <work_dir> [--budget 35] [--only SUBSTR]
                    [--frames 16] [--force]

Produces, inside <work_dir>:
    inventory.json      every file with ffprobe specs
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
SKIP_DIRS = {"cache", "renders", "autosave", "__pycache__", ".git"}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def kind(p):
    e = os.path.splitext(p)[1].lower()
    return "video" if e in VID else "image" if e in IMG else "audio" if e in AUD else "other"


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


def walk(root):
    out = []
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in sorted(files):
            if fn.startswith("."):
                continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, root)
            k = kind(fn)
            if k != "other":
                out.append((rel, full, k))
    return out


def contact_sheet(src, dst, n, width=200, cols=4):
    from PIL import Image, ImageDraw, ImageFont
    info = probe(src)
    dur = info.get("dur") or 0
    if dur <= 0:
        return False
    tmp = "/tmp/_cs.jpg"
    tiles = []
    for i in range(n):
        t = dur * (i + 0.5) / n
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
        os.remove(tmp)
    if not tiles:
        return False
    tw, th = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    sh = Image.new("RGB", (cols * tw, rows * th + 24), (20, 20, 24))
    for i, im in enumerate(tiles):
        sh.paste(im.resize((tw, th)), ((i % cols) * tw, (i // cols) * th + 24))
    d = ImageDraw.Draw(sh)
    try: f = ImageFont.truetype(FONT, 15)
    except Exception: f = ImageFont.load_default()
    d.text((6, 4), f"{os.path.basename(src)[:60]}   {dur:.1f}s", fill=(255, 255, 255), font=f)
    sh.save(dst, quality=72)
    return True


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
    A = ap.parse_args()
    t0 = time.time()
    root = os.path.abspath(A.root)
    work = os.path.abspath(A.work)
    thumbs = os.path.join(work, "thumbs"); a16 = os.path.join(work, "audio16k")
    for d in (work, thumbs, a16):
        os.makedirs(d, exist_ok=True)

    items = walk(root)
    if A.only:
        items = [i for i in items if A.only.lower() in i[0].lower()]

    # ---- inventory (cheap, always fully refreshed) ----
    inv_path = os.path.join(work, "inventory.json")
    inv = json.load(open(inv_path)) if os.path.exists(inv_path) and not A.force else {}
    for rel, full, k in items:
        if rel not in inv:
            inv[rel] = {"kind": k, **probe(full)}
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
        ok = contact_sheet(full, dst, A.frames)
        print(("sheet  " if ok else "FAILED ") + rel)

    # ---- image pages (fast; do them in one go once) ----
    imgs = [i for i in items if i[2] == "image"]
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

    # ---- skeleton for the judgement pass ----
    skel = {"project": os.path.basename(root), "root": root,
            "generated": time.strftime("%Y-%m-%d"),
            "script_beats": [{"id": "B1", "take": "", "dur": 0, "gist": ""}],
            "assets": [{"f": rel, "k": inv[rel]["kind"], "role": "", "shows": "",
                        "use": "", "beat": ""} for rel, _f, _k in items]}
    sp = os.path.join(work, "skeleton.json")
    if not os.path.exists(sp) or A.force:
        json.dump(skel, open(sp, "w"), indent=1)
        print("skeleton " + sp)

    print(f"\n{len(items)} assets · {sum(1 for i in items if i[2]=='video')} video · "
          f"{sum(1 for i in items if i[2]=='image')} image · "
          f"{sum(1 for i in items if i[2]=='audio')} audio · {time.time()-t0:.0f}s")
    print("MORE WORK REMAINS — run again" if remaining else "ALL DONE")


if __name__ == "__main__":
    main()
