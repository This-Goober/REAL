#!/usr/bin/env python3
"""compare_exports.py — measure how closely two editors rendered the same REAL storyboard.

    python3 compare_exports.py A.mov B.mp4 timeline.otio OUT_DIR
        [--label-a "Final Cut Pro (FCPXML)"] [--label-b "DaVinci Resolve (OTIO)"]
        [--band 740 1080]

A and B are the two native exports. The .otio is what the second editor
imported; its event list (frame-identical to the FCPXML by bench/otio_edl.py)
is the expected timing of every cut and caption. Both exports are read at the
timeline's frame rate; a constant frame offset between them is detected from
the cuts and removed before the paired metrics.

Outputs in OUT_DIR
  report.json, COMPARISON.md     everything below, as data and as a table
  frame-metrics.csv              per frame: MAD, SSIM, PSNR, caption-band ink in A and B
  cuts.csv                       expected cut frame, detected in A and B, offsets
  captions.csv                   expected on/off, detected in A and B, glyph box sizes
  captions-sheet.png             the caption band from A over B at each caption midpoint
  side-by-side.mp4               A | B | |A−B|×4, 540×960 each, A's audio

Measures
  geometry and length of each export
  cut agreement: detected cut frame minus expected, per cut, per export
  caption timing: detected on/off minus expected, per caption, per export
  caption appearance: yellow glyph box width/height in B relative to A
  picture: mean absolute luma difference, SSIM and PSNR per frame; summarised
           for all frames, frames with a caption, frames without
  audio: lag between the two mixes (ms) and level difference (dB) in three windows
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "bench"))
import otio_edl  # noqa: E402

AN_W, AN_H = 270, 480            # analysis size for timing (1/4 of 1080x1920)
PAIR_W, PAIR_H = 135, 240        # stored luma for the paired MAD
FONT = "/System/Library/Fonts/Helvetica.ttc"


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw).stdout


def probe(path):
    out = json.loads(sh(["ffprobe", "-v", "error", "-show_entries",
                         "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,"
                         "pix_fmt,color_space,color_transfer,sample_rate,channels",
                         "-of", "json", str(path)]))
    v = next(s for s in out["streams"] if s["codec_type"] == "video")
    a = next((s for s in out["streams"] if s["codec_type"] == "audio"), {})
    num, den = v["r_frame_rate"].split("/")
    return {"file": str(path), "width": int(v["width"]), "height": int(v["height"]),
            "fps": float(num) / float(den), "codec": v["codec_name"], "pix_fmt": v.get("pix_fmt"),
            "color_space": v.get("color_space"), "color_transfer": v.get("color_transfer"),
            "duration_s": float(out["format"]["duration"]),
            "audio": {"codec": a.get("codec_name"), "rate": a.get("sample_rate"),
                      "channels": a.get("channels")}}


def yellow_mask(rgb):
    r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
    return (r > 200) & (g > 170) & (b < 110) & ((r - b) > 110)


# --captions-from-timeline: each caption's band and ink colour come from the timeline
FCP_TITLE_SCALE = 1.73      # Final Cut draws a title in a 1080x1920 project at 1.73x its point size


def _hsv(rgb):
    a = rgb.astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-9), 0.0)
    return h, s, mx


def ink_mask_for(color):
    """The pixels that are a caption's ink, from the colour the timeline declares.
    Yellow keeps the tutorial's mask. Any other saturated colour is matched by
    hue (within 10 degrees), saturation and brightness, which keeps a vermilion
    caption apart from a violin's wood; an unsaturated one by brightness."""
    if not color:
        return yellow_mask
    ref = np.array([[[int(round(float(c) * 255)) for c in color[:3]]]], dtype=np.uint8)
    if ref[0, 0, 0] > 200 and ref[0, 0, 1] > 170 and ref[0, 0, 2] < 110:
        return yellow_mask
    h0, s0, v0 = (float(x[0, 0]) for x in _hsv(ref))

    def mask(rgb):
        h, s, v = _hsv(rgb)
        if s0 < 0.2:
            return (s <= 0.2) & (v >= 0.85 * v0)
        dh = np.abs(((h - h0) + 180.0) % 360.0 - 180.0)
        return (dh <= 10.0) & (s >= 0.75 * s0) & (v >= 0.6 * v0)
    return mask


