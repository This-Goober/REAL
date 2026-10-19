#!/usr/bin/env python3
"""project.py — generate one synthetic benchmark project and its ground truth.

A project is what a creator would hand the pipeline: a NOTEBOOK.md (the
script, with mock components), a human-labelled asset-catalog.json (we play
the human: every placeholder is labelled with a tag and a description), an
optional revisions.txt (creator corrections in the tracks-page grammar), and
a measured.json word alignment standing in for a recorded narration.

Alongside it we write truth.json — the reference edit decision list (EDL) —
computed HERE from the spec and the documented placement semantics
(bench/README.md §semantics), with no REAL code imported. The pipeline under
test must reproduce it.

    python3 project.py OUT_DIR --pool POOL_DIR --seed 7 [--beats 6]

Stdlib + numpy only.
"""
import argparse
import json
import os
import random
import re
import shutil

VOCAB = """anchor bridge candle delta ember fossil garden harbor island jigsaw
kettle lantern meadow needle orbit pebble quartz ribbon saddle timber under
velvet walnut yellow zephyr amber basket cobalt dune engine falcon glacier
hammer ivory jungle kernel ladder marble nickel oyster parcel quiver rocket
signal tunnel violet willow basalt cinder dagger ferry gravel hollow iron
jasper kiosk lumber mantle nutmeg pepper ripple sulfur thistle vapor wicket
cedar flint grain hazel lotus maple olive pearl reed sage tulip yarrow""".split()
VOCAB = sorted(set(VOCAB))

CLIP_DESC = ["a wide shot of the %s", "a close-up on the %s", "a slow pan across the %s",
             "the %s from above", "a handheld pass by the %s"]
IMG_DESC = ["a diagram of the %s", "a still of the %s", "a sketch of the %s",
            "a chart about the %s"]
STYLES = ("caption", "title")

CUT_INTO_WORD = 0.4      # a cut lands 40% into its anchor word (documented)
FPS = 30


# --------------------------------------------------------------- narration

def syllables(w):
    return max(1, len(re.findall(r"[aeiouy]+", w)))


def narration(rng, n_words):
    words = rng.sample(VOCAB, n_words)
    words[0] = words[0].capitalize()
    return words


def word_times(rng, beats, rate):
    """An independent speech-timing model (NOT the pipeline's estimator): a
    per-word duration from syllable count scaled by the speaker's rate, short
    inter-word gaps, a sentence pause, and a longer pause between beats."""
    t, out, i = 0.0, [], 0
    for k, b in enumerate(beats):
        if k:
            t += rng.uniform(0.55, 0.95)          # breath between beats
        for j, w in enumerate(b["words"]):
            d = (0.11 + 0.085 * syllables(w)) * rate * rng.uniform(0.85, 1.15)
            out.append({"i": i, "w": w, "start": round(t, 3), "end": round(t + d, 3)})
            t += d + rng.uniform(0.02, 0.06)
            i += 1
        t += 0.25                                  # sentence pause
    return out


# ------------------------------------------------------------------ spec

