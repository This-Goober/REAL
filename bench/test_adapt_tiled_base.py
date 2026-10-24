#!/usr/bin/env python3
"""Two base shots under one line tile the primary storyline.

    python3 -m unittest bench/test_adapt_tiled_base.py

A beat whose base shots start where the previous one ends, from the beat's
first frame to its last, compiles to consecutive spine items rather than a gap
with everything connected above it; an overlay attaches to the tile it starts
in; a dissolve into the next beat borrows from the tile that ends the beat;
and a beat whose shots leave a hole is still a gap.
"""
import copy
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "skills", "batch-2", "skills", "real-compile", "scripts")
sys.path.insert(0, SCRIPTS)

import adapt  # noqa: E402
from real_core import base_shot  # noqa: E402


def layer(lid, asset, t0, t1, z=0, base=True, kind="video", **kw):
    L = dict(id=lid, z=z, kind=kind, asset=asset, anchor_word=0, anchor_text="w", offset_ms=0,
             t0=t0, t1=t1, fit="fit", chosen_by="creator", confidence="high", why="t", base=base)
    L.update(kw)
    return L


def reel(second_t0=3.0):
    return {
        "version": 1, "reel": {"title": "tiles", "fps": 30, "width": 1080, "height": 1920},
        "clock": {"mode": "measured", "total_s": 12.0},
        "assets_root": "/Volumes/Edit/tiles",
        "assets": [dict(id="A1", kind="video", dur_s=6.0, w=1920, h=1080, fps=30, file="Videos/a.mov", exists=False),
                   dict(id="A2", kind="video", dur_s=8.0, w=1920, h=1080, fps=30, file="Videos/b.mov", exists=False),
                   dict(id="A3", kind="image", w=1080, h=1920, file="Images/c.png", exists=False)],
        "beats": [
            dict(id="B1", name="two shots", t0=0.0, t1=8.0, w0=0, w1=3, narration="one two three four",
                 layers=[layer("B1.L1", "A1", 0.0, 3.0),
                         layer("B1.L2", "A2", second_t0, 8.0, z=1),
                         dict(id="B1.L3", z=2, kind="text", content="hello", style="caption", anchor_word=2,
                              anchor_text="three", offset_ms=0, t0=5.0, t1=6.5, fit="fit",
                              chosen_by="creator", confidence="high", why="t")],
                 audio=[], flags=[]),
            dict(id="B2", name="card", t0=8.0, t1=12.0, w0=4, w1=4, narration="five",
                 layers=[layer("B2.L1", "A3", 8.0, 12.0, kind="image")], audio=[], flags=[],
                 transition_in={"name": "Cross Dissolve", "dur_s": 1.0, "chosen_by": "creator"}),
        ],
        "open": {"unbound_layers": [], "unused_assets": [], "unresolved_specs": [], "questions": []},
    }


OPTS = {"stubs": False, "markers": False, "local_root": None, "stub_dir": None, "fallback_title": "t"}


class TiledBaseTests(unittest.TestCase):
    def test_tiles_become_consecutive_spine_items(self):
        story = adapt.adapt(reel(), copy.deepcopy(OPTS), [])
        beats = story["beats"]
        self.assertEqual([b["type"] for b in beats], ["video", "video", "image"])
        self.assertEqual([b["name"] for b in beats][:2], ["B1 two shots (1/2)", "B1 two shots (2/2)"])
        self.assertAlmostEqual(beats[0]["duration"], 3.0)
        self.assertAlmostEqual(beats[1]["duration"], 5.0)
        # the caption starts 5.0 s into the beat, i.e. 2.0 s into the second tile
        self.assertFalse(beats[0].get("overlays"))
        ov = beats[1]["overlays"]
        self.assertEqual(len(ov), 1)
        self.assertAlmostEqual(ov[0]["offset"], 2.0)
        self.assertAlmostEqual(ov[0]["duration"], 1.5)
        # the dissolve into the card sits on the card, and parity holds
        self.assertEqual(beats[2]["transition_in"]["duration"], 1.0)
        self.assertEqual(story["_parity"]["layers_in"], story["_parity"]["visual_elements_out"])

    def test_a_hole_is_still_a_gap(self):
        story = adapt.adapt(reel(second_t0=3.5), copy.deepcopy(OPTS), [])
        self.assertEqual(story["beats"][0]["type"], "gap")
        self.assertEqual(len(story["beats"][0]["overlays"]), 3)

    def test_dissolve_borrows_from_the_shot_that_ends_the_beat(self):
        b = reel()["beats"][0]
        self.assertEqual(base_shot(b, at="start")["id"], "B1.L1")
        self.assertEqual(base_shot(b, at="end")["id"], "B1.L2")
        self.assertEqual(base_shot(b)["id"], "B1.L1")

    def test_dissolve_refused_when_the_closing_shot_lacks_a_handle(self):
        r = reel()
        r["assets"][1]["dur_s"] = 5.2          # 5.0 s used from 0: 0.2 s left, a 1 s dissolve needs 0.5
        with self.assertRaises(adapt.Refusal):
            adapt.adapt(r, copy.deepcopy(OPTS), [])


if __name__ == "__main__":
    unittest.main()