def caption_band(c, height):
    """Rows of the full frame a caption occupies, the way Final Cut lays it out:
    the first line's baseline at the caption's position (px from the centre, y
    up), each further line 1.25 em below, ascenders 0.75 em above the first and
    descenders 0.25 em below the last (measured on the trailer's render), a
    third of a line of air, clipped to the frame — so a line that runs off the
    frame shows as ink on the frame's edge row."""
    lines = (c.get("text") or "").count("\n") + 1
    px = float(c.get("font_size") or 40) * FCP_TITLE_SCALE
    row0 = height / 2.0 - float((c.get("position") or [0, 0])[1])
    top = row0 - 0.75 * px - 0.35 * px
    bottom = row0 + max(lines - 1, 1) * 1.25 * px + 0.25 * px + 0.35 * px
    return (max(0, int(top)), min(height, int(bottom)))


def stream_stats(path, fps, specs):
    """Decode at analysis size; return per-frame luma delta, ink in each
    (band rows, mask) spec, and stored luma."""
    # -map 0:v:0 — the Final Cut export carries a cover-art MJPEG stream too
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf",
           "fps=%g,scale=%d:%d:flags=area" % (fps, AN_W, AN_H),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10 ** 7)
    n = AN_W * AN_H * 3
    deltas, lumas = [], []
    inks = [[] for _ in specs]
    prev = None
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        rgb = np.frombuffer(buf, dtype=np.uint8).reshape(AN_H, AN_W, 3)
        y = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)
        deltas.append(0.0 if prev is None else float(np.abs(y - prev).mean()))
        prev = y
        for k, ((y0, y1), mask) in enumerate(specs):
            inks[k].append(int(mask(rgb[y0:y1]).sum()))
        lumas.append(y.reshape(PAIR_H, 2, PAIR_W, 2).mean(axis=(1, 3)).astype(np.uint8))
    p.stdout.close()
    p.wait()
    return np.array(deltas), [np.array(i) for i in inks], np.stack(lumas) if lumas else np.zeros((0, PAIR_H, PAIR_W))


def detect_cut(delta, expected, radius=6):
    lo, hi = max(1, expected - radius), min(len(delta) - 1, expected + radius)
    if hi <= lo:
        return None, 0.0, 0.0
    win = delta[lo:hi + 1]
    i = int(np.argmax(win)) + lo
    around = np.concatenate([delta[max(1, lo - 30):lo], delta[hi + 1:hi + 31]])
    base = float(np.median(around)) if len(around) else 0.0
    return i, float(delta[i]), base


def detect_caption(ink, f0, f1, radius=6):
    """Onset/offset of a caption around the expected [f0, f1) from band ink."""
    lo, hi = max(0, f0 - radius), min(len(ink), f1 + radius)
    inside = ink[f0:min(f1, len(ink))]
    if len(inside) == 0:
        return None
    level = float(np.median(inside))
    if level < 20:
        return {"found": False, "level": level}
    thr = 0.3 * level
    on = next((i for i in range(lo, hi) if ink[i] > thr), None)
    off = next((i for i in range(hi - 1, lo - 1, -1) if ink[i] > thr), None)
    return {"found": on is not None, "level": level, "on": on,
            "off": None if off is None else off + 1}


def grab(path, frame, fps, out_png):
    sh(["ffmpeg", "-v", "error", "-y", "-ss", "%.4f" % ((frame + 0.5) / fps), "-i", str(path),
        "-map", "0:v:0", "-frames:v", "1", str(out_png)])
    return Image.open(out_png).convert("RGB")


def glyph_box(img, band, mask=yellow_mask):
    a = np.asarray(img.crop((0, band[0], img.width, band[1])))
    m = mask(a)
    ys, xs = np.where(m)
    if len(ys) < 30:
        return None
    rows = np.bincount(ys, minlength=a.shape[0])
    cols = np.bincount(xs, minlength=a.shape[1])
    gy = np.where(rows >= 4)[0]
    gx = np.where(cols >= 2)[0]
    return {"x0": int(gx.min()), "x1": int(gx.max()), "y0": int(gy.min()) + band[0],
            "y1": int(gy.max()) + band[0], "w": int(gx.max() - gx.min() + 1),
            "h": int(gy.max() - gy.min() + 1), "ink": int(m.sum())}


