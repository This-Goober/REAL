#!/usr/bin/env python3
"""check_captions.py — every caption line fits the frame as Final Cut draws it.

    python3 scripts/check_captions.py storyboard/reel.json [--max 0.85]

Final Cut lays a title out on a 1920x1080 template and scales it to the
project height, so a 60-point caption in a 1080x1920 project is drawn about
1.73x larger than 60 px (measured on demo/paganini-no23). Each line of each
caption is measured in Helvetica Neue Bold at that size; a line wider than
--max of the frame fails the build, and the creator splits it
(`B1: L2 text = it shows / its work`).
"""
import argparse
import json
import sys

from PIL import ImageFont

FCP_TITLE_SCALE = 1.73
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("reel")
    ap.add_argument("--max", type=float, default=0.85, help="widest allowed line, as a fraction of the frame")
    a = ap.parse_args()
    reel = json.load(open(a.reel))
    W = reel["reel"]["width"]
    bad = 0
    for b in reel["beats"]:
        for L in b["layers"]:
            if L.get("kind") != "text":
                continue
            size = float(L.get("font_size") or 40) * FCP_TITLE_SCALE
            font = ImageFont.truetype(FONT, int(round(size)), index=1)      # Bold
            for line in (L.get("content") or "").split("\n"):
                w = font.getlength(line)
                flag = "" if w <= a.max * W else "   <-- too wide"
                if flag:
                    bad += 1
                print("%-6s %-26s %4.0f px of %d (%.0f%%)%s" % (L["id"], repr(line), w, W, 100 * w / W, flag))
    if bad:
        sys.exit("%d caption line(s) wider than %.0f%% of the frame" % (bad, 100 * a.max))
    print("every caption line fits")


if __name__ == "__main__":
    main()
