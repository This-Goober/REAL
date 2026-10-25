#!/usr/bin/env python3
"""make_og_image.py — the link-preview card for the project page, and the touch icon.

    python3 assets/site/make_og_image.py

Writes og-image.jpg (1200x630, what WhatsApp, iMessage, Slack and the rest
show when the page's address is pasted) and apple-touch-icon.png (180x180).
Same elements as the page and the trailer's closing card: washi ground, REAL
in a tall serif, リアル set vertically, the vermilion seal. Fonts are the ones
every Mac ships with.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER, INK, VERMILION, GREY = (244, 239, 229), (28, 26, 24), (184, 46, 36), (120, 114, 104)
DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
HIRA = "/System/Library/Fonts/Hiragino Sans GB.ttc"
MENLO = "/System/Library/Fonts/Menlo.ttc"


def grain(img, n=2200, seed=7):
    import random
    random.seed(seed)
    W, H = img.size
    g = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(g)
    for _ in range(n):
        x, y = random.randrange(W), random.randrange(H)
        r = random.choice((1, 1, 2))
        d.ellipse((x, y, x + r, y + r), fill=random.randrange(18, 42))
    img.paste(Image.new("RGB", (W, H), (214, 206, 192)), mask=g.filter(ImageFilter.GaussianBlur(1.2)))


def seal(size, chars="実写", radius=None):
    s = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius or size // 11, fill=VERMILION + (255,))
    f = ImageFont.truetype(HIRA, int(size * 0.4), index=1)
    for i, ch in enumerate(chars):
        cw = d.textlength(ch, font=f)
        d.text(((size - cw) / 2, size * 0.08 + i * size * 0.43), ch, font=f, fill=PAPER + (255,))
    return s


def og():
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), PAPER)
    grain(img)
    d = ImageDraw.Draw(img)
    d.line((80, 70, W - 80, 70), fill=INK, width=2)
    d.line((80, H - 44, W - 80, H - 44), fill=INK, width=2)
    f_real = ImageFont.truetype(DIDOT, 230)
    d.text((80, 130), "REAL", font=f_real, fill=INK)
    w_real = d.textlength("REAL", font=f_real)
    f_jp = ImageFont.truetype(HIRA, 56, index=1)
    x = 80 + w_real + 36
    for i, ch in enumerate("リアル"):
        cw = d.textlength(ch, font=f_jp)
        d.text((x + (70 - cw) / 2, 170 + i * 66), ch, font=f_jp, fill=INK)
    s = seal(96)
    img.paste(s, (int(x + 84), 300), s)
    d = ImageDraw.Draw(img)
    f_line = ImageFont.truetype(DIDOT, 40)
    d.text((84, 404), "An AI production crew for the director's own footage.", font=f_line, fill=INK)
    d.text((84, 456), "It edits. It does not generate. It shows its work.", font=f_line, fill=INK)
    f_url = ImageFont.truetype(MENLO, 26)
    d.text((84, 528), "this-goober.github.io/REAL", font=f_url, fill=GREY)
    out = os.path.join(HERE, "og-image.jpg")
    img.save(out, quality=88, optimize=True)
    print("wrote", out, img.size, os.path.getsize(out) // 1024, "KB")


def touch_icon():
    img = Image.new("RGB", (180, 180), PAPER)
    s = seal(140, radius=16)
    img.paste(s, (20, 20), s)
    out = os.path.join(HERE, "apple-touch-icon.png")
    img.save(out, optimize=True)
    print("wrote", out, img.size)


if __name__ == "__main__":
    og()
    touch_icon()