def ffmpeg_quality(a, b, fps, shift_b, out_dir):
    """SSIM and PSNR per frame at 540x960, B trimmed by shift_b frames."""
    res = {}
    for name in ("ssim", "psnr"):
        log = out_dir / ("%s.log" % name)
        graph = ("[0:v]fps=%g,scale=540:960:flags=area[a];"
                 "[1:v]fps=%g,trim=start_frame=%d,setpts=PTS-STARTPTS,scale=540:960:flags=area[b];"
                 "[a][b]%s=stats_file=%s" % (fps, fps, max(0, shift_b), name, log))
        if shift_b < 0:
            graph = graph.replace("[0:v]fps=%g," % fps,
                                  "[0:v]fps=%g,trim=start_frame=%d,setpts=PTS-STARTPTS," % (fps, -shift_b))
            graph = graph.replace("trim=start_frame=0,setpts=PTS-STARTPTS,", "")
        sh(["ffmpeg", "-v", "error", "-i", str(a), "-i", str(b), "-lavfi", graph, "-f", "null", "-"])
        vals = []
        for line in open(log):
            m = re.search(r"All:([0-9.]+)", line) if name == "ssim" else re.search(r"psnr_avg:([0-9.inf]+)", line)
            if m:
                v = m.group(1)
                vals.append(float("inf") if v == "inf" else float(v))
        res[name] = np.array(vals)
    return res["ssim"], res["psnr"]


def audio(path, t0, dur, sr=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(dur), "-i", str(path),
                          "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    return x - x.mean()


def audio_compare(a, b, windows, sr=16000):
    out = []
    for t0 in windows:
        xa, xb = audio(a, t0, 6), audio(b, t0, 6)
        n = min(len(xa), len(xb))
        if n < sr:
            out.append({"t0": t0, "note": "no audio"})
            continue
        xa, xb = xa[:n], xb[:n]
        best = (0, -1.0)
        for lag in range(-3200, 3201, 4):           # ±200 ms
            c = np.dot(xa[lag:], xb[:n - lag]) if lag >= 0 else np.dot(xa[:n + lag], xb[-lag:])
            c /= (np.linalg.norm(xa) * np.linalg.norm(xb) + 1e-9)
            if c > best[1]:
                best = (lag, c)
        rms_a, rms_b = np.sqrt((xa ** 2).mean()) + 1e-9, np.sqrt((xb ** 2).mean()) + 1e-9
        out.append({"t0": t0, "lag_ms": round(best[0] * 1000.0 / sr, 2), "corr": round(best[1], 4),
                    "level_b_minus_a_db": round(20 * np.log10(rms_b / rms_a), 2)})
    return out


def label_strip(width, labels, h=44):
    im = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 26)
    cell = width // len(labels)
    for i, t in enumerate(labels):
        w = d.textlength(t, font=f)
        x = i * cell + (cell - w) / 2
        d.rectangle((x - 10, 6, x + w + 10, h - 6), fill=(0, 0, 0, 140))
        d.text((x, 10), t, font=f, fill=(255, 255, 255, 255))
    return im


def side_by_side(a, b, fps, shift_b, labels, out_mp4, work):
    strip = work / "labels.png"
    label_strip(1620, labels).save(strip)
    trim_b = "trim=start_frame=%d,setpts=PTS-STARTPTS," % shift_b if shift_b > 0 else ""
    trim_a = "trim=start_frame=%d,setpts=PTS-STARTPTS," % (-shift_b) if shift_b < 0 else ""
    graph = ("[0:v]fps=%g,%sscale=540:960:flags=area,split[a0][a1];"
             "[1:v]fps=%g,%sscale=540:960:flags=area,split[b0][b1];"
             "[a1][b1]blend=all_mode=difference,lutyuv=y='min(255\\,val*4)':u=128:v=128[d];"
             "[a0][b0][d]hstack=inputs=3[v0];[v0][2:v]overlay=0:0:shortest=1[v]"
             % (fps, trim_a, fps, trim_b))
    sh(["ffmpeg", "-v", "error", "-y", "-i", str(a), "-i", str(b), "-loop", "1", "-i", str(strip),
        "-filter_complex", graph, "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "fast",
        "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
        "-movflags", "+faststart", str(out_mp4)])


