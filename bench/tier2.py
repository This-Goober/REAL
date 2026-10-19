#!/usr/bin/env python3
"""tier2.py — REAL reproducing an independently made cut from generated content.

Target: the Codex reference package in bench/ground-truth/<project>/ (720x1280,
30 fps, eSpeak narration, 7 shots + 7 transparent caption PNGs, frame EDL in
truth.json). REAL gets the media, the catalogue, the narration WAV and a
notebook; it aligns the narration itself with /real-compile's `voice.py
measure` (pocketsphinx) and plans on that measurement.

    python3 tier2.py PROJECT [--gt ground-truth] [--out work/tier2] [--lpips]

Modes (each a full pipeline run):
  A  default     pauses blank (named black gaps), no revisions
  B  hold        `clock.py time --pauses hold`, no revisions
  C  hold+edit   B + one creator revision per caption expressing the approved
                 rule "caption starts 400 ms after the cut" (`Bn: L2 offset = +300`,
                 the cut being 100 ms before the line's first word)

The notebook REAL gets is Codex's adapted notebook re-expressed in REAL's
notebook format: each caption is layered on its shot with `|` (Codex wrote them
as separate lines, which in REAL's format means a cut). Narration, descriptions
and tags are unchanged. The reformat is mechanical and saved next to the run.
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compose  # noqa: E402
import fcpxml_edl  # noqa: E402
import metrics  # noqa: E402

from run_real import SKILLS as SK  # the frozen copy (see run_real.py)
SB = os.path.join(SK, "real-storyboarding", "scripts")
CO = os.path.join(SK, "real-compile", "scripts")


def sh(*cmd, cwd=None, ok=True):
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True, cwd=cwd)
    if ok and r.returncode:
        raise SystemExit("FAILED %s\n%s%s" % (" ".join(cmd[:2]), r.stdout[-2000:], r.stderr[-2000:]))
    return r


def layered_notebook(src):
    """Codex's notebook -> REAL notebook with each caption layered on its shot."""
    out, pending = [], None
    for line in open(src).read().splitlines():
        m_v = re.match(r"^<(video clip of .*)>$", line.strip())
        m_c = re.match(r"^<(show image of caption .*)>$", line.strip())
        if m_v:
            pending = m_v.group(1)
            continue
        if m_c and pending:
            out.append("<%s | %s>" % (pending, m_c.group(1)))
            pending = None
            continue
        if pending:
            out.append("<%s>" % pending)
            pending = None
        out.append(line)
    if pending:
        out.append("<%s>" % pending)
    text = "\n".join(out) + "\n"
    text = text.replace("Exact timing is in EDIT-DECISIONS.csv.",
                        "Re-expressed for REAL: captions layered with |.")
    return text


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def alignment_report(clock_words, measured, onsets):
    """REAL's measured word starts vs the synthesiser's own word onsets."""
    a = [norm(w["w"]) for w in clock_words]
    b = [norm(o["text"]) for o in onsets]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    mw = {w["i"]: w for w in measured["words"]}
    diffs = []
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            i, j = blk.a + k, blk.b + k
            m = mw.get(i)
            if m is not None:
                diffs.append((m["s"] - onsets[j]["start"]) * 1000.0)
    if not diffs:
        return {"matched_words": 0}
    import numpy as np
    d = np.array(diffs)
    return {"matched_words": len(diffs), "words_clock": len(a), "words_onsets": len(b),
            "onset_err_ms_median": float(np.median(np.abs(d))),
            "onset_err_ms_p95": float(np.percentile(np.abs(d), 95)),
            "onset_err_ms_max": float(np.max(np.abs(d))),
            "onset_bias_ms_mean": float(np.mean(d)),
            "within_1_frame": float(np.mean(np.abs(d) <= 1000 / 30.0)),
            "within_3_frames": float(np.mean(np.abs(d) <= 3000 / 30.0))}


def split_tracks(edl):
    base = [e for e in edl["events"] if e["z"] == 0 and e["kind"] != "gap"]
    over = [e for e in edl["events"] if e["z"] > 0]
    return base, over