def make_spec(rng, pool_clips, pool_images, n_beats, difficulty):
    clips = rng.sample(range(1, pool_clips + 1), n_beats)
    images = list(range(1, pool_images + 1))
    rng.shuffle(images)
    rate = rng.uniform(0.85, 1.2)
    beats, imgs_used = [], []
    for k in range(n_beats):
        n_words = rng.randint(9, 16)
        words = narration(rng, n_words)
        ovl = []
        kinds = []
        if difficulty == "easy":
            kinds = rng.choice([[], ["text"], ["image"]])
        else:
            kinds = rng.choice([[], ["text"], ["image"], ["image", "text"],
                                ["text", "image"]])
        for kind in kinds:
            if kind == "image":
                img = images.pop()
                imgs_used.append(img)
                ovl.append({"kind": "image", "asset": "img%02d" % img,
                            "dur": round(rng.uniform(1.4, 2.6), 1)})
            else:
                n = rng.randint(2, 5)
                content = " ".join(rng.sample(VOCAB, n))
                ovl.append({"kind": "text", "content": content,
                            "style": rng.choice(STYLES),
                            "dur": round(rng.uniform(1.2, 2.2), 1)})
        beats.append({"id": "B%d" % (k + 1), "name": "beat %d" % (k + 1),
                      "words": words, "base": "clip%02d" % clips[k],
                      "overlays": ovl})
    spec = {"fps": FPS, "w": 1080, "h": 1920, "rate": round(rate, 3),
            "beats": beats, "clips": clips, "images": imgs_used}
    spec["word_times"] = word_times(rng, beats, rate)
    # anchors: the documented distribution rule, then creator overrides on
    # roughly half the overlays (exercises the revision path)
    i0 = 0
    for b in beats:
        L = len(b["words"])
        b["w0"], b["w1"] = i0, i0 + L - 1
        groups = 1 + len(b["overlays"])           # base + each overlay
        for gi, o in enumerate(b["overlays"], start=1):
            o["anchor_rule"] = b["w0"] + int(gi * L / groups)
            o["anchor"] = o["anchor_rule"]
            o["creator"] = False
        i0 += L
    wt = {w["i"]: w for w in spec["word_times"]}
    for b in beats:
        end = wt[b["w1"]]["end"]
        prev_cut = None
        for o in b["overlays"]:
            if rng.random() < 0.5:
                # a creator moves it to a word in the front 60% of the line
                lo, hi = b["w0"] + 1, b["w0"] + max(1, int(0.6 * len(b["words"])))
                o["anchor"] = rng.randint(lo, hi)
                o["creator"] = True
            w = wt[o["anchor"]]
            cut = w["start"] + CUT_INTO_WORD * (w["end"] - w["start"])
            # keep cues >= 0.5s apart (the snap window is 0.3s) and keep the
            # overlay inside the line under any plausible clock
            if prev_cut is not None and abs(cut - prev_cut) < 0.5:
                o["anchor"] = min(b["w1"] - 1, o["anchor"] + 2)
                w = wt[o["anchor"]]
                cut = w["start"] + CUT_INTO_WORD * (w["end"] - w["start"])
            room = end - cut
            # REAL's documented hold rule: a timed overlay that would outrun
            # the line at its DEFAULT anchor becomes a hold that plays after
            # the words stop. Tier 1 does not model holds, so every overlay
            # must also fit at its default anchor (start of the anchor word,
            # 0.10 s tolerance), or the project leaves its own semantics.
            room_rule = end + 0.10 - wt[o["anchor_rule"]]["start"]
            o["dur"] = round(min(o["dur"], max(0.8, 0.5 * room)), 1)
            if o["dur"] > room_rule - 0.05:
                o["dur"] = max(0.4, int((room_rule - 0.05) * 10) / 10.0)
            prev_cut = cut
            o["creator"] = o["creator"] or (o["anchor"] != o["anchor_rule"])
    return spec


# ------------------------------------------------------------ ground truth

def snap(t):
    return int(round(t * FPS))


def truth_edl(spec):
    """The reference EDL. Semantics (see README):
      beat k occupies [start(w0), end(w1)]; between beats the screen is black;
      the base clip of a beat runs the whole beat from source frame 0;
      an overlay starts 40% into its anchor word, lasts its explicit duration,
      and never outlives its beat."""
    wt = {w["i"]: w for w in spec["word_times"]}
    ev, cursor = [], 0
    for b in spec["beats"]:
        f0, f1 = snap(wt[b["w0"]]["start"]), snap(wt[b["w1"]]["end"])
        if f0 > cursor:
            ev.append({"kind": "gap", "asset": None, "f0": cursor, "f1": f0, "z": 0})
        ev.append({"kind": "video", "asset": b["base"], "f0": f0, "f1": f1,
                   "src_in": 0, "z": 0, "beat": b["id"]})
        for zi, o in enumerate(b["overlays"], start=1):
            w = wt[o["anchor"]]
            cut = w["start"] + CUT_INTO_WORD * (w["end"] - w["start"])
            o0, o1 = snap(cut), min(f1, snap(cut + o["dur"]))
            e = {"kind": o["kind"], "f0": o0, "f1": o1, "z": zi, "beat": b["id"],
                 "anchor": o["anchor"]}
            if o["kind"] == "image":
                e["asset"] = o["asset"]
            else:
                e["asset"] = None
                e["text"] = o["content"]
                e["style"] = o["style"]
            ev.append(e)
        cursor = f1
    return {"fps": FPS, "w": spec["w"], "h": spec["h"], "total_f": cursor,
            "events": ev}


# ---------------------------------------------------------- creator files

def write_notebook(spec, path, tags=True):
    lines = ["---", "reel: Benchmark reel", "aspect: 9:16", "---", ""]
    for b in spec["beats"]:
        lines.append("## %s" % b["name"])
        lines.append("")
        lines.append("<%s.>" % " ".join(b["words"]))
        n = int(b["base"][4:])
        lines.append("<video clip of %s #%s>" % (
            CLIP_DESC[n % len(CLIP_DESC)] % VOCAB[(n * 7) % len(VOCAB)]
            if not tags else "placeholder footage %d" % n, b["base"])
            if tags else "<video clip of %s>" % (
            CLIP_DESC[n % len(CLIP_DESC)] % VOCAB[(n * 7) % len(VOCAB)]))
        for o in b["overlays"]:
            if o["kind"] == "image":
                m = int(o["asset"][3:])
                desc = IMG_DESC[m % len(IMG_DESC)] % VOCAB[(m * 11) % len(VOCAB)]
                lines.append("<show image of %s ~%.1fs%s>"
                             % (desc, o["dur"], " #" + o["asset"] if tags else ""))
            else:
                lines.append("<caption: %s ~%.1fs>" % (o["content"], o["dur"]))
        lines.append("")
    open(path, "w").write("\n".join(lines))


