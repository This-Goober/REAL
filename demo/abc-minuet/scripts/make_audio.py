"""Piano rendering of the four Minuet bars (in C) with FluidR3 grand piano via tinysoundfont, 110 quarter notes a
minute. Needs tinysoundfont and the FluidR3_GM soundfont
(SOUNDFONT=path/to/FluidR3_GM.sf2)."""
import os, subprocess, wave, numpy as np, tinysoundfont
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # run from the demo folder
BPM, RATE = 110, 44100
# (beats, MIDI) — G C/ D/ E/ F/ | G C C | A F/ G/ A/ B/ | c C C |
NOTES = [(1, 67), (.5, 60), (.5, 62), (.5, 64), (.5, 65),
         (1, 67), (1, 60), (1, 60),
         (1, 69), (.5, 65), (.5, 67), (.5, 69), (.5, 71),
         (1, 72), (1, 60), (1, 60)]
beat = 60 / BPM
ev, t = [], 0.25
for b, p in NOTES:
    d = b * beat
    ev += [(t, 1, p), (t + d * 0.92, 0, p)]
    t += d
end = t + 1.2
ev.sort(key=lambda e: (e[0], e[1]))
s = tinysoundfont.Synth(gain=-4.0, samplerate=RATE)
s.program_select(0, s.sfload(os.environ.get("SOUNDFONT", "FluidR3_GM.sf2")), 0, 0)
out, pos = [], 0
for tm, on, p in ev + [(end, 0, 0)]:
    n = int(round(tm * RATE))
    if n > pos:
        out.append(np.frombuffer(s.generate(n - pos), dtype=np.float32).copy()); pos = n
    if on: s.noteon(0, p, 82)
    elif p: s.noteoff(0, p)
x = np.concatenate(out).reshape(-1, 2)
x = (x / max(1e-6, np.abs(x).max()) * 0.8 * 32767).astype(np.int16)
os.makedirs("work", exist_ok=True)
with wave.open("work/minuet.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(x.tobytes())
for name in ("minuet-piano", "minuet-piano-end"):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "work/minuet.wav", "-af", "afade=t=out:st=%.2f:d=1.0" % (end - 1.0),
                    "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "256k", f"media/Audio/{name}.mp3"], check=True)
print("minuet %.2fs at %d bpm" % (end, BPM))