def boundary_stats(truth_ev, pred_ev):
    m = metrics.greedy_match(truth_ev, pred_ev, 0.5 - 1e-9)
    ins = [abs(pred_ev[j]["f0"] - truth_ev[i]["f0"]) for i, j, _ in m]
    outs = [abs(pred_ev[j]["f1"] - truth_ev[i]["f1"]) for i, j, _ in m]
    b = ins + outs
    f = lambda thr: (2 * len(metrics.greedy_match(truth_ev, pred_ev, thr - 1e-9))  # noqa: E731
                     / (len(truth_ev) + len(pred_ev))) if (truth_ev or pred_ev) else 1.0
    return {"n_truth": len(truth_ev), "n_pred": len(pred_ev), "matched@0.5": len(m),
            "f1@0.5": f(0.5), "f1@0.9": f(0.9), "f1@1.0": f(1.0),
            "in_err_mean_f": (sum(ins) / len(ins)) if ins else None,
            "out_err_mean_f": (sum(outs) / len(outs)) if outs else None,
            "max_err_f": max(b) if b else None,
            "within_1f": (sum(1 for x in b if x <= 1) / len(b)) if b else 0.0,
            "within_3f": (sum(1 for x in b if x <= 3) / len(b)) if b else 0.0}


def base_frame_accuracy(truth, edl):
    """Per-frame agreement of the PRIMARY track only (captions are transparent
    overlays, so the topmost-opaque rule of metrics.visible does not apply)."""
    n = truth["total_f"]

    def track(ev):
        t = [None] * n
        for e in ev:
            if e["z"] == 0 and e["kind"] in ("video", "image"):
                for f in range(max(0, e["f0"]), min(n, e["f1"])):
                    t[f] = e["asset"]
        return t
    a, b = track(truth["events"]), track(edl["events"])
    return {"frames": n, "base_frame_acc": sum(1 for x, y in zip(a, b) if x == y) / n,
            "black_frames_truth": sum(1 for x in a if x is None),
            "black_frames_pred": sum(1 for x in b if x is None),
            "total_f_truth": n, "total_f_pred": edl["total_f"]}


