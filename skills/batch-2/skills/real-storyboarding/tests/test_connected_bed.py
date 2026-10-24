"""Audio the creator describes as running under the whole reel is a connected span, and the
span carries one of the four audio kinds, so the reel it lands in validates."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

S = Path(__file__).resolve().parents[1] / "scripts"
NOTEBOOK = """---
reel: bed test
target: 10s
aspect: 9:16
---

## one

<Two notes that seem to fight each other.>
<video clip of me playing both notes #demo | audio of a quiet piano theme under the whole reel #bed>

## two

<When two frequencies are close, they interfere.>
<show image of two sine waves #waves>
"""
CATALOGUE = {"project": "t", "root": "/tmp/t", "generated": "2026-10-24", "script_beats": [], "assets": [
    {"id": "A1", "f": "Videos/demo.mov", "k": "video", "exists": True, "dur": 12.0, "w": 1080, "h": 1920, "fps": 30,
     "rotation": 0, "role": "demo", "shows": "both notes", "use": "B1", "beat": "B1", "binds_to": "", "tags": ["demo"]},
    {"id": "A2", "f": "Audio/theme.wav", "k": "audio", "exists": True, "dur": 60.0,
     "role": "piano theme", "shows": "quiet piano", "use": "under everything", "beat": "any", "binds_to": "", "tags": ["bed"]},
    {"id": "A3", "f": "Images/waves.png", "k": "image", "exists": True, "w": 1080, "h": 1920,
     "role": "waves", "shows": "two sine waves", "use": "B2", "beat": "B2", "binds_to": "", "tags": ["waves"]},
]}


class ConnectedBedTests(unittest.TestCase):
    def test_under_the_whole_reel_is_a_bed_span(self):
        d = Path(tempfile.mkdtemp())
        (d / "NOTEBOOK.md").write_text(NOTEBOOK)
        (d / "asset-catalog.json").write_text(json.dumps(CATALOGUE))
        py = sys.executable
        run = lambda *a: subprocess.run([py] + [str(x) for x in a], check=True, capture_output=True, text=True, cwd=d)
        run(S / "notebook.py", "parse", "NOTEBOOK.md", "-o", "notebook.json")
        run(S / "clock.py", "time", "notebook.json", "-o", "clock.json")
        run(S / "bind.py", "bind", "notebook.json", "asset-catalog.json", "-o", "bindings.json")
        run(S / "build.py", "build", "notebook.json", "clock.json", "bindings.json", "-o", "reel.json",
            "--assets-root", "/tmp/t")
        reel = json.loads((d / "reel.json").read_text())
        spans = reel.get("connected") or []
        self.assertEqual(len(spans), 1, spans)
        self.assertEqual(spans[0]["kind"], "bed")
        self.assertEqual(spans[0]["asset"], "A2")
        self.assertEqual(spans[0]["t0"], 0.0)
        self.assertAlmostEqual(spans[0]["t1"], reel["clock"]["total_s"], places=3)
        self.assertLess(spans[0]["duck_db"], 0)
        # the span is not also a lane inside the beat
        self.assertFalse([a for b in reel["beats"] for a in b["audio"] if a.get("asset") == "A2"])
        run(S / "build.py", "validate", "reel.json")


if __name__ == "__main__":
    unittest.main()
