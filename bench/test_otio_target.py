#!/usr/bin/env python3
"""Tests for the `otio` compile target and the cross-target check.

    python3 -m pytest bench/test_otio_target.py -q      (or)  python3 bench/test_otio_target.py

No media is needed: every story declares its durations and sizes and is built
with probe=False, exactly as a story whose footage only exists on another Mac.
"""
import copy
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "skills", "batch-2", "skills", "real-compile", "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, HERE)

import targets  # noqa: E402
import fcpxml_edl  # noqa: E402
import otio_edl  # noqa: E402

STORY = {
    "project": "cross-target fixture", "event": "REAL", "frame_rate": "30",
    "width": 1080, "height": 1920, "assets_root": "/Volumes/Edit/fixture",
    "beats": [
        {"type": "video", "src": "Videos/a.mov", "start": 1.5, "duration": 4.0,
         "asset_duration": 10.0, "name": "B1 demo", "note": "narration: hello",
         "markers": [{"t": 0.5, "value": "must read by 2s"}],
         "overlays": [
             {"type": "image", "src": "Images/i.png", "lane": 1, "offset": 0.5,
              "duration": 2.0, "width": 1080, "height": 1920,
              "transform": {"scale": 0.6, "position": [0, 300]}},
             {"text": "they interfere", "lane": 2, "offset": 1.0, "duration": 1.2,
              "font_size": 40, "position": [0, -620], "shadow": True}]},
        {"type": "gap", "duration": 0.7, "name": "deliberate blank"},
        {"type": "image", "src": "Images/j.png", "duration": 3.0, "width": 1080,
         "height": 1920, "name": "B3 still",
         "overlays": [{"text": "Attention", "lane": 1, "offset": 0.0,
                       "duration": 1.5, "font_size": 132, "position": [0, 0]}]},
    ],
    "connected": [
        {"src": "Audio/v.wav", "type": "audio", "lane": -1, "offset": 0,
         "duration": 7.0, "asset_duration": 8.0, "role": "dialogue",
         "name": "narration — v.wav"},
        {"src": "Videos/a.mov", "type": "video", "src_enable": "audio", "lane": -2,
         "offset": 2.0, "duration": 3.0, "asset_duration": 10.0, "volume_db": -6},
    ],
}


def build_both(story, tmp, probe=False):
    fx, ot = targets.get("fcpxml"), targets.get("otio")
    f_path, o_path = os.path.join(tmp, "t.fcpxml"), os.path.join(tmp, "t.otio")
    rf = fx.build(story, f_path, base_dir=tmp, probe=probe)
    ro = ot.build(story, o_path, base_dir=tmp, probe=probe)
    return f_path, o_path, rf, ro


class OTIOTargetTests(unittest.TestCase):

    def test_registered(self):
        names = [n for n, _ext, _d in targets.available()]
        self.assertIn("otio", names)
        self.assertEqual(targets.get("otio").extension, ".otio")

    def test_cross_target_equivalence(self):
        with tempfile.TemporaryDirectory() as tmp:
            f_path, o_path, rf, ro = build_both(STORY, tmp)
            self.assertFalse(targets.get("otio").validate(o_path).errors)
            edl_f = fcpxml_edl.parse(f_path)
            edl_o = otio_edl.parse(o_path)
            rep = otio_edl.compare(edl_o, edl_f)
            self.assertTrue(rep["equal"], json.dumps(rep, indent=1))
            # 3 spine items + 3 overlays
            self.assertEqual(len(edl_o["events"]), 6)
            self.assertEqual(len(edl_o["audio"]), 2)
            self.assertEqual(edl_o["total_f"], (120 + 21 + 90))
            # every track is padded to the storyline's length
            import opentimelineio as otio
            tl = otio.adapters.read_from_file(o_path)
            self.assertEqual({int(t.duration().value) for t in tl.tracks}, {120 + 21 + 90})
            text = [e for e in edl_o["events"] if e["kind"] == "text"]
            self.assertEqual(sorted(e["text"] for e in text), ["Attention", "they interfere"])
            src_in = [e["src_in"] for e in edl_o["events"] if e["kind"] == "video"]
            self.assertEqual(src_in, [45])

    def test_fractional_rate_stays_on_grid(self):
        story = copy.deepcopy(STORY)
        story["frame_rate"] = "23.976"
        with tempfile.TemporaryDirectory() as tmp:
            _f, o_path, _rf, _ro = build_both(story, tmp)
            v = targets.get("otio").validate(o_path)
            self.assertFalse(v.errors, v.errors)
            raw = json.load(open(o_path))
            rate = raw["metadata"]["REAL"]["rate"]
            self.assertAlmostEqual(rate, 24000 / 1001, places=9)
            edl = otio_edl.parse(o_path)   # raises if any value is not integral
            self.assertEqual(edl["fps"], 24)

    def test_validate_catches_overrun(self):
        story = copy.deepcopy(STORY)
        story["beats"][0]["start"] = 8.0   # 8 + 4 > 10 s asset
        with tempfile.TemporaryDirectory() as tmp:
            _f, o_path, _rf, ro = build_both(story, tmp)
            self.assertTrue(any("only 10.00s long" in w for w in ro.warnings))
            v = targets.get("otio").validate(o_path)
            self.assertTrue(any("reads past the end" in e for e in v.errors), v.errors)

    def test_overlap_on_one_lane_refuses(self):
        story = copy.deepcopy(STORY)
        story["beats"][0]["overlays"].append(
            {"type": "image", "src": "Images/k.png", "lane": 1, "offset": 1.0,
             "duration": 1.0, "width": 1080, "height": 1920})
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Exception) as cm:
                targets.get("otio").build(story, os.path.join(tmp, "t.otio"),
                                          base_dir=tmp, probe=False)
            self.assertIn("overlap", str(cm.exception))

    def test_title_without_text_is_an_error(self):
        story = copy.deepcopy(STORY)
        story["beats"][2]["overlays"][0]["text"] = "   "
        with tempfile.TemporaryDirectory() as tmp:
            _f, o_path, _rf, _ro = build_both(story, tmp)
            v = targets.get("otio").validate(o_path)
            self.assertTrue(any("no text" in e for e in v.errors), v.errors)

    def test_compare_detects_a_one_frame_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            f_path, o_path, _rf, _ro = build_both(STORY, tmp)
            moved = copy.deepcopy(STORY)
            moved["beats"][0]["overlays"][0]["offset"] = 0.5 + 1 / 30
            o2 = os.path.join(tmp, "moved.otio")
            targets.get("otio").build(moved, o2, base_dir=tmp, probe=False)
            rep = otio_edl.compare(otio_edl.parse(o2), fcpxml_edl.parse(f_path))
            self.assertFalse(rep["equal"])
            self.assertEqual(len(rep["events"]["only_in_otio"]), 1)


if __name__ == "__main__":
    unittest.main()
