#!/usr/bin/env python3
"""metrics.py — score a compiled timeline against the reference.

Three levels, as bench/README.md explains:

  structural  — the FCPXML parsed back to an EDL vs truth.json. Shot-level
                precision/recall/F1 (CineBench), greedy IoU-matched F1@θ
                (MEDit-Bench), Kendall tau on primary-track order, in/out
                error in frames, time coverage (EditDuet), gap frames.
  pixel       — the two renders compared frame by frame: SSIM, PSNR, LPIPS,
                and the per-frame match rate.
  decoded     — the marker strips read back from the REAL render vs the
                truth render: which asset / which source frame is on screen.

    python3 metrics.py structural truth.json edl.json
    python3 metrics.py pixel truth.mp4 real.mp4 [--lpips] [--every 1]
    python3 metrics.py decoded truth.mp4 real.mp4
"""
import json
import subprocess
import sys

import numpy as np

FPS = 30


# ------------------------------------------------------------- structural

def visible(events, total_f):
    """Topmost opaque visual per frame -> (asset or 'gap', z) arrays."""
    top = [None] * total_f
    for e in sorted(events, key=lambda e: e["z"]):
        if e["kind"] not in ("video", "image"):
            continue
        for f in range(max(0, e["f0"]), min(total_f, e["f1"])):
            top[f] = (e["asset"], e.get("src_in", 0) + (f - e["f0"]) if e["kind"] == "video" else 0)
    return top


def kendall_tau(a, b):
    """Kendall tau between two orderings of (mostly) the same items; items
    missing from either side are ignored."""
    common = [x for x in a if x in b]
    if len(common) < 2:
        return 1.0 if common == [x for x in b if x in a] else 0.0
    pos = {x: i for i, x in enumerate(b)}
    conc = disc = 0
    for i in range(len(common)):
        for j in range(i + 1, len(common)):
            d = pos[common[i]] - pos[common[j]]
            if d < 0:
                conc += 1
            elif d > 0:
                disc += 1
    n = conc + disc
    return (conc - disc) / n if n else 1.0


def iou(a, b):
    inter = max(0, min(a["f1"], b["f1"]) - max(a["f0"], b["f0"]))
    union = max(a["f1"], b["f1"]) - min(a["f0"], b["f0"])
    return inter / union if union else 0.0


def same_identity(a, b):
    if a["kind"] != b["kind"]:
        return False
    if a["kind"] == "text":
        return a.get("text", "").strip().lower() == b.get("text", "").strip().lower()
    return a.get("asset") == b.get("asset")


def greedy_match(truth, pred, thr):
    """One-to-one matching, best IoU first, same identity, IoU >= thr."""
    pairs = []
    for i, t in enumerate(truth):
        for j, p in enumerate(pred):
            if same_identity(t, p):
                v = iou(t, p)
                if v >= thr:
                    pairs.append((v, i, j))
    pairs.sort(reverse=True)
    used_t, used_p, matched = set(), set(), []
    for v, i, j in pairs:
        if i in used_t or j in used_p:
            continue
        used_t.add(i)
        used_p.add(j)
        matched.append((i, j, v))
    return matched


