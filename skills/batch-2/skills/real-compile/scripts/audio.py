#!/usr/bin/env python3
"""Voice-track assembly helpers (import as a module). All audio = float32 numpy
mono arrays at SR=44100. Load anything via rd() (ffmpeg-decoded).

Ported unchanged from the retired reel-editor skill; scripts/voice.py assemble
is the front door. The 12 ms crossfade in xfade_concat is what stops a retake
splice from clicking — don't shorten it. put_demo and beating_peaks came across
with the rest and are still useful when a demo clip's own audio has to swell
under and then over the narration.

Typical flow:
    from audio import *
    t3 = rd("takes/3.wav"); patch = rd("takes/retake1.wav")
    fixed = xfade_concat([t3[:int(cut*SR)], patch[int(a*SR):int(b*SR)]])
    mix = Mix(total_seconds)
    mix.put(fixed, at=0.0)
    mix.put_demo(demo_audio, m0=..., live=(l0,l1), narr_end=..., gain=2.0)
    mix.save("master.wav")
"""
import subprocess, wave
import numpy as np

SR = 44100

def rd(path, sr=SR):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1",
                        "-ar", str(sr), "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()

def save(x, path, sr=SR):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

def xfade_concat(parts, ms=12):
    """Concatenate with short linear crossfades — click-free splices."""
    n = int(SR * ms / 1000)
    out = parts[0]
    for p in parts[1:]:
        a, b = out.copy(), p.copy()
        a[-n:] *= np.linspace(1, 0, n); b[:n] *= np.linspace(0, 1, n)
        out = np.concatenate([a[:-n], a[-n:] + b[:n], b[n:]])
    return out

def compress_pause(x, at_sec, keep_sec=0.2, window=1.5):
    """Shrink a silence around at_sec down to keep_sec (blank-elimination tool)."""
    a = int(max(0, at_sec - window) * SR); b = int((at_sec + window) * SR)
    seg = x[a:b]
    env = np.convolve(np.abs(seg), np.ones(2000) / 2000, "same")
    quiet = env < (env.max() * 0.06)
    if not quiet.any():
        return x
    idx = np.where(quiet)[0]
    q0, q1 = idx[0], idx[-1]
    keep = int(keep_sec * SR)
    if q1 - q0 <= keep:
        return x
    return np.concatenate([x[:a + q0 + keep // 2], x[a + q1 - keep // 2:]])

class Mix:
    def __init__(self, total_sec):
        self.x = np.zeros(int(total_sec * SR), dtype=np.float32)

    def put(self, seg, at, fade_in=0.0, fade_out=0.15, env=None):
        seg = seg.copy()
        if env is not None:
            seg *= env
        if fade_in > 0:
            n = int(fade_in * SR); seg[:n] *= np.linspace(0, 1, n)
        if fade_out > 0:
            n = int(fade_out * SR); seg[-n:] *= np.linspace(1, 0, n)
        i = int(at * SR)
        self.x[i:i + len(seg)] += seg[:len(self.x) - i]

    def put_demo(self, src, m0, m1, s0, live, narr_end, gain=2.0, bed=0.30):
        """Demo-clip audio, source-time-continuous with its visible video.
        Ducked bed under narration; swells to full as narration ends (Principle 4);
        ducks back down if its video outlives the live window."""
        l0, l1 = live
        seg = src[int(s0 * SR):int((s0 + (m1 - m0)) * SR)]
        n = len(seg); tt = np.arange(n) / SR + m0
        env = np.full(n, bed * gain, dtype=np.float32)
        ramp1 = min(l0 + 0.3, m1)
        env[tt >= ramp1] = gain
        sel = (tt >= narr_end) & (tt < ramp1)
        env[sel] = bed * gain + (gain - bed * gain) * (tt[sel] - narr_end) / max(ramp1 - narr_end, 1e-6)
        if m1 > l1 + 0.05:
            env[tt >= l1] = bed * gain * 0.95
        self.put(seg, m0, fade_in=0.25, fade_out=0.6, env=env)

    def save(self, path):
        peak = np.abs(self.x).max()
        if peak > 0.98:
            self.x *= 0.98 / peak
        save(self.x, path)

def beating_peaks(x, top=3, win_s=0.8, hop_s=0.25):
    """Rank moments by amplitude-beating strength (wawawa proxy) — for Principle 5
    moment-cue candidates. Returns [(t_sec, score), ...] best first."""
    hop, win = int(hop_s * SR), int(win_s * SR)
    scores = []
    for i0 in range(0, len(x) - win, hop):
        seg = x[i0:i0 + win]
        e = np.convolve(np.abs(seg), np.ones(1000) / 1000, "same")
        e = e - e.mean()
        E = np.abs(np.fft.rfft(e)) ** 2
        fr = np.fft.rfftfreq(len(e), 1 / SR)
        sc = E[(fr > 2) & (fr < 14)].sum() / max(E[(fr > 0.4) & (fr < 60)].sum(), 1e-9)
        scores.append((round(i0 / SR, 2), round(float(sc), 4)))
    scores.sort(key=lambda t: -t[1])
    out = []
    for t, s in scores:
        if all(abs(t - u) > 1.5 for u, _ in out):
            out.append((t, s))
        if len(out) == top:
            break
    return out
