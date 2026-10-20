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
from targets import title_raster  # noqa: E402
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

    def test_raster_titles_are_stills_with_the_same_edl(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            fx, ot = targets.get("fcpxml"), targets.get("otio")
            f_path = os.path.join(tmp, "t.fcpxml")
            fx.build(STORY, f_path, base_dir=tmp, probe=False)
            o_path = os.path.join(tmp, "r.otio")
            ro = ot.build(STORY, o_path, base_dir=tmp, probe=False, titles="raster")
            self.assertTrue(any("rendered to" in w for w in ro.warnings), ro.warnings)
            raw = open(o_path).read()
            self.assertNotIn("GeneratorReference", raw)
            tdir = os.path.join(tmp, "r-titles")
            pngs = sorted(os.listdir(tdir))
            self.assertEqual(len(pngs), 2, pngs)
            centres = {}
            for p in pngs:
                im = Image.open(os.path.join(tdir, p))
                self.assertEqual(im.size, (1080, 1920))
                self.assertEqual(im.mode, "RGBA")
                box = im.getchannel("A").getbbox()
                self.assertIsNotNone(box, "nothing drawn in %s" % p)
                centres[p] = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            # "they interfere" sits at [0, -620] (620 px below centre), "Attention" at [0, 0];
            # Final Cut's layout box sits BASELINE_SHIFT_EM below that, at the template scale
            k = title_raster.template_scale(1920)
            shift = lambda size: title_raster.BASELINE_SHIFT_EM * size * k  # noqa: E731
            by_text = {p.split("-")[0]: c for p, c in centres.items()}
            self.assertAlmostEqual(by_text["they"][1], 960 + 620 + shift(40), delta=25)
            self.assertAlmostEqual(by_text["attention"][1], 960 + shift(132), delta=30)
            # the em follows Final Cut: 40 pt in a 1080x1920 project draws about 71 px
            they = Image.open(os.path.join(tdir, [p for p in pngs if p.startswith("they")][0]))
            tb = they.getchannel("A").getbbox()
            self.assertGreater(tb[3] - tb[1], 40 * k * 0.7)
            for c in centres.values():
                self.assertAlmostEqual(c[0], 540, delta=25)
            v = ot.validate(o_path)
            self.assertFalse(v.errors, v.errors)
            edl_o = otio_edl.parse(o_path)
            rep = otio_edl.compare(edl_o, fcpxml_edl.parse(f_path))
            self.assertTrue(rep["equal"], json.dumps(rep, indent=1))
            text = [e for e in edl_o["events"] if e["kind"] == "text"]
            self.assertEqual(sorted(e["text"] for e in text), ["Attention", "they interfere"])
            self.assertTrue(all(e.get("rendered", "").startswith("file:///") for e in text))
            # a rendered title whose picture is the wrong size is caught
            bad = Image.new("RGBA", (100, 100))
            bad.save(os.path.join(tdir, pngs[0]))
            v2 = ot.validate(o_path)
            self.assertTrue(any("rendered title is 100x100" in e for e in v2.errors), v2.errors)

    def test_raster_title_wraps_like_a_paragraph_box(self):
        from PIL import Image
        story = copy.deepcopy(STORY)
        story["beats"][2]["overlays"][0]["text"] = "Attention Is All You Need"
        story["beats"][2]["overlays"][0]["font_size"] = 72        # 128 px at the template scale
        k = title_raster.template_scale(1920)
        with tempfile.TemporaryDirectory() as tmp:
            o_path = os.path.join(tmp, "w.otio")
            targets.get("otio").build(story, o_path, base_dir=tmp, probe=False, titles="raster")
            tdir = os.path.join(tmp, "w-titles")
            png = [p for p in os.listdir(tdir) if p.startswith("attention")][0]
            box = Image.open(os.path.join(tdir, png)).getchannel("A").getbbox()
            self.assertLessEqual(box[2] - box[0], 1080 * 0.9 + 4)        # inside the box
            self.assertGreater(box[3] - box[1], 72 * k * 1.5)            # two lines or more
            self.assertAlmostEqual((box[1] + box[3]) / 2,
                                   960 + title_raster.BASELINE_SHIFT_EM * 72 * k, delta=30)
            # a rebuild prunes stills that no longer belong to the timeline
            story["beats"][2]["overlays"][0]["text"] = "Attention"
            targets.get("otio").build(story, o_path, base_dir=tmp, probe=False, titles="raster")
            self.assertFalse([p for p in os.listdir(tdir) if p.startswith("attention-is")])

    def test_raster_glow_only_title_is_visible(self):
        from PIL import Image
        story = copy.deepcopy(STORY)
        ov = story["beats"][2]["overlays"][0]
        ov.update({"face": False, "glow": {"color": [1, 0.878, 0.263, 1],
                                              "opacity": 1, "blur": 1, "radius": 0}})
        with tempfile.TemporaryDirectory() as tmp:
            o_path = os.path.join(tmp, "g.otio")
            targets.get("otio").build(story, o_path, base_dir=tmp, probe=False, titles="raster")
            raw = json.load(open(o_path))
            self.assertIn('"glow"', json.dumps(raw))
            tdir = os.path.join(tmp, "g-titles")
            png = [p for p in os.listdir(tdir) if p.startswith("attention")][0]
            im = Image.open(os.path.join(tdir, png))
            box = im.getchannel("A").getbbox()
            self.assertIsNotNone(box)
            r, g, b, a = im.crop(box).resize((1, 1), Image.BOX).getpixel((0, 0))
            self.assertGreater(r, b)      # yellow, not white: the glow is the ink

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