def structural(truth, edl):
    T = [e for e in truth["events"] if e["kind"] != "gap"]
    P = [e for e in edl["events"] if e["kind"] != "gap"]
    out = {"n_truth": len(T), "n_pred": len(P)}
    # shot-level selection: the set of distinct assets used
    ts = {e["asset"] for e in T if e.get("asset")}
    ps = {e["asset"] for e in P if e.get("asset")}
    tp = len(ts & ps)
    prec = tp / len(ps) if ps else 0.0
    rec = tp / len(ts) if ts else 0.0
    out["shot_precision"], out["shot_recall"] = prec, rec
    out["shot_f1"] = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    # placement-level F1 at IoU thresholds (greedy one-to-one)
    for thr in (0.5, 0.9, 1.0):
        m = greedy_match(T, P, thr - 1e-9)
        p_ = len(m) / len(P) if P else 0.0
        r_ = len(m) / len(T) if T else 0.0
        out["f1@%.1f" % thr] = 2 * p_ * r_ / (p_ + r_) if p_ + r_ else 0.0
    m = greedy_match(T, P, 0.5 - 1e-9)
    ins = [abs(P[j]["f0"] - T[i]["f0"]) for i, j, _ in m]
    outs = [abs(P[j]["f1"] - T[i]["f1"]) for i, j, _ in m]
    out["matched@0.5"] = len(m)
    out["in_err_mean_f"] = float(np.mean(ins)) if ins else None
    out["out_err_mean_f"] = float(np.mean(outs)) if outs else None
    out["in_err_max_f"] = int(max(ins)) if ins else None
    out["out_err_max_f"] = int(max(outs)) if outs else None
    out["boundaries_within_1f"] = (sum(1 for x in ins + outs if x <= 1) / len(ins + outs)
                                   if ins else 0.0)
    out["mean_iou"] = float(np.mean([v for _, _, v in m])) if m else 0.0
    # primary-track order (base videos in time order)
    t_order = [e["asset"] for e in sorted(truth["events"], key=lambda e: e["f0"])
               if e["kind"] == "video" and e["z"] == 0]
    # REAL may place the base on a lane over a gap: take video events in time
    # order, lowest z first, as the primary sequence
    p_order = []
    for e in sorted(edl["events"], key=lambda e: (e["f0"], e["z"])):
        if e["kind"] == "video" and (not p_order or p_order[-1] != e["asset"]):
            p_order.append(e["asset"])
    out["order_exact"] = t_order == p_order
    out["kendall_tau"] = kendall_tau(t_order, p_order)
    # per-frame agreement of the topmost visual and its source frame
    tt, pp = visible(truth["events"], truth["total_f"]), visible(edl["events"], truth["total_f"])
    n = truth["total_f"]
    same_asset = sum(1 for a, b in zip(tt, pp) if (a and b and a[0] == b[0]) or (a is None and b is None))
    same_frame = sum(1 for a, b in zip(tt, pp) if a == b)
    out["frame_asset_acc"] = same_asset / n
    out["frame_exact_acc"] = same_frame / n
    out["black_frames_truth"] = sum(1 for a in tt if a is None)
    out["black_frames_pred"] = sum(1 for b in pp if b is None)
    # duration / coverage (EditDuet)
    d, dh = truth["total_f"], edl["total_f"]
    out["total_f_truth"], out["total_f_pred"] = d, dh
    out["time_coverage"] = min(d, dh) / max(d, dh) if max(d, dh) else 0.0
    return out


# ------------------------------------------------------------------ pixel

