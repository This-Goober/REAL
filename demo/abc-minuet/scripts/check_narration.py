"""After compile: every narration clip must end after the speech it carries. Compares each narration window (read
from timeline/story.json, in file time) with where speech actually stops in the voice track (silencedetect). Exit 1
if any line loses more than 60 ms."""
import json, re, subprocess, sys
import os; os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # run from the demo folder
S = json.load(open("timeline/story.json"))
clips = [c for c in S["connected"] if c.get("role") == "dialogue"]
src = "media/" + clips[0]["src"]
err = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", "silencedetect=n=-40dB:d=0.25", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
stops = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
silences = list(zip(stops, ends + [1e9] * (len(stops) - len(ends))))
bad = 0
clips = sorted(clips, key=lambda c: c["start"])
for i, c in enumerate(clips):
    a, b = c["start"], c["start"] + c["duration"]
    if i + 1 < len(clips) and clips[i + 1]["start"] - b <= 0.05:   # the next clip carries on from here
        print("%-10s file %6.2f-%6.2f  %s" % ("narration", a, b, "runs straight into the next clip, ok"))
        continue
    in_silence = any(s0 - 0.03 <= b <= s1 for s0, s1 in silences)
    cut = 0.0 if in_silence else min([s0 for s0, _ in silences if s0 > b] or [b]) - b
    bad += cut > 0.06
    print("%-10s file %6.2f-%6.2f  %s" % ("narration", a, b, "CUT %.2fs of speech" % cut if cut > 0.06 else "ends in a pause, ok"))
sys.exit(1 if bad else 0)
