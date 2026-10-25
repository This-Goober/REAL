#!/usr/bin/env python3
"""A dissolve into (or out of) a still: the still is written with Final Cut's
infinite-media start, and its anchored children follow it.

    python3 -m unittest bench/test_fcpxml_still_transition.py

Final Cut Pro refuses an FCPXML whose transition touches a `<video>` still
with `start="0s"`: the dissolve borrows half its length before the still's
in-point and nothing is there. Titles and gaps already use `start="3600s"`;
a still next to a transition now does too, and a still elsewhere keeps 0s.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "skills", "batch-2", "skills", "real-compile", "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, HERE)

import fcpxml  # noqa: E402
import fcpxml_edl  # noqa: E402

STORY = {
    "project": "still after a dissolve", "event": "REAL", "frame_rate": "30",
    "width": 1080, "height": 1920, "assets_root": "/Volumes/Edit/fixture",
    "beats": [
        {"type": "video", "src": "Videos/a.mov", "start": 0.0, "duration": 6.0,
         "asset_duration": 8.0, "name": "B1 shot"},
        {"type": "image", "src": "Images/card.png", "duration": 5.0, "width": 1080, "height": 1920,
         "name": "B2 card", "transition_in": {"name": "Cross Dissolve", "duration": 1.0},
         "overlays": [{"text": "hello", "lane": 1, "offset": 1.0, "duration": 1.5,
                       "font_size": 40, "position": [0, -620]}]},
        {"type": "image", "src": "Images/other.png", "duration": 2.0, "width": 1080, "height": 1920,
         "name": "B3 plain still"},
    ],
}


class StillTransitionTests(unittest.TestCase):
    def build(self):
        import tempfile
        d = tempfile.mkdtemp()
        out = os.path.join(d, "t.fcpxml")
        xml = fcpxml.Story(STORY, base_dir=d, do_probe=False).build()
        open(out, "w").write(xml)
        return xml, out

    def test_still_after_a_dissolve_gets_infinite_media_start(self):
        xml, out = self.build()
        stills = re.findall(r'<video [^>]*name="(B2 card|B3 plain still)"[^>]*start="([^"]+)"', xml)
        self.assertEqual(dict(stills), {"B2 card": "3600s", "B3 plain still": "0s"})
        # the transition is centred on the cut at 6.0 s
        self.assertIn('<transition name="Cross Dissolve" offset="11/2s" duration="1s">', xml)
        # the title anchored to the card is offset from the card's start (3600 s + 1 s)
        m = re.search(r'<title [^>]*name="hello"[^>]*offset="([^"]+)"', xml)
        self.assertEqual(m.group(1), "3601s")
        # the independent reader still sees the still on its frames
        edl = fcpxml_edl.parse(out)
        card = next(e for e in edl["events"] if e["kind"] == "image" and e["asset"] == "card")
        self.assertEqual((card["f0"], card["f1"]), (180, 330))
        title = next(e for e in edl["events"] if e["kind"] == "text")
        self.assertEqual((title["f0"], title["f1"]), (210, 255))
        self.assertEqual([t["f"] for t in edl["transitions"]], [180])


if __name__ == "__main__":
    unittest.main()
