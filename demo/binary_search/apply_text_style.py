#!/usr/bin/env python3
"""apply_text_style.py — the creator's text look for this reel, as per-layer
overrides on the reel (the schema lets a text layer override its style preset;
`revise.py` has no grammar for size, colour or position).

    python3 apply_text_style.py reel.json

Creator direction, 18 October: white page, gray on white, notion.so style; captions at
55 px, 20 % from the top (kept from the attention reel for consistency). So:

  caption  Helvetica Neue Medium 55, colour #37352F, no shadow, y = +576
  title    Helvetica Neue Medium 96, colour #37352F, no shadow, y = +576
           (the closing title takes the caption slot; the stills keep their
           top third empty for it)

Positions are REAL frame pixels from the centre, y up; 20 % from the top of a
1920-high frame is y = +576, which FCPXML writes as "0 30". Idempotent; carried
forward by `build.py retime` and `build.py build --preserve`.
"""
import json
import sys

INK = [55 / 255, 53 / 255, 47 / 255, 1]
TOP_FRACTION = 0.20
LOOK = {
    "caption": dict(font="Helvetica Neue", font_face="Medium", font_size=55),
    "title": dict(font="Helvetica Neue", font_face="Medium", font_size=96),
}


def main(path):
    reel = json.load(open(path))
    h = int(reel["reel"]["height"])
    y = int(round(h / 2 - TOP_FRACTION * h))
    n = 0
    for b in reel["beats"]:
        for l in b.get("layers", []):
            if l.get("kind") != "text" or l.get("style") not in LOOK:
                continue
            l.update(LOOK[l["style"]])
            l["color"] = INK
            l["shadow"] = False
            l["position"] = [0, y]
            l["style_by"] = "creator"
            l["chosen_by"] = "creator"
            l["confidence"] = "high"
            l["candidates"] = []
            l["note"] = ("creator: %s, Helvetica Neue Medium %d px, #37352F on white, no shadow, "
                         "20%% from the top (y=+%d) — creator decision, 18 Oct 2026" % (l["style"], l["font_size"], y))
            n += 1
            print("  %s %-8s %r" % (l["id"], l["style"], l.get("content")))
    json.dump(reel, open(path, "w"), indent=1, ensure_ascii=False)
    print("%d text layer(s) styled" % n)


if __name__ == "__main__":
    main(sys.argv[1])