def write_catalog(spec, root, path):
    assets = []
    for n in spec["clips"]:
        aid = "clip%02d" % n
        assets.append({"id": aid, "f": "Videos/%s.mp4" % aid, "k": "video",
                       "dur": 12.0, "w": 1080, "h": 1920, "fps": 30, "rotation": 0,
                       "exists": True,
                       "role": "placeholder clip %d" % n,
                       "shows": "a labelled placeholder: %s"
                                % (CLIP_DESC[n % len(CLIP_DESC)] % VOCAB[(n * 7) % len(VOCAB)]),
                       "use": "the base shot of its beat", "beat": "any",
                       "binds_to": "a `<video clip of %s>` type component"
                                   % (CLIP_DESC[n % len(CLIP_DESC)] % VOCAB[(n * 7) % len(VOCAB)]),
                       "tags": [aid]})
    for m in spec["images"]:
        aid = "img%02d" % m
        assets.append({"id": aid, "f": "Images/%s.png" % aid, "k": "image",
                       "dur": None, "w": 1080, "h": 1080, "fps": None, "rotation": 0,
                       "exists": True,
                       "role": "placeholder image %d" % m,
                       "shows": "a labelled placeholder: %s"
                                % (IMG_DESC[m % len(IMG_DESC)] % VOCAB[(m * 11) % len(VOCAB)]),
                       "use": "an overlay", "beat": "any",
                       "binds_to": "a `<show image of %s>` type component"
                                   % (IMG_DESC[m % len(IMG_DESC)] % VOCAB[(m * 11) % len(VOCAB)]),
                       "tags": [aid]})
    cat = {"project": "Benchmark reel", "root": root, "generated": "bench",
           "script_beats": [], "assets": assets}
    json.dump(cat, open(path, "w"), indent=1)


def write_revisions(spec, path):
    """Creator corrections in the tracks-page grammar. Layer slots: the base
    video is L1, overlays follow in written order (L2, L3)."""
    lines = []
    for b in spec["beats"]:
        for zi, o in enumerate(b["overlays"], start=2):
            if o["creator"]:
                lines.append("%s: L%d anchor = %s" % (b["id"], zi, b["words"][o["anchor"] - b["w0"]]))
            if o["kind"] == "text" and o["style"] != "caption":
                lines.append("%s: L%d style = %s" % (b["id"], zi, o["style"]))
    open(path, "w").write("\n".join(lines) + ("\n" if lines else ""))
    return len(lines)


def build_project(out, pool, seed, n_beats, difficulty, tags=True):
    rng = random.Random(seed)
    pool_clips = len([f for f in os.listdir(os.path.join(pool, "Videos")) if f.endswith(".mp4")])
    pool_images = len([f for f in os.listdir(os.path.join(pool, "Images")) if f.endswith(".png")])
    spec = make_spec(rng, pool_clips, pool_images, n_beats, difficulty)
    spec["seed"] = seed
    media = os.path.join(out, "media")
    for sub in ("Videos", "Images"):
        os.makedirs(os.path.join(media, sub), exist_ok=True)
    for n in spec["clips"]:
        src = os.path.join(pool, "Videos", "clip%02d.mp4" % n)
        dst = os.path.join(media, "Videos", "clip%02d.mp4" % n)
        if not os.path.exists(dst):
            os.symlink(os.path.abspath(src), dst)
    for m in spec["images"]:
        src = os.path.join(pool, "Images", "img%02d.png" % m)
        dst = os.path.join(media, "Images", "img%02d.png" % m)
        if not os.path.exists(dst):
            os.symlink(os.path.abspath(src), dst)
    json.dump(spec, open(os.path.join(out, "spec.json"), "w"), indent=1)
    json.dump(truth_edl(spec), open(os.path.join(out, "truth.json"), "w"), indent=1)
    write_notebook(spec, os.path.join(out, "NOTEBOOK.md"), tags=tags)
    write_catalog(spec, os.path.abspath(media), os.path.join(out, "asset-catalog.json"))
    json.dump({"words": spec["word_times"]}, open(os.path.join(out, "measured.json"), "w"), indent=1)
    n_rev = write_revisions(spec, os.path.join(out, "revisions.txt"))
    return spec, n_rev


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--beats", type=int, default=6)
    ap.add_argument("--difficulty", default="normal", choices=["easy", "normal"])
    ap.add_argument("--no-tags", action="store_true",
                    help="omit #tags from the notebook so binding relies on descriptions")
    a = ap.parse_args()
    spec, n_rev = build_project(a.out, a.pool, a.seed, a.beats, a.difficulty, tags=not a.no_tags)
    t = json.load(open(os.path.join(a.out, "truth.json")))
    print("project %s: %d beats, %d events, %d frames (%.2fs), %d creator revisions"
          % (a.out, len(spec["beats"]), len(t["events"]), t["total_f"],
             t["total_f"] / FPS, n_rev))