def run_mode(pdir, mode, gt, use_lpips):
    out = os.path.join(pdir, "mode-" + mode)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    media = os.path.join(pdir, "media")
    pauses = ["--pauses", "hold"] if mode in ("B", "C") else []
    sh(os.path.join(SB, "notebook.py"), "parse", os.path.join(pdir, "NOTEBOOK.md"),
       "-o", "notebook.json", cwd=out)
    sh(os.path.join(SB, "clock.py"), "time", "notebook.json", "-o", "clock.json",
       "--measured", os.path.join(pdir, "measured.json"), *pauses, cwd=out)
    sh(os.path.join(SB, "bind.py"), "bind", "notebook.json",
       os.path.join(pdir, "asset-catalog.json"), "-o", "bindings.json", cwd=out)
    sh(os.path.join(SB, "build.py"), "build", "notebook.json", "clock.json", "bindings.json",
       "-o", "reel.json", "--assets-root", media, "--stubs-dir", "stubs", cwd=out)
    reel = json.load(open(os.path.join(out, "reel.json")))
    revs = []
    for b in reel["beats"]:
        # classify every caption layer the way a creator would in the tracks page
        for l in b["layers"]:
            if l["kind"] == "image" and l.get("asset", "").startswith("img"):
                pass
        if mode == "C":
            slot = next((l["id"].split(".")[-1] for l in b["layers"]
                         if (l.get("asset") or "").startswith("img")), None)
            if slot:
                revs.append("%s: %s offset = +300" % (b["id"], slot))
    if revs:
        open(os.path.join(out, "revisions.txt"), "w").write("\n".join(revs) + "\n")
        sh(os.path.join(SB, "revise.py"), "apply", "reel.json", "revisions.txt",
           "-o", "reel.json", "--clock", "clock.json", cwd=out)
    sh(os.path.join(SB, "build.py"), "validate", "reel.json", cwd=out)
    sh(os.path.join(CO, "adapt.py"), "reel.json", "-o", "story.json",
       "--assets-root-local", media, cwd=out)
    sh(os.path.join(CO, "compile.py"), "build", "story.json", "timeline.fcpxml", cwd=out)
    v = sh(os.path.join(CO, "compile.py"), "validate", "timeline.fcpxml", "--local-root",
           media, cwd=out, ok=False)
    edl = fcpxml_edl.parse(os.path.join(out, "timeline.fcpxml"))
    json.dump(edl, open(os.path.join(out, "edl.json"), "w"), indent=1)
    truth = json.load(open(os.path.join(gt, "truth.json")))
    tb, to = split_tracks(truth)
    pb, po = split_tracks(edl)
    row = {"mode": mode, "validate_ok": v.returncode == 0, "revisions": len(revs),
           "shots": boundary_stats(tb, pb), "captions": boundary_stats(to, po),
           **base_frame_accuracy(truth, edl)}
    real_mp4 = os.path.join(out, "real.mp4")
    compose.render(edl, media, real_mp4)
    row["pixel_vs_reference"] = metrics.pixel(os.path.join(gt, "reference.mp4"), real_mp4,
                                              use_lpips=use_lpips, every=3)
    row["pixel_vs_truth_render"] = metrics.pixel(os.path.join(pdir, "truth-render.mp4"),
                                                 real_mp4, use_lpips=use_lpips, every=3)
    json.dump(row, open(os.path.join(out, "score.json"), "w"), indent=1)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--gt", default=os.path.join(HERE, "ground-truth"))
    ap.add_argument("--out", default=os.path.join(HERE, "work", "tier2"))
    ap.add_argument("--modes", default="A,B,C")
    ap.add_argument("--lpips", action="store_true")
    ap.add_argument("--realign", action="store_true")
    a = ap.parse_args()
    gt = os.path.abspath(os.path.join(a.gt, a.project))
    pdir = os.path.abspath(os.path.join(a.out, a.project))
    os.makedirs(pdir, exist_ok=True)
    media = os.path.join(pdir, "media")
    if not os.path.exists(media):
        os.symlink(os.path.join(gt, "media"), media)
    # inputs REAL sees
    open(os.path.join(pdir, "NOTEBOOK.md"), "w").write(layered_notebook(os.path.join(gt, "NOTEBOOK.md")))
    cat = json.load(open(os.path.join(gt, "asset-catalog.json")))
    cat["root"] = media
    json.dump(cat, open(os.path.join(pdir, "asset-catalog.json"), "w"), indent=1)
    # the words REAL indexes, in REAL's own tokenisation, are what gets aligned
    tmp = os.path.join(pdir, "_words")
    os.makedirs(tmp, exist_ok=True)
    sh(os.path.join(SB, "notebook.py"), "parse", os.path.join(pdir, "NOTEBOOK.md"),
       "-o", "notebook.json", cwd=tmp)
    sh(os.path.join(SB, "clock.py"), "time", "notebook.json", "-o", "clock.json", cwd=tmp)
    words = json.load(open(os.path.join(tmp, "clock.json")))["words"]
    open(os.path.join(pdir, "narration.txt"), "w").write(" ".join(w["w"] for w in words) + "\n")
    if os.path.exists(os.path.join(pdir, "measured.json")) and not a.realign:
        r = subprocess.CompletedProcess([], 0, "reusing measured.json (--realign to redo)", "")
    else:
        r = sh(os.path.join(CO, "voice.py"), "measure", "--script", os.path.join(pdir, "narration.txt"),
           "--audio", os.path.join(gt, "narration.wav"), "-o",
           os.path.join(pdir, "measured.json"), ok=False)
    print(r.stdout.strip()[-600:])
    if r.returncode:
        raise SystemExit("alignment refused; see above")
    measured = json.load(open(os.path.join(pdir, "measured.json")))
    onsets = json.load(open(os.path.join(gt, "narration.json")))["word_onsets"]
    report = {"project": a.project, "alignment": alignment_report(words, measured, onsets)}
    truth = json.load(open(os.path.join(gt, "truth.json")))
    tr = os.path.join(pdir, "truth-render.mp4")
    if not os.path.exists(tr):
        compose.render(truth, media, tr)
    rb = os.path.join(pdir, "renderer-baseline.json")
    if not os.path.exists(rb):
        json.dump(metrics.pixel(os.path.join(gt, "reference.mp4"), tr, use_lpips=a.lpips, every=3),
                  open(rb, "w"), indent=1)
    report["renderer_baseline"] = json.load(open(rb))
    prev = os.path.join(pdir, "report.json")
    report["modes"] = (json.load(open(prev)).get("modes", {}) if os.path.exists(prev) else {})
    for m in a.modes.split(","):
        report["modes"][m] = run_mode(pdir, m, gt, a.lpips)
        s = report["modes"][m]
        print("mode %s  shots F1@1=%.2f in=%.1ff  captions F1@1=%.2f in=%.1ff  base frames %.3f  black %d/%d  SSIM %.3f"
              % (m, s["shots"]["f1@1.0"], s["shots"]["in_err_mean_f"] or -1,
                 s["captions"]["f1@1.0"], s["captions"]["in_err_mean_f"] or -1,
                 s["base_frame_acc"], s["black_frames_pred"], s["black_frames_truth"],
                 s["pixel_vs_reference"]["ssim_mean"]))
    json.dump(report, open(os.path.join(pdir, "report.json"), "w"), indent=1)
    print(json.dumps(report["alignment"], indent=1))


if __name__ == "__main__":
    main()
