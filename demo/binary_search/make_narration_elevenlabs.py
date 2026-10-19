#!/usr/bin/env python3
"""make_narration_elevenlabs.py — one ElevenLabs take of the full script, plus
the provider's own word times kept aside for comparison.

    python3 make_narration_elevenlabs.py [--script pass1-estimated/narration.txt]
                                         [--out .../Audio/narration.wav]

The request goes through bench/ground-truth/elevenlabs_narration.py, which
reads the API key at run time from ~/.elevenlabs/env and never writes it
anywhere. The raw response is cached under elevenlabs-takes/ keyed by the
request body, so re-running this script costs nothing; only a changed script
or voice setting is a new billable request. Authorised by the authors (18 October).

Output WAV: 48 kHz stereo PCM, 150 ms lead-in, 1 s tail, like the system-voice
take it replaces, so the narration lane never runs past the file after a retime.
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
HELPER = os.path.join(ROOT, "bench", "ground-truth", "elevenlabs_narration.py")
MEDIA = os.path.join(HERE, "media")
LEAD, TAIL = 0.15, 1.0


def load_helper():
    spec = importlib.util.spec_from_file_location("eleven", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=os.path.join(HERE, "pipeline", "narration.txt"))
    ap.add_argument("--out", default=os.path.join(MEDIA, "Audio", "narration.wav"))
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()

    el = load_helper()
    text = open(a.script).read().strip()
    body = {"text": text, "model_id": el.MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.15,
                               "use_speaker_boost": True, "speed": a.speed},
            "seed": 1706}
    takes = os.path.join(HERE, "elevenlabs-takes")
    from pathlib import Path
    response, fp = el.request_take(body, Path(takes))
    rate = el.RATE
    audio = el.decode(response)                      # 44.1 kHz mono float32
    active = np.flatnonzero(np.abs(audio) > 0.001)
    if not len(active):
        sys.exit("empty audio")
    left = max(0, int(active[0]) - int(0.05 * rate))
    right = min(len(audio), int(active[-1]) + int(0.05 * rate) + 1)
    audio = audio[left:right]
    out_audio = np.concatenate([np.zeros(int(LEAD * rate), np.float32), audio,
                                np.zeros(int(TAIL * rate), np.float32)])
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(rate), "-ac", "1",
                    "-i", "-", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", a.out],
                   input=out_audio.tobytes(), check=True)

    al = response.get("normalized_alignment") or response.get("alignment")
    words = []
    if al:
        chars = "".join(al["characters"])
        for m in re.finditer(r"\S+", chars):
            s = al["character_start_times_seconds"][m.start()] - left / rate + LEAD
            e = al["character_end_times_seconds"][m.end() - 1] - left / rate + LEAD
            words.append({"w": m.group(), "s": round(s, 4), "e": round(e, 4)})
    meta = {"provenance": "ElevenLabs API neural narration", "model": el.MODEL,
            "voice_id": el.VOICE, "voice_name": el.VOICE_NAME, "take": fp,
            "request_chars": len(text), "speed": a.speed, "lead_s": LEAD, "tail_s": TAIL,
            "trim_left_s": round(left / rate, 4), "duration_s": round(len(out_audio) / rate, 3),
            "audio": a.out, "words": words,
            "note": "provider character alignment grouped into whitespace tokens; a comparison "
                    "signal, not acoustic ground truth (see E06). REAL's clock comes from "
                    "voice.py measure (PocketSphinx) on the WAV."}
    json.dump(meta, open(os.path.join(HERE, "provider-words.json"), "w"), indent=1)
    print("take %s  voice %s  %d chars  %.2fs of audio (+%.2fs lead, +%.1fs tail)  %d provider words"
          % (fp, el.VOICE_NAME, len(text), (right - left) / rate, LEAD, TAIL, len(words)))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
