#!/usr/bin/env python3
"""make_panel_frame.py — the news-style frame over a panel shot, as a transparent PNG.

    python3 scripts/make_panel_frame.py OUT.png --step 転 --label STORYBOARD --of "3 / 4" \
        --tag tracks --headline "THE TRACKS PAGE" --deck "this trailer's own storyboard"

1080x1920, transparent except where it draws, so scripts/panel.py can lay it
over the shot:

  head banner   translucent sumi ink across the top of the shot, a faint
                seigaiha wave in it; the vermilion 実写 seal, REAL and リアル
                on the left; on the right the step the shot illustrates, in
                the landing page's 起承転結 (転 storyboard, 結 compile)
  lower strip   at the foot of the shot: a vermilion tag with a line icon
                (tracks | editor | pair), a headline and a deck saying what
                the shot is, like a news chyron
  rule          a vermilion line where the shot meets the paper quarter

The palette and type are the page's and the closing card's: paper #F4EFE5,
sumi #1C1A18, vermilion #B82E24; Didot for REAL, Hiragino Mincho for the
Japanese, Avenir Next for the labels. Every Mac ships these fonts.
"""
import argparse
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, TOP = 1080, 1920, 1440
PAPER = (244, 239, 229)
INK = (24, 22, 20)
VERM = (184, 46, 36)
DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
MINCHO = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
BANNER_H = 132
STRIP_H = 92


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def spaced(draw, xy, text, fnt, fill, tracking=0.0, anchor_right=False):
    """Draw letter-spaced text; returns its width."""
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x, y = xy
    if anchor_right:
        x -= total
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += w + tracking
    return total


def seigaiha(size, r=26, alpha=20):
    """Overlapping wave arcs, the classic seigaiha, in paper colour at low alpha."""
    w, h = size
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    row = 0
    y = h + r
    while y > -r:
        off = 0 if row % 2 == 0 else r
        x = -r + off
        while x < w + r:
            for k in (1.0, 0.72, 0.44):
                rr = r * k
                d.arc((x - rr, y - rr, x + rr, y + rr), 180, 360, fill=PAPER + (alpha,), width=2)
            x += 2 * r
        y -= r / 2.0
        row += 1
    return im