def summarize(x):
    x = np.asarray([v for v in x if np.isfinite(v)], dtype=float)
    if len(x) == 0:
        return None
    return {"n": int(len(x)), "mean": round(float(x.mean()), 4), "median": round(float(np.median(x)), 4),
            "p05": round(float(np.percentile(x, 5)), 4), "p95": round(float(np.percentile(x, 95)), 4),
            "min": round(float(x.min()), 4), "max": round(float(x.max()), 4)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("otio"); ap.add_argument("out")
    ap.add_argument("--label-a", default="Final Cut Pro (FCPXML)")
    ap.add_argument("--label-b", default="DaVinci Resolve (OTIO)")
    ap.add_argument("--band", nargs=2, type=int, default=[740, 1080],
                    help="rows of the caption band in the full frame")
    ap.add_argument("--captions-from-timeline", action="store_true",
                    help="take each caption's band (position, size, lines) and ink colour from the "
                         "timeline instead of one --band and the yellow mask")
    ap.add_argument("--audio-at", nargs="+", type=float, default=[10.0, 50.0, 85.0],
                    help="start of each 6 s audio window, in seconds")
    args = ap.parse_args()
    A, B, out = Path(args.a), Path(args.b), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)

    edl = otio_edl.parse(args.otio)
    fps = float(edl["fps"])
    total_f = int(edl["total_f"])
    base = [e for e in edl["events"] if e["z"] == 0]
    cuts = [e["f0"] for e in base[1:]]
    captions = [e for e in edl["events"] if e["kind"] == "text"]
    stills = [e for e in edl["events"] if e["kind"] == "image" and e["z"] > 0]
    pa, pb = probe(A), probe(B)
    report = {"a": dict(pa, label=args.label_a), "b": dict(pb, label=args.label_b),
              "expected": {"fps": fps, "frames": total_f, "cuts": cuts,
                           "captions": [(c["f0"], c["f1"], c["text"]) for c in captions],
                           "stills": [(s["f0"], s["f1"]) for s in stills]}}
    scale = pa["height"] / 1920.0
    # one (band, mask) spec per distinct caption look; a single one by default
    if args.captions_from_timeline:
        keys, spec_of = [], []
        for c in captions:
            key = (caption_band(c, 1920), tuple(c.get("color") or ()))
            if key not in keys:
                keys.append(key)
            spec_of.append(keys.index(key))
        bands = [k[0] for k in keys]
        masks = [ink_mask_for(list(k[1]) or None) for k in keys]
    else:
        bands, masks, spec_of = [tuple(args.band)], [yellow_mask], [0] * len(captions)
    specs = [((int(b[0] * scale * AN_H / pa["height"]), int(b[1] * scale * AN_H / pa["height"])), m)
             for b, m in zip(bands, masks)]

    print("decoding A ...", flush=True)
    dA, inkA, YA = stream_stats(A, fps, specs)
    print("decoding B ...", flush=True)
    dB, inkB, YB = stream_stats(B, fps, specs)
    report["frames"] = {"a": int(len(dA)), "b": int(len(dB)), "expected": total_f}

    # cuts and the constant offset between the exports
    rows, offs = [], []
    for c in cuts:
        ia, va, ba = detect_cut(dA, c)
        ib, vb, bb = detect_cut(dB, c)
        rows.append({"expected": c, "a": ia, "a_minus_expected": None if ia is None else ia - c,
                     "a_strength": round(va / (ba + 1e-6), 1),
                     "b": ib, "b_minus_expected": None if ib is None else ib - c,
                     "b_strength": round(vb / (bb + 1e-6), 1)})
        if ia is not None and ib is not None:
            offs.append(ib - ia)
    shift_b = int(round(float(np.median(offs)))) if offs else 0
    report["cuts"] = rows
    report["shift_b_minus_a_frames"] = shift_b
    with open(out / "cuts.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # paired picture metrics, B shifted
    n = min(len(YA), len(YB) - shift_b if shift_b >= 0 else len(YB)) if shift_b >= 0 else min(len(YA) + shift_b, len(YB))
    if shift_b >= 0:
        mad = np.abs(YA[:n].astype(np.int16) - YB[shift_b:shift_b + n].astype(np.int16)).mean(axis=(1, 2))
    else:
        mad = np.abs(YA[-shift_b:-shift_b + n].astype(np.int16) - YB[:n].astype(np.int16)).mean(axis=(1, 2))
    print("ssim/psnr ...", flush=True)
    ssim, psnr = ffmpeg_quality(A, B, fps, shift_b, work)
    m = min(n, len(ssim), len(psnr))
    cap_frames = np.zeros(m, dtype=bool)
    for c in captions:
        cap_frames[max(0, c["f0"]):min(m, c["f1"])] = True
    report["picture"] = {
        "frames_compared": int(m),
        "mad_luma": {"all": summarize(mad[:m]), "with_caption": summarize(mad[:m][cap_frames]),
                     "without_caption": summarize(mad[:m][~cap_frames])},
        "ssim": {"all": summarize(ssim[:m]), "with_caption": summarize(ssim[:m][cap_frames]),
                 "without_caption": summarize(ssim[:m][~cap_frames])},
        "psnr_db": {"all": summarize(psnr[:m]), "with_caption": summarize(psnr[:m][cap_frames]),
                    "without_caption": summarize(psnr[:m][~cap_frames])},
        "worst_frames_by_ssim": [int(i) for i in np.argsort(ssim[:m])[:10]],
    }
    with open(out / "frame-metrics.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "mad_luma", "ssim", "psnr_db", "ink_a", "ink_b"])
        for i in range(m):
            ib = i + shift_b
            w.writerow([i, round(float(mad[i]), 3), round(float(ssim[i]), 5), round(float(psnr[i]), 3),
                        int(sum(x[i] for x in inkA)),
                        int(sum(x[ib] for x in inkB)) if 0 <= ib < len(inkB[0]) else ""])

    # caption timing and appearance
    crows, tiles = [], []
    for ci, c in enumerate(captions):
        k = spec_of[ci]
        band, mask = bands[k], masks[k]
        da = detect_caption(inkA[k], c["f0"], c["f1"])
        db = detect_caption(np.roll(inkB[k], -shift_b) if shift_b else inkB[k], c["f0"], c["f1"])
        mid = (c["f0"] + c["f1"]) // 2
        fa = grab(A, mid, fps, work / ("a-%04d.png" % mid))
        fb = grab(B, mid + shift_b, fps, work / ("b-%04d.png" % mid))
        ga, gb = glyph_box(fa, band, mask), glyph_box(fb, band, mask)
        row = {"text": c["text"].replace("\n", " / "), "expected_on": c["f0"], "expected_off": c["f1"],
               "a_on": da and da.get("on"), "a_off": da and da.get("off"),
               "b_on": db and db.get("on"), "b_off": db and db.get("off"),
               "a_box_w": ga and ga["w"], "a_box_h": ga and ga["h"], "a_center_y": ga and (ga["y0"] + ga["y1"]) / 2,
               "b_box_w": gb and gb["w"], "b_box_h": gb and gb["h"], "b_center_y": gb and (gb["y0"] + gb["y1"]) / 2}
        for k in ("on", "off"):
            for s in ("a", "b"):
                v = row["%s_%s" % (s, k)]
                row["%s_%s_err" % (s, k)] = None if v is None else v - row["expected_%s" % k]
        row["b_over_a_width"] = round(gb["w"] / ga["w"], 3) if ga and gb else None
        row["b_over_a_height"] = round(gb["h"] / ga["h"], 3) if ga and gb else None
        crows.append(row)
        # tile: A band over B band, half size
        ba_ = fa.crop((0, band[0], fa.width, band[1])).resize((540, (band[1] - band[0]) // 2))
        bb_ = fb.crop((0, band[0], fb.width, band[1])).resize((540, (band[1] - band[0]) // 2))
        tile = Image.new("RGB", (540, ba_.height * 2 + 30), (20, 20, 20))
        tile.paste(ba_, (0, 24)); tile.paste(bb_, (0, 24 + ba_.height + 6))
        d = ImageDraw.Draw(tile)
        f = ImageFont.truetype(FONT, 18)
        d.text((6, 3), "%s  f%d–%d   A above, B below" % (row["text"][:34], c["f0"], c["f1"]), font=f, fill="white")
        tiles.append(tile)
    report["captions"] = crows
    with open(out / "captions.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(crows[0].keys()))
        w.writeheader(); w.writerows(crows)
    cols = 3
    rows_n = (len(tiles) + cols - 1) // cols
    tw, th = tiles[0].size[0], max(t.size[1] for t in tiles)
    sheet = Image.new("RGB", (cols * tw + 8 * (cols - 1), rows_n * th + 8 * (rows_n - 1)), (0, 0, 0))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * (tw + 8), (i // cols) * (th + 8)))
    sheet.save(out / "captions-sheet.png")

    # audio
    report["audio"] = audio_compare(A, B, args.audio_at)

    # movie
    print("side-by-side ...", flush=True)
    side_by_side(A, B, fps, shift_b, [args.label_a, args.label_b, "|A − B| × 4"], out / "side-by-side.mp4", work)

    # write-up
    (out / "report.json").write_text(json.dumps(report, indent=2, default=lambda o: None) + "\n")
    L = []
    L.append("# %s vs %s — the same storyboard rendered by two editors\n" % (args.label_a, args.label_b))
    L.append("| | A: %s | B: %s |\n|---|---|---|" % (args.label_a, args.label_b))
    L.append("| file | `%s` | `%s` |" % (A.name, B.name))
    L.append("| geometry | %dx%d @ %g fps, %s | %dx%d @ %g fps, %s |" % (pa["width"], pa["height"], pa["fps"], pa["codec"], pb["width"], pb["height"], pb["fps"], pb["codec"]))
    L.append("| frames decoded (expected %d) | %d | %d |" % (total_f, len(dA), len(dB)))
    L.append("| constant offset B − A | | %+d frame(s) |\n" % shift_b)
    L.append("## Cuts (frame of each picture change; expected from the timeline)\n")
    L.append("| expected | A | A − exp | B | B − exp |\n|---|---|---|---|---|")
    for r in rows:
        L.append("| %d | %s | %s | %s | %s |" % (r["expected"], r["a"], r["a_minus_expected"], r["b"], r["b_minus_expected"]))
    L.append("\n## Captions (on/off frames and glyph box, full-resolution frames)\n")
    L.append("| caption | expected on–off | A on–off (err) | B on–off (err) | A box w×h | B box w×h | B/A w | B/A h |\n|---|---|---|---|---|---|---|---|")
    for r in crows:
        L.append("| %s | %d–%d | %s–%s (%s/%s) | %s–%s (%s/%s) | %s×%s | %s×%s | %s | %s |" % (
            r["text"], r["expected_on"], r["expected_off"], r["a_on"], r["a_off"], r["a_on_err"], r["a_off_err"],
            r["b_on"], r["b_off"], r["b_on_err"], r["b_off_err"], r["a_box_w"], r["a_box_h"], r["b_box_w"], r["b_box_h"],
            r["b_over_a_width"], r["b_over_a_height"]))
    pic = report["picture"]
    L.append("\n## Picture, per frame, B aligned to A (%d frames)\n" % pic["frames_compared"])
    L.append("| metric | all frames | frames with a caption | frames without |\n|---|---|---|---|")
    for key, label in (("ssim", "SSIM (1 = identical)"), ("psnr_db", "PSNR dB"), ("mad_luma", "mean |ΔY| (0–255)")):
        cells = []
        for part in ("all", "with_caption", "without_caption"):
            s = pic[key][part]
            cells.append("median %s, p5 %s, min %s" % (s["median"], s["p05"], s["min"]) if s else "—")
        L.append("| %s | %s |" % (label, " | ".join(cells)))
    L.append("\n## Audio (A vs B, 6 s windows)\n")
    L.append("| window | lag B−A | correlation | level B−A |\n|---|---|---|---|")
    for w_ in report["audio"]:
        L.append("| %.0f s | %s ms | %s | %s dB |" % (w_["t0"], w_.get("lag_ms"), w_.get("corr"), w_.get("level_b_minus_a_db")))
    L.append("\nFiles: `side-by-side.mp4` (A | B | amplified difference), `captions-sheet.png`, "
             "`frame-metrics.csv`, `cuts.csv`, `captions.csv`, `report.json`.\n")
    (out / "COMPARISON.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