def frames_of(path, scale_w=None, gray=False):
    """Yield frames as uint8 arrays via ffmpeg rawvideo."""
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
                           capture_output=True, text=True).stdout.strip().split(",")
    w, h = int(probe[0]), int(probe[1])
    if scale_w:
        h = int(round(h * scale_w / w)) // 2 * 2
        w = scale_w
    fmt = "gray" if gray else "rgb24"
    ch = 1 if gray else 3
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", fmt]
    if scale_w:
        cmd += ["-vf", "scale=%d:%d" % (w, h)]
    cmd += ["-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h * ch
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        a = np.frombuffer(buf, np.uint8)
        yield a.reshape((h, w)) if gray else a.reshape((h, w, 3))
    p.wait()


def pixel(truth_mp4, real_mp4, use_lpips=False, every=1, width=270):
    from skimage.metrics import structural_similarity, peak_signal_noise_ratio
    A = list(frames_of(truth_mp4, width))
    B = list(frames_of(real_mp4, width))
    n = min(len(A), len(B))
    ssim, psnr, lp = [], [], []
    model = None
    if use_lpips:
        import torch
        import lpips as lpips_mod
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        model = lpips_mod.LPIPS(net="alex", verbose=False).to(dev)
    for i in range(0, n, every):
        a, b = A[i], B[i]
        ssim.append(structural_similarity(a, b, channel_axis=2, data_range=255))
        if np.array_equal(a, b):
            psnr.append(100.0)
        else:
            psnr.append(min(100.0, peak_signal_noise_ratio(a, b, data_range=255)))
        if model is not None:
            import torch
            ta = torch.from_numpy(a.copy()).permute(2, 0, 1).float().div(127.5).sub(1).unsqueeze(0).to(dev)
            tb = torch.from_numpy(b.copy()).permute(2, 0, 1).float().div(127.5).sub(1).unsqueeze(0).to(dev)
            with torch.no_grad():
                lp.append(float(model(ta, tb)))
    ssim = np.array(ssim)
    out = {"frames_compared": len(ssim), "len_truth": len(A), "len_pred": len(B),
           "ssim_mean": float(ssim.mean()), "ssim_min": float(ssim.min()),
           "ssim_match_rate@0.95": float((ssim > 0.95).mean()),
           "psnr_mean": float(np.mean(psnr)), "psnr_median": float(np.median(psnr))}
    if lp:
        out["lpips_mean"] = float(np.mean(lp))
        out["lpips_max"] = float(np.max(lp))
    return out


# ---------------------------------------------------------------- decoded

def video_size(path):
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
                           capture_output=True, text=True).stdout.strip().split(",")
    return int(probe[0]), int(probe[1])


def strip_rows(path, rows, width):
    """Stream only the given pixel rows of every frame (ffmpeg crop), so
    decoding a 40 s timeline moves kilobytes, not gigabytes."""
    outs = []
    for y in rows:
        # chroma subsampling needs an even crop height: take 2 rows, keep 1
        cmd = ["ffmpeg", "-v", "error", "-i", path, "-vf",
               "crop=%d:2:0:%d,format=gray" % (width, y // 2 * 2),
               "-f", "rawvideo", "-pix_fmt", "gray", "-"]
        raw = subprocess.run(cmd, capture_output=True).stdout
        a = np.frombuffer(raw, np.uint8).reshape((-1, 2, width))[:, 0, :]
        outs.append(a)
    return outs


def decode_video(path):
    """Works at any render scale: strip rows are located proportionally."""
    import synth
    w, h = video_size(path)
    s = w / synth.W
    ys = (int((synth.STRIP_Y + synth.STRIP_H // 2) * s),
          int(((synth.H - synth.IMG) // 2 + synth.STRIP_Y + synth.STRIP_H // 2) * s))
    top_rows, mid_rows = strip_rows(path, ys, w)
    n = min(len(top_rows), len(mid_rows))
    out = []
    for i in range(n):
        top = synth.decode_strip(top_rows[i][None, :], 0)
        mid = synth.decode_strip(mid_rows[i][None, :], 0)
        out.append((top, mid))
    return out


def decoded(truth_mp4, real_mp4):
    A, B = decode_video(truth_mp4), decode_video(real_mp4)
    n = min(len(A), len(B))
    base_same = sum(1 for i in range(n) if (A[i][0] or (None,))[0] == (B[i][0] or (None,))[0])
    exact = sum(1 for i in range(n) if A[i] == B[i])
    overlay_same = sum(1 for i in range(n) if (A[i][1] or (None,))[0] == (B[i][1] or (None,))[0])
    return {"frames": n, "decoded_base_acc": base_same / n,
            "decoded_overlay_acc": overlay_same / n,
            "decoded_exact_acc": exact / n,
            "undecodable_truth": sum(1 for a in A if a[0] is None),
            "undecodable_pred": sum(1 for b in B if b[0] is None)}


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "structural":
        print(json.dumps(structural(json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))), indent=1))
    elif cmd == "pixel":
        ev = int(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 1
        print(json.dumps(pixel(sys.argv[2], sys.argv[3], "--lpips" in sys.argv, ev), indent=1))
    elif cmd == "decoded":
        print(json.dumps(decoded(sys.argv[2], sys.argv[3]), indent=1))
