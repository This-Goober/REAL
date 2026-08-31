#!/usr/bin/env python3
"""Forced alignment + retake transcription (pocketsphinx — model bundled in the pip
wheel, works with no network). Audio in any format (ffmpeg-converted internally).

Ported unchanged from the retired reel-editor skill. Drive it through
scripts/voice.py, which knows what the rest of the pipeline expects; run it
directly for oovcheck and for free-transcribing a take you can't identify.

  align.py align <script.txt> <audio> <out.json> [--oov oov.json]
  align.py transcribe <audio>

align: script.txt is the DISPLAY text (case/punct kept). Output JSON is a list of
{"w": display_token, "n": normalized, "s": start_sec, "e": end_sec}.
Fails loudly if the audio doesn't match the text (that usually means the spoken words
differ from the script — free-transcribe the region to find out what was said).

--oov: JSON {"word": "PHONE SEQ", ...} for out-of-dictionary words. Common music ones
are built in. Check first with: align.py oovcheck <script.txt>
"""
import sys, json, wave, subprocess, tempfile, re, os

BUILTIN_OOV = {
 "soundwave": "S AW N D W EY V", "soundwaves": "S AW N D W EY V Z",
 "helpfulness": "HH EH L P F AH L N AH S",
 "overtone": "OW V ER T OW N", "overtones": "OW V ER T OW N Z",
 "overtone's": "OW V ER T OW N Z", "wawawawa": "W AA W AA W AA W AA",
 "synergetically": "S IH N ER JH EH T IH K L IY",
 "microtones": "M AY K R OW T OW N Z", "semitones": "S EH M IY T OW N Z",
 "tunable": "T UW N AH B AH L", "intonation": "IH N T AH N EY SH AH N",
 "vibrato": "V IH B R AA T OW", "arpeggio": "AA R P EH JH IY OW",
 "arpeggios": "AA R P EH JH IY OW Z", "pizzicato": "P IH T S IH K AA T OW",
}

def to16k(path):
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path,
                    "-ac", "1", "-ar", "16000", f.name], check=True)
    return f.name

def norm(tok):
    return tok.lower().strip('.,!?";:()[]').replace('"', "").replace("“", "").replace("”", "")

def make_decoder(extra_oov=None):
    from pocketsphinx import Decoder
    d = Decoder(samprate=16000)
    for w, p in {**BUILTIN_OOV, **(extra_oov or {})}.items():
        try:
            d.add_word(w, p, False)
        except Exception:
            pass
    return d

def align(script_path, audio_path, out_path, oov_path=None):
    display = open(script_path).read().split()
    toks = [norm(t) for t in display]
    toks_d = [t for t in toks if t]
    extra = json.load(open(oov_path)) if oov_path else None
    d = make_decoder(extra)
    missing = sorted({t for t in toks_d if d.lookup_word(t) is None})
    if missing:
        sys.exit(f"OOV words with no phones (supply via --oov): {missing}")
    d.set_align_text(" ".join(toks_d))
    wav = to16k(audio_path)
    with wave.open(wav) as f:
        data = f.readframes(f.getnframes())
    d.start_utt(); d.process_raw(data, full_utt=True); d.end_utt()
    if d.hyp() is None:
        sys.exit("ALIGNMENT FAILED — audio does not match script text. "
                 "Free-transcribe the audio to see what was actually said.")
    segs = [(s.word, s.start_frame / 100.0, s.end_frame / 100.0) for s in d.seg()
            if not s.word.startswith("<") and s.word != "(NULL)"]
    out, di = [], 0
    disp_nonempty = [w for w, t in zip(display, toks) if t]
    for w_, s, e in segs:
        base = re.sub(r"\(\d+\)$", "", w_)
        assert base == norm(disp_nonempty[di]), f"mismatch {base} vs {disp_nonempty[di]}"
        out.append({"w": disp_nonempty[di], "n": base, "s": round(s, 3), "e": round(e, 3)})
        di += 1
    assert di == len(disp_nonempty)
    json.dump(out, open(out_path, "w"))
    print(f"aligned {len(out)} words, span {out[0]['s']}–{out[-1]['e']}s")

def transcribe(audio_path):
    d = make_decoder()
    wav = to16k(audio_path)
    with wave.open(wav) as f:
        data = f.readframes(f.getnframes())
    d.start_utt(); d.process_raw(data, full_utt=True); d.end_utt()
    print(d.hyp().hypstr if d.hyp() else "(nothing recognized)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "align":
        oov = sys.argv[sys.argv.index("--oov") + 1] if "--oov" in sys.argv else None
        align(sys.argv[2], sys.argv[3], sys.argv[4], oov)
    elif cmd == "transcribe":
        transcribe(sys.argv[2])
    elif cmd == "oovcheck":
        d = make_decoder()
        toks = {norm(t) for t in open(sys.argv[2]).read().split()}
        print(sorted(t for t in toks if t and d.lookup_word(t) is None))
    else:
        sys.exit(__doc__)
