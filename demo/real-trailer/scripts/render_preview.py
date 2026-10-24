#!/usr/bin/env python3
"""render_preview.py — a preview movie of the compiled OpenTimelineIO timeline, with ffmpeg.

    python3 scripts/render_preview.py timeline/real-trailer.otio preview/real-trailer-preview.mp4 \
        [--media-root media] [--crf 20]

REAL ends at the timeline; the editor renders. This script exists so the
trailer can be watched before an editor is opened, and so the landing page has
a movie while the editor render is on its way. It reads the .otio the compiler
wrote (through the benchmark's independent reader for the picture, and the
file itself for the sound), so what it draws is the exported timeline, not the
storyboard:

  * the primary storyline in order, each clip trimmed at its in-point, fitted
    into the sequence (letterboxed; a `transform.scale` from a fill layer is
    applied as the editors would);
  * a cross dissolve where the timeline has one, with the same media handles
    the editors use;
  * stills and the rasterised captions as overlays on their frames;
  * every audio clip at its level (clips at -60 dB are left out; a ducked bed
    is held at its duck level, a simplification the editors do not share: they
    get the envelope).

It is a preview. Frame-exact parity with Final Cut Pro or DaVinci Resolve is
measured by scripts in demo/paganini-no23, not promised here.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "bench"))
import otio_edl  # noqa: E402  (the independent reader)


def sh(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit("ffmpeg failed (%d):\n  %s\n%s" % (r.returncode, " ".join(str(c) for c in cmd)[:600],
                                                   r.stderr.strip()[-1500:]))


def url_path(url):
    return unquote(urlparse(url).path) if url.startswith("file:") else url


def media_ref(clip):
    mr = clip.get("media_reference")
    if not mr and clip.get("media_references"):
        key = clip.get("active_media_reference_key") or "DEFAULT_MEDIA"
        mr = clip["media_references"].get(key) or next(iter(clip["media_references"].values()))
    return mr or {}


def local(path, media_root):
    """A timeline path as reachable here: by name under media_root/{Videos,Images,Audio}
    when given, else as written."""
    if media_root:
        name = os.path.basename(path)
        for sub in ("Videos", "Images", "Audio", ""):
            cand = os.path.join(media_root, sub, name) if sub else os.path.join(media_root, name)
            if os.path.exists(cand):
                return cand
    return path


def fit_filter(label, w, h, scale=1.0):
    """scale to fit the frame, then scale out by `scale` (a fill transform) and crop."""
    f = ("scale=%d:%d:force_original_aspect_ratio=decrease:flags=lanczos,"
         "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=black" % (w, h, w, h))
    if abs(scale - 1.0) > 0.005:
        f += ",scale=iw*%.4f:ih*%.4f:flags=lanczos,crop=%d:%d" % (scale, scale, w, h)
    return "[%s]%s,setsar=1,format=yuv420p" % (label, f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("otio")
    ap.add_argument("out")
    ap.add_argument("--media-root", default=None)
    ap.add_argument("--crf", type=int, default=20)
    a = ap.parse_args()
    otio_path = os.path.abspath(a.otio)
    edl = otio_edl.parse(otio_path)
    raw = json.load(open(otio_path))
    fps, W, H, total_f = edl["fps"], edl["w"], edl["h"], edl["total_f"]
    tracks = raw["tracks"]["children"]

    # ---- picture: paths and transforms per clip, from the file itself ----
    clip_meta = {}          # (track, start_f) -> {path, transform_scale}
    for t in tracks:
        if t.get("kind") != "Video":
            continue
        cur = 0
        for c in t["children"]:
            schema = c.get("OTIO_SCHEMA", "")
            if schema.startswith("Transition"):
                continue
            dur = int(round(c["source_range"]["duration"]["value"]))
            if schema.startswith("Clip"):
                mr = media_ref(c)
                tr = ((c.get("metadata") or {}).get("REAL") or {}).get("transform") or {}
                sc = tr.get("scale", 1.0)
                if isinstance(sc, (list, tuple)):
                    sc = sc[0]
                clip_meta[(t.get("name"), cur)] = {"path": url_path(mr.get("target_url") or ""),
                                                   "scale": float(sc or 1.0),
                                                   "name": c.get("name")}
            cur += dur
    base = sorted([e for e in edl["events"] if e["z"] == 0], key=lambda e: e["f0"])
    overlays = sorted([e for e in edl["events"] if e["z"] > 0], key=lambda e: (e["z"], e["f0"]))
    trans = {tr["f"]: tr for tr in edl.get("transitions") or []}

    tmp = Path(tempfile.mkdtemp(prefix="real-preview-"))
    segs = []     # rendered base segments: (file, f0, f1, extra_tail_f, extra_head_f)
    for i, e in enumerate(base):
        n = e["f1"] - e["f0"]
        head = trans.get(e["f0"], {}).get("out_f", 0) if i else 0        # dissolve into this clip
        tail = trans.get(e["f1"], {}).get("in_f", 0) if i + 1 < len(base) else 0  # dissolve out of it
        meta = next((m for (tn, s), m in clip_meta.items() if tn == "V1" and s == e["f0"]), {})
        path = local(meta.get("path", ""), a.media_root)
        seg = tmp / ("base%03d.mp4" % i)
        if e["kind"] == "video":
            if not os.path.exists(path):
                sys.exit("missing media for %s: %s" % (e.get("name"), path))
            src_in = int(e.get("src_in", 0)) - head
            if src_in < 0:
                sys.exit("%s: a dissolve needs %d frames before its in-point" % (e.get("name"), -src_in))
            sh(["ffmpeg", "-v", "error", "-y", "-ss", "%.6f" % (src_in / fps), "-i", path,
                "-frames:v", str(n + head + tail), "-an", "-filter_complex",
                fit_filter("0:v", W, H, meta.get("scale", 1.0)) + ",fps=%d[v]" % fps, "-map", "[v]",
                "-r", str(fps), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(seg)])
        elif e["kind"] == "image":
            if not os.path.exists(path):
                sys.exit("missing still for %s: %s" % (e.get("name"), path))
            sh(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(fps), "-i", path,
                "-frames:v", str(n + head + tail), "-filter_complex",
                fit_filter("0:v", W, H, meta.get("scale", 1.0)) + "[v]", "-map", "[v]",
                "-r", str(fps), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(seg)])
        else:   # gap or anything else: black
            sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=%dx%d:r=%d" % (W, H, fps),
                "-frames:v", str(n + head + tail), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(seg)])
        segs.append((seg, e["f0"], e["f1"], head, tail))

    # ---- join the base: a dissolve where the timeline has one, a cut elsewhere ----
    inputs, chain, cur, acc_len = [], [], None, 0
    for i, (seg, f0, f1, head, tail) in enumerate(segs):
        inputs += ["-i", str(seg)]
        n = f1 - f0 + head + tail
        if cur is None:
            cur, acc_len = "[%d:v]" % i, n
            continue
        prev_tail = segs[i - 1][4]
        if prev_tail or head:
            d = (prev_tail + head) / fps
            off = (acc_len - prev_tail - head) / fps
            # concat leaves a microsecond timebase; xfade wants both inputs on one
            chain.append("%ssettb=AVTB[p%d];[%d:v]settb=AVTB[q%d];[p%d][q%d]xfade=transition=fade:"
                         "duration=%.6f:offset=%.6f[x%d]" % (cur, i, i, i, i, i, d, off, i))
            cur = "[x%d]" % i
            acc_len = acc_len + n - prev_tail - head
        else:
            chain.append("%s[%d:v]concat=n=2:v=1:a=0[x%d]" % (cur, i, i))
            cur = "[x%d]" % i
            acc_len += n
    chain_str = ";".join(chain) if chain else None
    joined = tmp / "base.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs
    if chain_str:
        cmd += ["-filter_complex", chain_str, "-map", cur]
    cmd += ["-frames:v", str(total_f), "-r", str(fps), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(joined)]
    sh(cmd)

    # ---- overlays: stills fitted and centred, rasterised captions full-frame ----
    ov_inputs, ov_chain, cur = [], [], "[0:v]"
    k = 1
    for e in overlays:
        if e["kind"] == "text":
            path = url_path(e.get("rendered") or "")
        else:
            meta = next((m for (tn, s), m in clip_meta.items() if s == e["f0"] and
                         os.path.basename(m["path"]).startswith(e["asset"])), {})
            path = meta.get("path", "")
        path = local(path, a.media_root)
        if not path or not os.path.exists(path):
            print("  overlay %s has no file here (%s) — skipped" % (e.get("name"), path), file=sys.stderr)
            continue
        ov_inputs += ["-i", path]
        pre = "[%d:v]scale=%d:%d:force_original_aspect_ratio=decrease,format=rgba[o%d]" % (k, W, H, k)
        ov_chain.append(pre)
        ov_chain.append("%s[o%d]overlay=(W-w)/2:(H-h)/2:enable='between(n,%d,%d)'[c%d]"
                        % (cur, k, e["f0"], e["f1"] - 1, k))
        cur = "[c%d]" % k
        k += 1
    picture = tmp / "picture.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(joined)] + ov_inputs
    if ov_chain:
        cmd += ["-filter_complex", ";".join(ov_chain), "-map", cur]
    cmd += ["-frames:v", str(total_f), "-r", str(fps), "-c:v", "libx264", "-crf", str(a.crf),
            "-pix_fmt", "yuv420p", str(picture)]
    sh(cmd)

    # ---- sound: every audio clip at its level, from the file itself ----
    aud_inputs, aud_chain, labels = [], [], []
    k = 0
    for t in tracks:
        if t.get("kind") != "Audio":
            continue
        cur_f = 0
        for c in t["children"]:
            dur = int(round(c["source_range"]["duration"]["value"]))
            if c.get("OTIO_SCHEMA", "").startswith("Clip"):
                mr = media_ref(c)
                meta = (c.get("metadata") or {}).get("REAL") or {}
                vol = float(meta.get("volume_db") or 0)
                duck = meta.get("ducking") or {}
                if isinstance(duck, dict) and duck.get("duck_db") is not None:
                    vol += float(duck["duck_db"])
                elif isinstance(duck, (int, float)):
                    vol += float(duck)
                path = local(url_path(mr.get("target_url") or ""), a.media_root)
                if vol > -50 and os.path.exists(path):
                    start = c["source_range"]["start_time"]["value"] / fps
                    aud_inputs += ["-ss", "%.6f" % start, "-t", "%.6f" % (dur / fps), "-i", path]
                    aud_chain.append("[%d:a]volume=%.2fdB,aresample=48000,adelay=%d|%d,apad[a%d]"
                                     % (k + 1, vol, int(cur_f / fps * 1000), int(cur_f / fps * 1000), k))
                    labels.append("[a%d]" % k)
                    k += 1
            cur_f += dur
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if labels:
        mix = "".join(labels) + "amix=inputs=%d:normalize=0:duration=longest,atrim=0:%.6f[a]" % (len(labels), total_f / fps)
        sh(["ffmpeg", "-v", "error", "-y", "-i", str(picture)] + aud_inputs +
           ["-filter_complex", ";".join(aud_chain + [mix]), "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])
    else:
        sh(["ffmpeg", "-v", "error", "-y", "-i", str(picture), "-c:v", "copy", "-an", out])
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                            "-show_entries", "stream=nb_read_frames,width,height", "-of", "csv=p=0", out],
                           capture_output=True, text=True).stdout.strip()
    print("wrote %s — %s (timeline %d frames at %d fps, %d base clips, %d overlays, %d audio clips)"
          % (out, probe, total_f, fps, len(base), k and len(labels) or 0, len(labels)))


if __name__ == "__main__":
    main()
