#!/usr/bin/env python3
"""make_visuals.py — the three stills and two clips for the binary-search reel,
in a white, gray-on-white, notion.so-style look, plus catalog_data.json for
/real-create-catalogue. Pillow + ffmpeg, deterministic, no inference.

    python3 make_visuals.py [--out DIR] [--catalog-only]

Every still is 1080x1920 drawn at 2x and downsampled; clips are 30 fps H.264
(yuv420p), silent, and longer than their beats so the shot can hold.
The top 30 % of every frame is left empty for the captions.
"""
import argparse
import json
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_OUT = os.path.join(HERE, "media")

W, H, FPS, S = 1080, 1920, 30, 2
WHITE = (255, 255, 255)
INK = (55, 53, 47)          # notion text
SOFT = (120, 119, 116)      # secondary text
PALE = (209, 207, 201)      # discarded numbers
PALE_FILL = (247, 247, 245)
CELL_FILL = (241, 241, 239)
HAIR = (211, 209, 203)
TTC = "/System/Library/Fonts/HelveticaNeue.ttc"
FACE = {"regular": 0, "bold": 1, "light": 7, "medium": 10}

GRID_X0, GRID_Y0, CELL, GAP = 65, 640, 86, 10     # 10 x 10, 950 px wide, y 640..1590
LABEL_Y = 1690

_fonts = {}


def font(size, face="regular"):
    key = (size, face)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(TTC, int(size * S), index=FACE[face])
    return _fonts[key]


def canvas():
    im = Image.new("RGB", (W * S, H * S), WHITE)
    return im, ImageDraw.Draw(im)


def finish(im):
    return im.resize((W, H), Image.LANCZOS)


def sc(v):
    return int(round(v * S))


def text(d, xy, s, size=32, fill=INK, face="regular", anchor="mm"):
    d.text((sc(xy[0]), sc(xy[1])), s, font=font(size, face), fill=fill, anchor=anchor)


def box(d, b, fill=CELL_FILL, outline=None, r=12, width=2):
    d.rounded_rectangle([sc(b[0]), sc(b[1]), sc(b[2]), sc(b[3])], radius=sc(r),
                        fill=fill, outline=outline, width=sc(width) if outline else 0)


def blend(c0, c1, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c0, c1))


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def cell_box(n):
    i = n - 1
    r, c = divmod(i, 10)
    x = GRID_X0 + c * (CELL + GAP)
    y = GRID_Y0 + r * (CELL + GAP)
    return (x, y, x + CELL, y + CELL)


def grid(d, state=None, ring=None, ring_t=1.0, crossed=()):
    """state(n) -> 'on' | 'pale' | float 0..1 (fade to pale)."""
    for n in range(1, 101):
        b = cell_box(n)
        st = state(n) if state else "on"
        if st == "on":
            fill, ink = CELL_FILL, INK
        elif st == "pale":
            fill, ink = PALE_FILL, PALE
        else:
            fill, ink = blend(CELL_FILL, PALE_FILL, st), blend(INK, PALE, st)
        box(d, b, fill=fill)
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        text(d, (cx, cy + 1), str(n), 30, ink, "regular")
        if n in crossed:
            d.line([sc(b[0] + 18), sc(b[1] + 18), sc(b[2] - 18), sc(b[3] - 18)], fill=SOFT, width=sc(3))
            d.line([sc(b[0] + 18), sc(b[3] - 18), sc(b[2] - 18), sc(b[1] + 18)], fill=SOFT, width=sc(3))
    if ring:
        b = cell_box(ring)
        pad = 6 + 6 * (1 - ease(ring_t))
        col = blend(WHITE, INK, ease(ring_t))
        d.rounded_rectangle([sc(b[0] - pad), sc(b[1] - pad), sc(b[2] + pad), sc(b[3] + pad)],
                            radius=sc(16), outline=col, width=sc(5))


def encode(path, frames):
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-", "-an",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                          "-movflags", "+faststart", path], stdin=subprocess.PIPE)
    for im in frames:
        p.stdin.write(im.tobytes())
    p.stdin.close()
    if p.wait():
        sys.exit("ffmpeg failed on " + path)


# ------------------------------------------------------------------ stills

def img_grid():
    im, d = canvas()
    grid(d)
    text(d, (W / 2, LABEL_Y), "pick a number from 1 to 100", 40, SOFT, "light")
    return finish(im)


def img_again():
    im, d = canvas()
    grid(d, state=lambda n: "pale" if (n > 50 or n < 25) else "on", ring=25)
    text(d, (W / 2, LABEL_Y), "too low  ·  the smaller ones go", 40, SOFT, "light")
    return finish(im)


def img_halving():
    im, d = canvas()
    sizes = [100, 50, 25, 13, 7, 4, 2, 1]
    y = 620
    bar_h, gap, max_w = 72, 26, 800
    for i, n in enumerate(sizes):
        w = max(bar_h, max_w * n / 100)
        box(d, (100, y, 100 + w, y + bar_h), fill=CELL_FILL if i < 7 else INK, r=14)
        text(d, (100 + w + 28, y + bar_h / 2 + 1), str(n), 40, INK, "regular", anchor="lm")
        y += bar_h + gap
    text(d, (W / 2, 1500), "7 guesses", 64, INK, "medium")
    text(d, (W / 2, 1580), "each guess cuts the pile in half", 40, SOFT, "light")
    return finish(im)


# ------------------------------------------------------------------- clips

