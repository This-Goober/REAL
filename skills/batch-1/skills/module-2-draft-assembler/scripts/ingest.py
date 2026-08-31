#!/usr/bin/env python3
"""Probe and thumbnail a folder of media -> media.json.

Everything downstream refers to files by the stable `id` this assigns, not by
filename, so renaming a file at the source doesn't invalidate a draft.

    python3 ingest.py media/ --out media.json --thumbs thumbs/

Thumbnails are embedded as data URIs so STORYBOARD.html stays a single file
the director can open anywhere. Video gets a 4-frame contact strip (one frame
per quarter) because a single poster frame is a bad way to recognise a take.
"""
import argparse, base64, io, json, os, re, shutil, subprocess, sys

VIDEO = {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".webm"}
IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".tif", ".tiff", ".bmp"}
AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".aiff", ".flac"}

def have(cmd):
    return shutil.which(cmd) is not None

def slug(name):
    s = re.sub(r"[^a-z0-9]+", "_", os.path.splitext(name)[0].lower()).strip("_")
    return s[:40] or "asset"

def ffprobe(path):
    if not have("ffprobe"):
        return {}
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=60).stdout
        d = json.loads(out)
    except Exception:
        return {}
    info = {}
    fmt = d.get("format", {})
    if fmt.get("duration"):
        try: info["duration"] = round(float(fmt["duration"]), 3)
        except ValueError: pass
    for s in d.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in info:
            info["width"], info["height"] = s.get("width"), s.get("height")
            rate = s.get("r_frame_rate", "")
            if "/" in rate:
                n, den = rate.split("/")
                if float(den): info["fps"] = round(float(n) / float(den), 3)
        if s.get("codec_type") == "audio":
            info["has_audio"] = True
    return info

def data_uri(path, mime="image/jpeg"):
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()

def thumb_image(src, dst, w=360):
    if have("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                        "-vf", f"scale={w}:-1", "-frames:v", "1", dst],
                       capture_output=True, timeout=120)
        return os.path.exists(dst)
    try:
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((w, w * 4))
        im.save(dst, "JPEG", quality=82)
        return True
    except Exception:
        return False

def thumb_video(src, dst, dur, w=360, n=4):
    """Contact strip: n frames sampled across the clip, tiled horizontally."""
    if not have("ffmpeg") or not dur:
        return False
    tmpdir = dst + ".frames"
    os.makedirs(tmpdir, exist_ok=True)
    got = []
    for i in range(n):
        t = max(0.0, dur * (i + 0.5) / n)
        f = os.path.join(tmpdir, f"{i}.jpg")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", src,
                        "-vf", f"scale={w // n}:-1", "-frames:v", "1", f],
                       capture_output=True, timeout=120)
        if os.path.exists(f):
            got.append(f)
    ok = False
    if got:
        lst = os.path.join(tmpdir, "list.txt")
        with open(lst, "w") as fh:
            for g in got:
                fh.write(f"file '{os.path.basename(g)}'\n")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", got[0]]
                           + sum([["-i", g] for g in got[1:]], [])
                           + ["-filter_complex", f"hstack=inputs={len(got)}", dst],
                           capture_output=True, timeout=120)
        ok = os.path.exists(dst)
        if not ok and got:
            shutil.copy(got[0], dst)
            ok = True
    shutil.rmtree(tmpdir, ignore_errors=True)
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", default="media.json")
    ap.add_argument("--thumbs", default="thumbs")
    ap.add_argument("--no-embed", action="store_true",
                    help="reference thumbnail paths instead of embedding data URIs")
    a = ap.parse_args()

    os.makedirs(a.thumbs, exist_ok=True)
    items, seen = [], {}
    for root, _, files in os.walk(a.folder):
        for fn in sorted(files):
            if fn.startswith("."):
                continue
            ext = os.path.splitext(fn)[1].lower()
            kind = ("video" if ext in VIDEO else "image" if ext in IMAGE
                    else "audio" if ext in AUDIO else None)
            if kind is None:
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, a.folder)
            base = slug(fn)
            mid = base
            i = 2
            while mid in seen:
                mid = f"{base}_{i}"; i += 1
            seen[mid] = True

            info = ffprobe(path)
            if kind == "image":
                # some JPEGs report a spurious sub-second container "duration"
                # (JFIF/EXIF artifact) that reads like a real playback length
                # downstream and false-positives an overrun check. A still has
                # no natural duration — it holds for whatever the beat asks.
                info.pop("duration", None)
            item = {"id": mid, "file": rel, "kind": kind,
                    "bytes": os.path.getsize(path), **info}

            if kind in ("video", "image"):
                tp = os.path.join(a.thumbs, mid + ".jpg")
                ok = (thumb_video(path, tp, info.get("duration", 0))
                      if kind == "video" else thumb_image(path, tp))
                if ok:
                    item["thumb"] = (tp if a.no_embed else data_uri(tp))
                    item["thumb_kind"] = "strip" if kind == "video" else "still"
            items.append(item)

    warn = []
    if not have("ffprobe"):
        warn.append("ffprobe not found — no durations or dimensions probed")
    if not have("ffmpeg"):
        warn.append("ffmpeg not found — video thumbnails skipped")
    for it in items:
        if it["kind"] == "video" and "duration" not in it:
            warn.append(f"{it['file']}: duration unknown; a clip placed from it needs an explicit duration")
        if it["kind"] == "image" and it.get("file", "").lower().endswith((".webp", ".gif")):
            warn.append(f"{it['file']}: Final Cut is unreliable with this format — convert to PNG before hand-off")

    out = {"root": os.path.abspath(a.folder), "count": len(items),
           "warnings": warn, "media": items}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)

    print(f"{len(items)} files -> {a.out}")
    for k in ("video", "image", "audio"):
        n = sum(1 for i in items if i["kind"] == k)
        if n: print(f"  {k:6} {n}")
    for w in warn:
        print("  ! " + w, file=sys.stderr)

if __name__ == "__main__":
    main()
