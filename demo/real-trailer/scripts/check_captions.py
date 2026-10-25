#!/usr/bin/env python3
"""check_captions.py — every caption fits the frame as Final Cut draws it.

    python3 scripts/check_captions.py storyboard/reel.json [--max 0.85] [--margin 0.05]

Width: Final Cut lays a title out on a 1920x1080 template and scales it to
the project height, so a caption in a 1080x1920 project is drawn about 1.73x
its point size (measured on demo/paganini-no23). Each line is measured in
Helvetica Neue Bold at that size; a line wider than --max of the frame fails,
and the creator splits it (`B1: L2 text = it shows / its work`).

Height: Final Cut puts the first line's baseline at the caption's position
and adds each further line 1.25 em below it, so a third line grows the block
downward (measured on the trailer's render, where a 3-line caption at the
bottom position ran off the frame). Ascenders reach 0.75 em above the first
baseline, descenders 0.25 em below the last. The block must stay --margin of
the frame height inside the top and bottom edges; a longer caption is moved
up (`B5: L3 position = 0 -440`).
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
    ap.add_argument("--margin", type=float, default=0.05, help="space kept above and below, as a fraction of the height")
    a = ap.parse_args()
    reel = json.load(open(a.reel))
    W, H = reel["reel"]["width"], reel["reel"]["height"]
    bad = 0
    for b in reel["beats"]:
        for L in b["layers"]:
            if L.get("kind") != "text":
                continue
            size = float(L.get("font_size") or 40) * FCP_TITLE_SCALE
            font = ImageFont.truetype(FONT, int(round(size)), index=1)      # Bold
            lines = (L.get("content") or "").split("\n")
            for line in lines:
                w = font.getlength(line)
                flag = "" if w <= a.max * W else "   <-- too wide"
                if flag:
                    bad += 1
                print("%-6s %-26s %4.0f px of %d (%.0f%%)%s" % (L["id"], repr(line), w, W, 100 * w / W, flag))
            row0 = H / 2.0 - float((L.get("position") or [0, -620])[1])
            top = row0 - 0.75 * size
            bottom = row0 + (len(lines) - 1) * 1.25 * size + 0.25 * size
            lo, hi = a.margin * H, (1 - a.margin) * H
            flag = "" if (top >= lo and bottom <= hi) else "   <-- outside the frame's %.0f%% margin" % (100 * a.margin)
            if flag:
                bad += 1
            print("%-6s %d line(s), rows %4.0f-%4.0f of %d (keep inside %.0f-%.0f)%s"
                  % (L["id"], len(lines), top, bottom, H, lo, hi, flag))
    if bad:
        sys.exit("%d caption problem(s): too wide or outside the frame" % bad)
    print("every caption fits the frame")


if __name__ == "__main__":
    main()