def clip_one_by_one():
    n = 7 * FPS
    for f in range(n):
        im, d = canvas()
        k = min(100, f // 3 + 1) if f >= 6 else 0    # a new cross every 3 frames
        grid(d, crossed=set(range(1, k + 1)))
        text(d, (W / 2, LABEL_Y), "tries: %d" % k, 44, SOFT, "regular")
        yield finish(im)


def clip_halve():
    n = 7 * FPS
    for f in range(n):
        im, d = canvas()
        ring_t = (f - 20) / 25
        fade = ease((f - 75) / 35)
        state = (lambda nn: (fade if nn > 50 else "on")) if f >= 75 else None
        grid(d, state=state, ring=50 if f >= 20 else None, ring_t=ring_t)
        if f >= 45:
            a = ease((f - 45) / 15)
            label = "too high" if f < 75 else "too high  ·  the bigger ones go"
            text(d, (W / 2, LABEL_Y), label, 40, blend(WHITE, SOFT, a), "light")
        yield finish(im)


# ----------------------------------------------------------------- catalogue

def catalog(out):
    beats = [("B1", "hook", "Let's play a guessing game. I'm thinking of a number from one to one hundred."),
             ("B2", "the slow way", "You could guess one, two, three, four. That could take a hundred tries."),
             ("B3", "the trick", "Guess the middle, fifty. Too high? Throw away all the bigger numbers."),
             ("B4", "again", "Guess the middle of what is left. Twenty five. Too low? Throw away the smaller ones."),
             ("B5", "payoff", "Every guess cuts the pile in half. Seven guesses. That is binary search.")]
    A = []

    def add(f, k, role, shows, use, beat, binds_to, tags):
        A.append({"f": f, "k": k, "role": role, "shows": shows, "use": use, "beat": beat,
                  "binds_to": binds_to, "tags": tags})

    add("Images/img-grid.png", "image", "★ The hundred numbers",
        "A ten by ten grid of cells numbered 1 to 100, gray on a white page; 'pick a number from 1 to 100' beneath. Top third empty.",
        "B1, under the hook line.", "B1",
        "a `<show image of the numbers one to one hundred as a ten by ten grid…>` component", ["img-grid", "grid", "hundred", "numbers", "hook"])
    add("Videos/clip-one-by-one.mp4", "video", "Crossing out one at a time (animated)",
        "The same grid; from 0.2 s a number is crossed out every three frames from the top left, a 'tries: N' counter climbing beneath; 69 crossed by 7 s, never finishing. Silent, 7.0 s, longer than the beat on purpose.",
        "B2, the whole beat.", "B2",
        "a `<video clip of the same grid with the numbers being crossed out one at a time…>` component", ["clip-one-by-one", "linear", "slow", "crossed", "counter"])
    add("Videos/clip-halve.mp4", "video", "★ Guess the middle (animated)",
        "The grid; cell 50 ringed from 0.7 s, 'too high' beneath from 1.5 s, numbers 51-100 fade to pale gray between 2.5 and 3.7 s, then the frame holds. Silent, 7.0 s, longer than the beat.",
        "B3, the whole beat.", "B3",
        "a `<video clip of the grid with the cell for fifty ringed… fading to pale gray>` component", ["clip-halve", "middle", "fifty", "too-high", "halve"])
    add("Images/img-again.png", "image", "Half again",
        "Grid with 51-100 pale, cell 25 ringed, 'too low  the smaller ones go' beneath, 1-24 pale as well; only 26-50 still dark.",
        "B4, under 'twenty five'.", "B4",
        "a `<show image of the grid with the numbers above fifty already pale, the cell for twenty five ringed…>` component", ["img-again", "twenty-five", "too-low", "again"])
    add("Images/img-halving.png", "image", "★ The halving staircase",
        "Eight bars each half the width of the one above, labelled 100 50 25 13 7 4 2 1, the last one dark; '7 guesses' and 'each guess cuts the pile in half' beneath.",
        "B5, under the closing title.", "B5",
        "a `<show image of a column of gray bars each half the width of the one above…>` component", ["img-halving", "staircase", "seven", "guesses", "payoff"])
    wav = os.path.join(out, "Audio", "narration.wav")
    script = os.path.join(HERE, "pipeline", "narration.txt")
    if os.path.exists(wav):
        spoken = open(script).read().strip() if os.path.exists(script) else ""
        add("Audio/narration.wav", "audio", "Voice take 1 — full script",
            "ElevenLabs neural narration (George, eleven_multilingual_v2) of the five lines of NOTEBOOK.md in order as one take, 150 ms lead-in, 1 s of silence at the end. Says: " + spoken,
            "B1-B5. The measured clock for the whole reel.", "any",
            "the narration spine — every spoken `<…>` line in the notebook, as one continuous take",
            ["narration", "take-1", "voice", "full-script"])
    data = {"project": "binary-search-5yo-30s", "root": out, "generated": "2026-10-18",
            "_comment": "Judgement fields written by Claude alongside make_visuals.py; facts are probed by build_catalog.py.",
            "script_beats": [{"id": i, "take": "Audio/narration.wav", "dur": 0, "gist": "%s. %s" % (n, g)}
                             for i, n, g in beats],
            "assets": A}
    path = os.path.join(out, "catalog_data.json")
    json.dump(data, open(path, "w"), indent=1, ensure_ascii=False)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--catalog-only", action="store_true")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    for sub_ in ("Images", "Videos", "Audio"):
        os.makedirs(os.path.join(out, sub_), exist_ok=True)
    if not a.catalog_only:
        for name, fn in (("img-grid", img_grid), ("img-again", img_again), ("img-halving", img_halving)):
            p = os.path.join(out, "Images", name + ".png")
            fn().save(p, optimize=True)
            print("still", p)
        for name, fn in (("clip-one-by-one", clip_one_by_one), ("clip-halve", clip_halve)):
            p = os.path.join(out, "Videos", name + ".mp4")
            encode(p, fn())
            print("clip ", p)
    print("catalog", catalog(out))


if __name__ == "__main__":
    main()
