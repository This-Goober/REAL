#!/usr/bin/env python3
"""
transcribe.py — rough, offline speech-to-text for narration takes.

    pip install pocketsphinx --break-system-packages
    python3 transcribe.py <dir-or-file.wav> [...]

Runs in the CONTAINER (not on the device), on the 16 kHz mono copies that
scan.py produced — those are ~1 MB each, so staging them is cheap.

pocketsphinx is deliberate: the pip wheel bundles its acoustic model, so it
works with no model download. Whisper is better but its weights are usually
unreachable from the sandbox. The output is rough — expect proper nouns and
domain jargon to come out mangled. That is fine. The job here is to work out
WHICH take covers WHICH part of the script, not to produce a clean transcript.
Read through the errors; the shape of the sentence is almost always legible.

Input must be 16 kHz mono 16-bit PCM WAV. Anything else gets silently poor
results, so convert first:
    ffmpeg -i in.wav -ar 16000 -ac 1 -c:a pcm_s16le out.wav
"""
import glob, os, sys


def main(args):
    try:
        from pocketsphinx import Decoder, Config, get_model_path
    except ImportError:
        sys.exit("pip install pocketsphinx --break-system-packages")

    mp = os.path.join(get_model_path(), "en-us")
    if not os.path.isdir(os.path.join(mp, "en-us")):
        mp = get_model_path()          # older wheel layouts
    cfg = Config(hmm=os.path.join(mp, "en-us"),
                 lm=os.path.join(mp, "en-us.lm.bin"),
                 dict=os.path.join(mp, "cmudict-en-us.dict"),
                 logfn=os.devnull)
    d = Decoder(cfg)

    files = []
    for a in args:
        files += sorted(glob.glob(os.path.join(a, "*.wav"))) if os.path.isdir(a) else [a]
    if not files:
        sys.exit("no wav files found")

    for f in files:
        with open(f, "rb") as fh:
            fh.read(44)
            data = fh.read()
        d.start_utt(); d.process_raw(data, False, True); d.end_utt()
        h = d.hyp()
        size = os.path.getsize(f)
        print(f"\n=== {os.path.basename(f)}  (~{size/32000:.1f}s)")
        print(h.hypstr if h else "(nothing decoded)")


if __name__ == "__main__":
    main(sys.argv[1:] or ["."])
