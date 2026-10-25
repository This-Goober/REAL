#!/usr/bin/env python3
"""narrate.py — the six narration takes, one per line of source/narration.txt.

    python3 scripts/narrate.py --engine elevenlabs [--voice George] [--model eleven_multilingual_v2]
    python3 scripts/narrate.py --engine kokoro [--voice am_michael] [--speed 1.0]     (open weights, local)
    python3 scripts/narrate.py --engine edge [--voice en-US-AndrewMultilingualNeural] [--rate +12%]
    ... [--out source/narration/<engine>]  to keep a read aside; media/Audio holds the one in use

Writes media/Audio/take-01.wav … take-06.wav (48 kHz mono PCM). Each file is
trimmed to start on its first word, found by force-aligning the line to the
synthesized audio with the compile skill's aligner, because the storyboard
places a take at the measured start of its first word. The read is a stand-in
for a human recording: replace the files and rebuild, every placement follows
its word.

ElevenLabs needs a key: the environment variable ELEVENLABS_API_KEY, a
`ELEVENLABS_API_KEY=...` line in ~/.elevenlabs/env, or the file
~/.config/elevenlabs/api_key (the key alone). Kokoro needs `pip install kokoro
soundfile` (it downloads the weights from Hugging Face on first use). The key never leaves this
machine except in the request header to api.elevenlabs.io. The voice is given
by name (looked up in the account's voice list) or as a voice id.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO = HERE.parent
ROOT = DEMO.parents[1]
ALIGN = ROOT / "skills/batch-2/skills/real-compile/scripts/align.py"
API = "https://api.elevenlabs.io/v1"


def key():
    """ELEVENLABS_API_KEY from the environment, from ~/.elevenlabs/env (KEY=value
    lines), or from ~/.config/elevenlabs/api_key (the key alone)."""
    k = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("XI_API_KEY")
    for f in (Path.home() / ".elevenlabs/env", Path.home() / ".elevenlabs/.env"):
        if not k and f.is_file():
            for line in f.read_text().splitlines():
                line = line.strip().removeprefix("export ").strip()
                if line.startswith(("ELEVENLABS_API_KEY=", "XI_API_KEY=")):
                    k = line.split("=", 1)[1].strip().strip("'\"")
    f = Path.home() / ".config/elevenlabs/api_key"
    if not k and f.is_file():
        k = f.read_text().strip()
    if not k:
        sys.exit("no ElevenLabs key: set ELEVENLABS_API_KEY, or put ELEVENLABS_API_KEY=... in ~/.elevenlabs/env")
    return k


def kokoro_tts(voice, speed, text, out_wav):
    """Kokoro-82M (Apache 2.0), run locally: 24 kHz mono."""
    import wave
    import numpy as np
    from kokoro import KPipeline
    pipe = kokoro_tts.pipe = getattr(kokoro_tts, "pipe", None) or KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    chunks = [audio for _gs, _ps, audio in pipe(text, voice=voice, speed=speed)]
    audio = np.concatenate([np.asarray(c, dtype="float32") for c in chunks])
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm.tobytes())


# ElevenLabs' premade voices, for a key that may speak but not list voices
PREMADE = {"george": "JBFqnCBsd6RMkjVDRZzb", "adam": "pNInz6obpgDQGcFmaJgB", "rachel": "21m00Tcm4TlvDq8ikWAM",
           "daniel": "onwK4e9ZLuTAKqWW03F9", "brian": "nPczCjzI2devNBz1zQrb", "liam": "TX3LPaxmHKxFdv7VOQHJ",
           "charlotte": "XB0fDUnXU5powFXDhCwa", "sarah": "EXAVITQu4vr4xnSDxMaL", "matilda": "XrExE9yKIg1WjnnlVkGX",
           "bill": "pqHfZKP75CvOlQylNhV4", "callum": "N2lVS1w4EtoT3dr4eOWO", "eric": "cjVigY5qzO86Huf0OWal",
           "roger": "CwhRBWXzGAHq8TQ4Fs17", "laura": "FGY2WhTYpPnrIDTdsKH5", "lily": "pFZP5JQG7iQjIQuC4Bku",
           "aria": "9BWtsMINqrJLrRacOk9x", "chris": "iP95p4xoKVk53GoZ742B", "jessica": "cgSgspJ2msm6clMCkdW9"}


def eleven_voice_id(k, voice):
    if len(voice) >= 20 and " " not in voice:          # already an id
        return voice
    try:
        req = urllib.request.Request(API + "/voices", headers={"xi-api-key": k})
        voices = json.load(urllib.request.urlopen(req, timeout=30))["voices"]
    except urllib.error.HTTPError as e:
        if e.code == 401 and voice.lower() in PREMADE:   # a key restricted to speech
            return PREMADE[voice.lower()]
        raise
    for v in voices:
        if v["name"].lower() == voice.lower():
            return v["voice_id"]
    if voice.lower() in PREMADE:
        return PREMADE[voice.lower()]
    names = ", ".join(sorted(v["name"] for v in voices))
    sys.exit("no voice named %r in this account; available: %s" % (voice, names))


def eleven_tts(k, voice_id, model, text, out_mp3, stability, similarity, style):
    body = json.dumps({"text": text, "model_id": model,
                       "voice_settings": {"stability": stability, "similarity_boost": similarity,
                                          "style": style, "use_speaker_boost": True}}).encode()
    req = urllib.request.Request("%s/text-to-speech/%s?output_format=mp3_44100_128" % (API, voice_id),
                                 data=body, method="POST",
                                 headers={"xi-api-key": k, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=120) as r:
        Path(out_mp3).write_bytes(r.read())


def edge_tts(voice, rate, text, out_mp3):
    exe = os.environ.get("EDGE_TTS", "edge-tts")
    subprocess.run([exe, "--voice", voice, "--rate=%s" % rate, "--text", text, "--write-media", out_mp3],
                   check=True, capture_output=True)


def to_wav(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src,
                    "-af", "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,"
                           "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,areverse",
                    "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", dst], check=True)


def first_word_s(line, wav, oov):
    with tempfile.TemporaryDirectory() as d:
        script = Path(d) / "line.txt"
        script.write_text(line + "\n")
        out = Path(d) / "words.json"
        py = os.environ.get("REAL_PYTHON") or shutil.which("python3") or sys.executable   # the one with pocketsphinx
        cmd = [py, str(ALIGN), "align", str(script), wav, str(out)]
        if oov:
            cmd += ["--oov", oov]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            sys.exit("alignment failed for %r:\n%s" % (line[:50], (r.stdout + r.stderr)[-600:]))
        words = json.load(open(out))
    return float(words[0]["s"]), len(words)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=("elevenlabs", "kokoro", "edge"), default="elevenlabs")
    ap.add_argument("--voice", default=None, help="elevenlabs: a voice name or id (default George); "
                                                  "kokoro: a voice (default am_michael); "
                                                  "edge: a voice name (default en-US-AndrewMultilingualNeural)")
    ap.add_argument("--speed", type=float, default=1.0, help="kokoro only")
    ap.add_argument("--model", default="eleven_multilingual_v2")
    ap.add_argument("--rate", default="+12%", help="edge only")
    ap.add_argument("--stability", type=float, default=0.5)
    ap.add_argument("--similarity", type=float, default=0.8)
    ap.add_argument("--style", type=float, default=0.15)
    ap.add_argument("--script", default=str(DEMO / "source/narration.txt"))
    ap.add_argument("--oov", default=str(DEMO / "source/oov.json"))
    ap.add_argument("--out", default=str(DEMO / "media/Audio"))
    a = ap.parse_args()
    lines = [ln.strip() for ln in open(a.script) if ln.strip()]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.engine == "elevenlabs":
        k = key()
        voice = a.voice or "George"
        vid = eleven_voice_id(k, voice)
        print("elevenlabs voice %s (%s), model %s" % (voice, vid, a.model))
    elif a.engine == "kokoro":
        voice = a.voice or "am_michael"
        print("kokoro voice %s, speed %.2f (hexgrad/Kokoro-82M, local)" % (voice, a.speed))
    else:
        voice = a.voice or "en-US-AndrewMultilingualNeural"
        print("edge voice %s, rate %s" % (voice, a.rate))
    receipt = {"engine": a.engine, "voice": voice,
               "model": {"elevenlabs": a.model, "kokoro": "hexgrad/Kokoro-82M", "edge": None}[a.engine],
               "rate": a.rate if a.engine == "edge" else None,
               "speed": a.speed if a.engine == "kokoro" else None, "takes": []}
    with tempfile.TemporaryDirectory() as d:
        for i, line in enumerate(lines, 1):
            spoken = line.replace("REAL", "Real")          # read as a word, not spelled out
            mp3 = os.path.join(d, "take-%02d.mp3" % i)
            raw = os.path.join(d, "take-%02d.raw.wav" % i)
            if a.engine == "elevenlabs":
                eleven_tts(k, vid, a.model, spoken, mp3, a.stability, a.similarity, a.style)
            elif a.engine == "kokoro":
                mp3 = os.path.join(d, "take-%02d.kokoro.wav" % i)
                kokoro_tts(voice, a.speed, spoken, mp3)
            else:
                edge_tts(voice, a.rate, spoken, mp3)
            to_wav(mp3, raw)
            t0, n = first_word_s(line, raw, a.oov if os.path.exists(a.oov) else None)
            final = out / ("take-%02d.wav" % i)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t0, "-i", raw,
                            "-c:a", "pcm_s16le", str(final)], check=True)
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                        "-of", "csv=p=0", str(final)], capture_output=True, text=True).stdout)
            print("  take-%02d  %5.2f s  %d words  (first word was at %.3f s)  %s" % (i, dur, n, t0, line[:48]))
            receipt["takes"].append({"file": final.name, "line": line, "seconds": round(dur, 3),
                                     "words": n, "trimmed_s": round(t0, 3)})
    (out / "narration-receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print("wrote %d takes to %s" % (len(lines), out))


if __name__ == "__main__":
    main()