def seal(size):
    s = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=max(6, size // 9), fill=VERM + (255,))
    f = font(MINCHO, int(size * 0.40), index=0)
    for i, ch in enumerate("実写"):
        cw = d.textlength(ch, font=f)
        d.text(((size - cw) / 2, size * 0.07 + i * size * 0.44), ch, font=f, fill=PAPER + (255,))
    return s


def icon(kind, w=64, h=48, stroke=4):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = PAPER + (255,)
    if kind == "tracks":                 # three lanes and a playhead
        for i, (x0, x1) in enumerate(((4, 40), (14, 58), (6, 30))):
            y = 8 + i * 14
            d.rounded_rectangle((x0, y, x1, y + 8), radius=4, outline=c, width=stroke - 1)
        d.line((24, 2, 24, h - 2), fill=c, width=stroke - 1)
        d.polygon([(19, 0), (29, 0), (24, 6)], fill=c)
    elif kind == "editor":               # a viewer with a play mark over a timeline
        d.rounded_rectangle((8, 2, 56, 30), radius=4, outline=c, width=stroke)
        d.polygon([(28, 9), (28, 23), (40, 16)], fill=c)
        d.line((2, 38, 62, 38), fill=c, width=stroke - 1)
        for x in (10, 26, 44):
            d.line((x, 34, x, 42), fill=c, width=stroke - 1)
    else:                                # pair: two frames, one storyboard
        d.rounded_rectangle((2, 6, 28, 42), radius=4, outline=c, width=stroke)
        d.rounded_rectangle((36, 6, 62, 42), radius=4, outline=c, width=stroke)
        d.line((29, 20, 35, 20), fill=c, width=stroke - 1)
        d.line((29, 28, 35, 28), fill=c, width=stroke - 1)
    return im


def make(step, label, of, tag, headline, deck):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # ---- head banner: translucent sumi, seigaiha, a soft shadow below it
    shadow = Image.new("RGBA", (W, BANNER_H + 30), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((0, 0, W, BANNER_H), fill=(0, 0, 0, 70))
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)), (0, 6))
    band = Image.new("RGBA", (W, BANNER_H), INK + (178,))
    band.alpha_composite(seigaiha((W, BANNER_H)))
    im.alpha_composite(band, (0, 0))
    d = ImageDraw.Draw(im)
    d.line((0, BANNER_H - 2, W, BANNER_H - 2), fill=VERM + (255,), width=4)

    sz = 84
    im.alpha_composite(seal(sz), (34, (BANNER_H - sz) // 2 - 1))
    d = ImageDraw.Draw(im)
    f_real = font(DIDOT, 70)
    x = 34 + sz + 24
    top = (BANNER_H - 70) // 2 - 6
    d.text((x, top), "REAL", font=f_real, fill=PAPER + (255,))
    x += d.textlength("REAL", font=f_real) + 18
    d.line((x, 38, x, BANNER_H - 40), fill=PAPER + (110,), width=2)
    x += 16
    spaced(d, (x, (BANNER_H - 34) // 2 - 4), "リアル", font(MINCHO, 34), PAPER + (235,), tracking=6)

    # step on the right: a vermilion disc with the kanji, the label and "3 / 4"
    disc = 78
    dx = W - 34 - disc
    dy = (BANNER_H - disc) // 2 - 1
    d.ellipse((dx, dy, dx + disc, dy + disc), fill=VERM + (255,))
    f_k = font(MINCHO, 46, index=1)
    kw = d.textlength(step, font=f_k)
    d.text((dx + (disc - kw) / 2, dy + 11), step, font=f_k, fill=PAPER + (255,))
    f_lab = font(AVENIR, 25, index=2)
    f_of = font(AVENIR, 20, index=5)
    spaced(d, (dx - 20, 38), label, f_lab, PAPER + (255,), tracking=4, anchor_right=True)
    spaced(d, (dx - 20, 72), "STEP " + of, f_of, PAPER + (170,), tracking=3, anchor_right=True)

    # ---- lower strip at the foot of the shot
    y0 = TOP - STRIP_H
    strip = Image.new("RGBA", (W, STRIP_H), INK + (196,))
    im.alpha_composite(strip, (0, y0))
    tagw = 120
    tagim = Image.new("RGBA", (tagw, STRIP_H), VERM + (255,))
    ic = icon(tag)
    tagim.alpha_composite(ic, ((tagw - ic.width) // 2, (STRIP_H - ic.height) // 2))
    im.alpha_composite(tagim, (0, y0))
    d = ImageDraw.Draw(im)
    f_head = font(AVENIR, 30, index=0)
    f_deck = font(AVENIR, 27, index=7)
    x = tagw + 26
    w = spaced(d, (x, y0 + 13), headline, f_head, PAPER + (255,), tracking=2.5)
    d.text((x, y0 + 50), deck, font=f_deck, fill=PAPER + (205,))
    # a small vertical リアル at the strip's right end, Mincho, quiet
    f_v = font(MINCHO, 22)
    vx, vy = W - 42, y0 + 12
    for ch in "リアル":
        cw = d.textlength(ch, font=f_v)
        d.text((vx + (22 - cw) / 2, vy), ch, font=f_v, fill=PAPER + (150,))
        vy += 23
    # the rule where the shot meets the paper
    d.line((0, TOP - 2, W, TOP - 2), fill=VERM + (255,), width=4)
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--step", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--of", required=True)
    ap.add_argument("--tag", choices=("tracks", "editor", "pair"), required=True)
    ap.add_argument("--headline", required=True)
    ap.add_argument("--deck", required=True)
    a = ap.parse_args()
    make(a.step, a.label, a.of, a.tag, a.headline, a.deck).save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
