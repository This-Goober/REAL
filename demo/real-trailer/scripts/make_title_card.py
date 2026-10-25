#!/usr/bin/env python3
"""make_title_card.py — the closing card of the trailer, 1080x1920.

    python3 scripts/make_title_card.py media/Images/T-title-made-with-real.png
    python3 scripts/make_title_card.py --paper paper.png      (the ground alone)

Washi-coloured ground, the word REAL in a tall serif, リアル set vertically
beside it, a vermilion seal, and the repository address. The same elements
the landing page uses, so the trailer ends where the page begins. Fonts are
the ones every Mac ships with (Didot, Hiragino Sans GB); nothing to install.
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
PAPER = (244, 239, 229)
INK = (28, 26, 24)
VERMILION = (184, 46, 36)
GREY = (120, 114, 104)


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def paper(w=W, h=H):
    """The card's ground: washi #F4EFE5 with a faint grain (seeded, so every
    file drawn from it is the same paper)."""
    import random
    img = Image.new("RGB", (w, h), PAPER)
    random.seed(7)
    grain = Image.new("L", (w, h), 0)
    g = ImageDraw.Draw(grain)
    for _ in range(int(2600 * w * h / (W * H))):
        x, y = random.randrange(w), random.randrange(h)
        r = random.choice((1, 1, 2))
        g.ellipse((x, y, x + r, y + r), fill=random.randrange(18, 42))
    grain = grain.filter(ImageFilter.GaussianBlur(1.2))
    img.paste(Image.new("RGB", (w, h), (214, 206, 192)), mask=grain)
    return img


def main(out):
    img = paper()
    d = ImageDraw.Draw(img)

    didot = "/System/Library/Fonts/Supplemental/Didot.ttc"
    hira = "/System/Library/Fonts/Hiragino Sans GB.ttc"
    f_small = font(didot, 44)
    f_real = font(didot, 250)
    f_jp = font(hira, 84, index=1)
    f_addr = font("/System/Library/Fonts/Menlo.ttc", 40)

    # a single thin rule high on the page, like the mount of a scroll
    d.line((140, 300, W - 140, 300), fill=INK, width=2)

    # MADE WITH
    t = "MADE WITH"
    w = d.textlength(t, font=f_small)
    d.text(((W - w) / 2, 560), t, font=f_small, fill=GREY, spacing=4)
    # REAL, large
    t = "REAL"
    w = d.textlength(t, font=f_real)
    x0 = 120
    d.text((x0, 610), t, font=f_real, fill=INK)

    # リアル vertically, clear of the word's right edge
    x = x0 + w + 48
    y = 650
    for ch in "リアル":
        cw = d.textlength(ch, font=f_jp)
        d.text((x + (120 - cw) / 2, y), ch, font=f_jp, fill=INK)
        y += 100

    # vermilion seal: square, rounded, two characters in negative
    sx, sy, ss = 160, 1040, 150
    seal = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    sd = ImageDraw.Draw(seal)
    sd.rounded_rectangle((0, 0, ss - 1, ss - 1), radius=14, fill=VERMILION + (255,))
    f_seal = font(hira, 60, index=1)
    for i, ch in enumerate("実写"):
        cw = sd.textlength(ch, font=f_seal)
        sd.text(((ss - cw) / 2, 12 + i * 64), ch, font=f_seal, fill=PAPER + (255,))
    img.paste(seal, (sx, sy), seal)

    # the line under the seal
    d = ImageDraw.Draw(img)
    d.text((sx + ss + 40, sy + 18), "edited by REAL,", font=f_small, fill=INK)
    d.text((sx + ss + 40, sy + 78), "notebook in the repository", font=f_small, fill=INK)

    # address
    t = "github.com/This-Goober/REAL"
    w = d.textlength(t, font=f_addr)
    d.text(((W - w) / 2, 1380), t, font=f_addr, fill=GREY)
    d.line((140, 1620, W - 140, 1620), fill=INK, width=2)
    img.save(out, optimize=True)
    print("wrote", out, img.size)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--paper":          # the plain paper, for panel.py
        paper().save(sys.argv[2])
        print("wrote", sys.argv[2])
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else "T-title-made-with-real.png")
