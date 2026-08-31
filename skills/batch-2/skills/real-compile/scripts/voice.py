#!/usr/bin/env python3
"""
voice.py — assemble the voice track, measure it, and report the drift.

    python3 voice.py script   reel.json -o narration.txt
    python3 voice.py assemble takes.json -o master.wav
    python3 voice.py measure  --script narration.txt --audio master.wav \
                              -o measured.json [--oov oov.json]
    python3 voice.py delta    reel.json measured.json [-o delta.json]
                              [--tolerance 0.35]

THE RULE THIS SCRIPT EXISTS TO ENFORCE
--------------------------------------
Alignment re-times. It does not re-plan. Every placement upstream is anchored
to a word index, so when the measured clock replaces the estimated one the
words move and the placements do not — nothing is reconsidered, nothing is
re-chosen, nothing is re-fitted.

But nothing gets absorbed quietly either. `delta` prints the estimate-to-
measured difference per beat, in seconds. If a section has drifted far enough
that the pacing the creator approved no longer holds, say so and offer to send
them back to /real-storyboarding. An approved reel is not silently re-timed.

And this script does not write times into reel.json. The clock swap lives in
/real-storyboarding (`clock.py swap`) and there is exactly one implementation
of it. What comes out of here is `measured.json` — a word-index -> timestamp
map — and a report.

    takes.json (for `assemble`)
    {
      "takes":   ["takes/1.wav", "takes/2.wav", "takes/3.wav"],
      "patches": [{"take": 1, "from_s": 12.40, "to_s": 15.52,
                   "file": "takes/retake-a.wav", "in_s": 0.18, "out_s": 3.30}],
      "compress_pauses": [{"at_s": 30.2, "keep_s": 0.25}],
      "xfade_ms": 12
    }

A patch replaces from_s..to_s of take N with in_s..out_s of the patch file.
Splices are 12 ms crossfades, which is what stops a splice from clicking.
`voice.py assemble` prints the new total; that total is what tells you whether
the recorded read matches the plan at all before you spend time aligning it.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


# --------------------------------------------------------------------------
# script — the token stream the word indices index
# --------------------------------------------------------------------------

def words_of(text):
    """Tokenise narration the way the word index is counted upstream.

    Whitespace split, minus anything with no letter or digit in it. A dashed
    aside — like this one — puts a bare em dash between two spaces, and if that
    counted as a word every index after it would be off by one against
    /real-storyboarding's clock. It is also not a word the aligner can look up,
    so filtering here fixes both problems at once.
    """
    return [t for t in str(text or "").split() if any(c.isalnum() for c in t)]


def cmd_script(argv):
    reel = json.load(open(argv[2]))
    out = argv[argv.index("-o") + 1] if "-o" in argv else "narration.txt"
    beats = reel.get("beats") or []
    words, ranges, problems = [], [], []
    for b in beats:
        w0 = len(words)
        words += words_of(b.get("narration"))
        if len(words) == w0:
            continue
        ranges.append((b.get("id"), w0, len(words) - 1))
        if b.get("w0") is not None and b.get("w1") is not None:
            if int(b["w0"]) != w0 or int(b["w1"]) != len(words) - 1:
                problems.append(
                    "beat %s declares words %s–%s but its narration occupies "
                    "%d–%d of the concatenated script. The word index is the "
                    "one thing every placement hangs off; if it disagrees with "
                    "the text, alignment will re-time the wrong beats."
                    % (b.get("id"), b["w0"], b["w1"], w0, len(words) - 1))
    if not words:
        print("REFUSED — no narration text in this reel; there is nothing to "
              "align. If the reel has no voiceover, skip the voice step.")
        return 2
    if problems:
        print("REFUSED — the reel's word indices do not match its narration. "
              "%d problem(s):\n" % len(problems))
        for i, p in enumerate(problems, 1):
            print("  %d. %s" % (i, p))
        print("\nFix in /real-storyboarding. Nothing was written.")
        return 2
    with open(out, "w") as f:
        f.write(" ".join(words) + "\n")
    print("wrote %s — %d words across %d beat(s)" % (out, len(words), len(ranges)))
    print("word ranges: " + ", ".join("%s %d–%d" % r for r in ranges[:8])
          + (" …" if len(ranges) > 8 else ""))
    print("\nNext: check the vocabulary before you align —\n"
          "  python3 %s oovcheck %s" % (os.path.join(HERE, "align.py"), out))
    return 0


# --------------------------------------------------------------------------
# assemble — sequential takes + retake patches -> one voice master
# --------------------------------------------------------------------------

def cmd_assemble(argv):
    import audio as A

    plan = json.load(open(argv[2]))
    out = argv[argv.index("-o") + 1] if "-o" in argv else "master.wav"
    base = os.path.dirname(os.path.abspath(argv[2]))
    ms = plan.get("xfade_ms", 12)

    def path(p):
        return p if os.path.isabs(p) else os.path.join(base, p)

    takes = [A.rd(path(t)) for t in plan.get("takes") or []]
    if not takes:
        print("REFUSED — takes.json lists no takes.")
        return 2
    for p in plan.get("patches") or []:
        i = int(p["take"])
        t = takes[i]
        patch = A.rd(path(p["file"]))
        a = int(float(p["from_s"]) * A.SR)
        b = int(float(p["to_s"]) * A.SR)
        pa = int(float(p.get("in_s", 0)) * A.SR)
        pb = int(float(p["out_s"]) * A.SR) if p.get("out_s") else len(patch)
        takes[i] = A.xfade_concat([t[:a], patch[pa:pb], t[b:]], ms=ms)
        print("  patched take %d: %.2f–%.2fs <- %s (%.2fs)"
              % (i, p["from_s"], p["to_s"], os.path.basename(p["file"]),
                 (pb - pa) / A.SR))
    x = A.xfade_concat(takes, ms=ms) if len(takes) > 1 else takes[0]
    for c in plan.get("compress_pauses") or []:
        before = len(x)
        x = A.compress_pause(x, float(c["at_s"]), float(c.get("keep_s", 0.2)))
        print("  compressed the pause at %.2fs by %.2fs"
              % (c["at_s"], (before - len(x)) / A.SR))
    A.save(x, out)
    print("wrote %s — %.3fs, %d take(s), %d patch(es), %dms crossfades"
          % (out, len(x) / A.SR, len(takes), len(plan.get("patches") or []), ms))
    print("This file is the clock from here on. Align against it, not against "
          "any individual take.")
    return 0


# --------------------------------------------------------------------------
# measure — forced alignment -> measured.json
# --------------------------------------------------------------------------

def cmd_measure(argv):
    import align

    script = argv[argv.index("--script") + 1]
    audio_path = argv[argv.index("--audio") + 1]
    out = argv[argv.index("-o") + 1] if "-o" in argv else "measured.json"
    oov = argv[argv.index("--oov") + 1] if "--oov" in argv else None

    tmp = out + ".words.tmp"
    try:
        align.align(script, audio_path, tmp, oov)
    except SystemExit as e:
        print("REFUSED — %s\n\nAlignment failing almost always means the words "
              "spoken are not the words planned. Free-transcribe the region "
              "(`align.py transcribe clip.wav`) to find out what was actually "
              "said, then fix the script or the take. Do not paper over it by "
              "shifting times." % e)
        return 2
    except ImportError:
        print("REFUSED — pocketsphinx is not installed here. "
              "`pip install pocketsphinx --break-system-packages` (the "
              "acoustic model ships inside the wheel, so it works offline).")
        return 2
    words = json.load(open(tmp))
    os.remove(tmp)

    dur = _duration(audio_path) or (words[-1]["e"] if words else 0)
    measured = {
        "version": "1.0",
        "mode": "measured",
        "source": "forced alignment (pocketsphinx) of %s against %s"
                  % (os.path.basename(script), os.path.basename(audio_path)),
        "audio": os.path.abspath(audio_path),
        "total_s": round(float(dur), 3),
        "n_words": len(words),
        "words": [{"i": i, "w": w["w"], "s": w["s"], "e": w["e"]}
                  for i, w in enumerate(words)],
    }
    with open(out, "w") as f:
        json.dump(measured, f, indent=1)
    print("wrote %s — %d words, %.3fs of audio, first word at %.3fs, last ends "
          "at %.3fs" % (out, len(words), measured["total_s"],
                        words[0]["s"], words[-1]["e"]))
    print("\nThis is a measurement, not a plan. Nothing has been re-placed. "
          "Run `voice.py delta` next to see what it does to the approved "
          "pacing before anything is swapped.")
    return 0


def _duration(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:
        return None


# --------------------------------------------------------------------------
# delta — estimate vs measured, per beat, in seconds
# --------------------------------------------------------------------------

def cmd_delta(argv):
    reel = json.load(open(argv[2]))
    measured = json.load(open(argv[3]))
    out = argv[argv.index("-o") + 1] if "-o" in argv else None
    tol = float(argv[argv.index("--tolerance") + 1]) if "--tolerance" in argv \
        else 0.35

    words = measured.get("words") or []
    if not words:
        print("REFUSED — %s has no words." % argv[3])
        return 2
    n = len(words)
    beats = reel.get("beats") or []
    missing = [b.get("id") for b in beats
               if b.get("w0") is None or b.get("w1") is None]
    if missing:
        print("REFUSED — these beats carry no word anchors: %s.\n"
              "Word indices are what makes re-timing safe; without them a "
              "measured clock would have to guess which beat moved, which is "
              "re-planning. Fix in /real-storyboarding."
              % ", ".join(str(m) for m in missing))
        return 2

    rows, worst, drift_max = [], 0.0, 0.0
    for b in beats:
        w0, w1 = int(b["w0"]), int(b["w1"])
        if w0 >= n or w1 >= n:
            print("REFUSED — beat %s indexes word %d but the measured track "
                  "has %d words. The script that was read is not the script "
                  "that was planned; re-derive it with `voice.py script`."
                  % (b.get("id"), max(w0, w1), n))
            return 2
        m0, m1 = words[w0]["s"], words[w1]["e"]
        e0, e1 = float(b["t0"]), float(b["t1"])
        d_start = m0 - e0
        d_dur = (m1 - m0) - (e1 - e0)
        worst = max(worst, abs(d_dur))
        drift_max = max(drift_max, abs(d_start))
        rows.append({"beat": b.get("id"), "name": b.get("name"),
                     "est_t0": round(e0, 3), "est_t1": round(e1, 3),
                     "meas_t0": round(m0, 3), "meas_t1": round(m1, 3),
                     "d_start_s": round(d_start, 3),
                     "d_dur_s": round(d_dur, 3),
                     "over_tolerance": abs(d_dur) > tol})

    est_total = float((reel.get("clock") or {}).get("total_s") or 0)
    meas_total = float(measured.get("total_s") or words[-1]["e"])
    d_total = meas_total - est_total

    print("estimate vs measured — per beat, in seconds  (tolerance %.2fs)\n"
          % tol)
    print("  %-6s %-22s %9s %9s %9s %9s" %
          ("beat", "name", "est dur", "meas dur", "Δ start", "Δ dur"))
    for r in rows:
        flag = "  <-- over" if r["over_tolerance"] else ""
        print("  %-6s %-22s %9.2f %9.2f %+9.2f %+9.2f%s"
              % (r["beat"], (r["name"] or "")[:22],
                 r["est_t1"] - r["est_t0"], r["meas_t1"] - r["meas_t0"],
                 r["d_start_s"], r["d_dur_s"], flag))
    print("\n  total: estimated %.2fs, measured %.2fs (%+.2fs, %+.1f%%)"
          % (est_total, meas_total, d_total,
             100 * d_total / est_total if est_total else 0))
    print("  worst single-beat duration error %.2fs; largest start drift %.2fs"
          % (worst, drift_max))

    over = [r for r in rows if r["over_tolerance"]]
    holds = not over and abs(d_total) <= max(1.0, 0.02 * est_total)
    if holds:
        verdict = "PACING HOLDS"
        print("\n%s — every beat lands within tolerance. The measured clock "
              "can be swapped in upstream (`/real-storyboarding`, clock.py "
              "swap) and every placement survives unchanged; it just re-times."
              % verdict)
    else:
        verdict = "PACING DOES NOT HOLD"
        print("\n%s — %d beat(s) outside tolerance%s."
              % (verdict, len(over),
                 "" if abs(d_total) <= max(1.0, 0.02 * est_total)
                 else " and the total is off by %+.2fs" % d_total))
        print("Do NOT absorb this quietly. The reel that was approved is not "
              "the reel the read produced. Tell the creator which sections "
              "moved, in their terms (\"the demo runs %s than planned\"), and "
              "offer to send them back to /real-storyboarding to re-fit the "
              "pacing before anything is compiled."
              % ("longer" if (over and over[0]["d_dur_s"] > 0) else "shorter"))
    print("\nEither way: nothing here has been re-planned, and no times have "
          "been written back into reel.json.")

    if out:
        with open(out, "w") as f:
            json.dump({"verdict": verdict, "tolerance_s": tol,
                       "est_total_s": est_total, "meas_total_s": meas_total,
                       "d_total_s": round(d_total, 3),
                       "worst_beat_dur_error_s": round(worst, 3),
                       "max_start_drift_s": round(drift_max, 3),
                       "beats": rows}, f, indent=1)
        print("wrote " + out)
    return 0 if holds else 3


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    fn = {"script": cmd_script, "assemble": cmd_assemble,
          "measure": cmd_measure, "delta": cmd_delta}.get(cmd)
    if fn is None:
        print(__doc__)
        return 2
    return fn(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
