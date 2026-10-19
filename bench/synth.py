#!/usr/bin/env python3
"""synth.py — synthetic, machine-readable placeholder media for the REAL
assembly benchmark.

Every placeholder clip and image carries a burned-in MARKER STRIP: a row of
24 black/white squares near its top edge encoding

    4 bits sync (1010) | 8 bits asset number | 12 bits source frame index

so a frame of any rendered timeline can be decoded back to *which asset is on
screen and which source frame of it* without OCR, without a model, and
without trusting the pipeline under test. Images are 1080x1080 (square), so
when they sit as a fitted overlay on a 1080x1920 clip the clip's own strip
(at the very top) stays visible and both can be decoded from one frame.

    python3 synth.py pool  OUT_DIR [--clips 16 --images 12 --clip-seconds 12]
    python3 synth.py decode FRAME.png          # debug: decode one frame

Stdlib + PIL + numpy + ffmpeg.
"""
import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920          # sequence size (9:16)
IMG = 1080                 # square images
FPS = 30
NBITS = 24
SYNC = (1, 0, 1, 0)
STRIP_Y, STRIP_H = 10, 44  # strip row inside the asset's own pixel space
CELL = W // NBITS          # 45 px

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def font(size):
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def bits_for(asset_no, frame_idx):
    b = list(SYNC)
    b += [(asset_no >> (7 - i)) & 1 for i in range(8)]
    b += [(frame_idx >> (11 - i)) & 1 for i in range(12)]
    return b


def paint_strip(arr, asset_no, frame_idx, y0=STRIP_Y):
    """Paint the marker strip into an HxWx3 uint8 array in place."""
    for k, bit in enumerate(bits_for(asset_no, frame_idx)):
        x0 = k * CELL
        arr[y0:y0 + STRIP_H, x0:x0 + CELL] = 255 if bit else 0
    # a grey border row above and below so the strip is unambiguous
    arr[y0 - 4:y0, :] = 128
    arr[y0 + STRIP_H:y0 + STRIP_H + 4, :] = 128


def decode_strip(arr, y0=STRIP_Y):
    """-> (asset_no, frame_idx) or None if no valid sync at that row."""
    ys = y0 + STRIP_H // 2 if arr.shape[0] > 1 else 0
    if ys >= arr.shape[0]:
        return None
    row = arr[ys]
    lum = row.mean(axis=1) if row.ndim == 2 else row
    cell = lum.shape[0] / NBITS           # works at any render scale
    bits = []
    for k in range(NBITS):
        xc = int((k + 0.5) * cell)
        if xc >= lum.shape[0]:
            return None
        bits.append(1 if lum[xc] > 127 else 0)
    if tuple(bits[:4]) != SYNC:
        return None
    asset_no = int("".join(map(str, bits[4:12])), 2)
    frame_idx = int("".join(map(str, bits[12:24])), 2)
    return asset_no, frame_idx


def hue_rgb(i, n, s=0.55, v=0.55):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb((i * 0.618033) % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def asset_number(asset_id):
    """clip07 -> 7, img03 -> 128+3. Images live in the upper half of the id
    space so a decoded number says which kind it is."""
    if asset_id.startswith("clip"):
        return int(asset_id[4:])
    if asset_id.startswith("img"):
        return 128 + int(asset_id[3:])
    raise ValueError(asset_id)


def asset_id_of(number):
    return "img%02d" % (number - 128) if number >= 128 else "clip%02d" % number


def make_clip(path, clip_no, seconds, fps=FPS):
    """A clip whose every frame says what it is: colour field, big label,
    marker strip (asset + frame index), and a moving bar so motion exists."""
    n = int(round(seconds * fps))
    base = np.zeros((H, W, 3), dtype=np.uint8)
    base[:] = hue_rgb(clip_no, 16)
    lab = Image.fromarray(base)
    d = ImageDraw.Draw(lab)
    d.text((W // 2, H // 2 - 120), "CLIP %02d" % clip_no, fill=(245, 245, 245),
           font=font(170), anchor="mm")
    d.text((W // 2, H // 2 + 60), "placeholder footage", fill=(230, 230, 230),
           font=font(60), anchor="mm")
    base = np.array(lab)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (W, H), "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
           "-pix_fmt", "yuv420p", "-g", "15", "-an", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    tc_font = font(72)
    for f in range(n):
        fr = base.copy()
        paint_strip(fr, clip_no, f)
        # a bar sweeping left-to-right once per second: visible motion
        x = int((f % fps) / fps * (W - 60))
        fr[H // 2 + 200:H // 2 + 260, x:x + 60] = 255
        im = Image.fromarray(fr)
        ImageDraw.Draw(im).text((W // 2, H - 220), "f%04d  %05.2fs" % (f, f / fps),
                                fill=(255, 255, 255), font=tc_font, anchor="mm")
        p.stdin.write(np.asarray(im).tobytes())
    p.stdin.close()
    p.wait()
    if p.returncode:
        raise SystemExit("ffmpeg failed writing %s" % path)
    return n


def make_image(path, img_no):
    arr = np.zeros((IMG, IMG, 3), dtype=np.uint8)
    arr[:] = hue_rgb(img_no + 40, 16, s=0.35, v=0.85)
    paint_strip(arr, 128 + img_no, 0)
    im = Image.fromarray(arr)
    d = ImageDraw.Draw(im)
    d.rectangle([30, 90, IMG - 30, IMG - 30], outline=(40, 40, 40), width=10)
    d.text((IMG // 2, IMG // 2 - 60), "IMG %02d" % img_no, fill=(30, 30, 30),
           font=font(170), anchor="mm")
    d.text((IMG // 2, IMG // 2 + 110), "placeholder still", fill=(50, 50, 50),
           font=font(60), anchor="mm")
    im.save(path)


def cmd_pool(args):
    os.makedirs(os.path.join(args.out, "Videos"), exist_ok=True)
    os.makedirs(os.path.join(args.out, "Images"), exist_ok=True)
    for i in range(1, args.clips + 1):
        p = os.path.join(args.out, "Videos", "clip%02d.mp4" % i)
        if not os.path.exists(p):
            n = make_clip(p, i, args.clip_seconds)
            print("wrote %s (%d frames)" % (p, n))
    for i in range(1, args.images + 1):
        p = os.path.join(args.out, "Images", "img%02d.png" % i)
        if not os.path.exists(p):
            make_image(p, i)
            print("wrote %s" % p)


def cmd_decode(args):
    arr = np.asarray(Image.open(args.frame).convert("RGB"))
    print("top strip   :", decode_strip(arr, STRIP_Y))
    print("image strip :", decode_strip(arr, (H - IMG) // 2 + STRIP_Y))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pool")
    p.add_argument("out")
    p.add_argument("--clips", type=int, default=16)
    p.add_argument("--images", type=int, default=12)
    p.add_argument("--clip-seconds", type=float, default=12.0)
    d = sub.add_parser("decode")
    d.add_argument("frame")
    a = ap.parse_args()
    {"pool": cmd_pool, "decode": cmd_decode}[a.cmd](a)
