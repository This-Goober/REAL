"""Workaround for REAL finding 10: each narration clip ends exactly at the aligner's end of its last word, and the
aligner puts word ends early, so lines lose their last syllable; a take split across two beats also loses the gap
between them. Run between adapt and compile: extend every narration clip to the start of the next one (minus one
frame), or by at most MAX_TAIL seconds, never past the end of the voice file."""
import json, subprocess, sys
MAX_TAIL = 1.0
FPS = 30
p = sys.argv[1] if len(sys.argv) > 1 else "timeline/story.json"
S = json.load(open(p))
from fractions import Fraction
fps = float(Fraction(str(S.get("frame_rate", FPS))))
q = lambda t: round(round(t * fps) / fps, 6)
clips = sorted([c for c in S["connected"] if c.get("role") == "dialogue"], key=lambda c: c["offset"])
src = "media/" + clips[0]["src"]
file_len = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]))
for i, c in enumerate(clips):
    end = c["offset"] + c["duration"]
    limit = clips[i + 1]["offset"] if i + 1 < len(clips) else end + MAX_TAIL
    limit = min(limit, end + MAX_TAIL, c["offset"] + (file_len - c["start"]) - 1 / fps)
    if limit > end:
        c["duration"] = q(limit - c["offset"])
        print("narration at %6.2fs: +%.2fs tail" % (c["offset"], c["duration"] - (end - c["offset"])))
json.dump(S, open(p, "w"), indent=1)
