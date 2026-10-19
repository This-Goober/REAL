#!/usr/bin/env python3
"""regression.py — end-to-end regression suite for the REAL pipeline.

Run from the folder containing the four real-* skill directories:

    python3 real-storyboarding/tests/regression.py

Exercises, with real script invocations on synthetic data:
 1  stage directions (components) not counted as narration      [brainstorm]
 2  estimated vs measured timing                                 [storyboarding]
 3  textual anchors surviving timing replacement                 [storyboarding]
 4  creator-defined anchor via revision line (word text)         [storyboarding]
 5  partial inspection of a clip via --window                    [catalogue]
 6  user-requested windows recorded structurally                 [catalogue]
 7  temporal evidence in the catalogue JSON                      [catalogue]
 8  ambiguous near-duplicates flagged for creator review         [catalogue]
 9  creator-selected placement surviving a rebuild (--preserve)  [storyboarding]
10  every storyboard layer surviving the handoff (parity)        [compile]
11  audio placement surviving the handoff                        [compile]
12  explicit title vs caption vs subtitle classification         [both]
13  canonical asset ids surviving renames                        [catalogue]
14  unresolved technical properties surfaced                     [storyboarding]
15  storyboarding producing the authoritative finalized reel     [contract]
16  compile consuming it without editorial decisions             [compile]
17  visual descriptions ending in "." are not counted as speech  [storyboarding]
18  the shipped example rebuilds to the shipped example reel      [docs]
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SB = os.path.join(ROOT, "real-storyboarding", "scripts")
CAT = os.path.join(ROOT, "real-create-catalogue", "scripts")
BR = os.path.join(ROOT, "real-brainstorm", "scripts")
CO = os.path.join(ROOT, "real-compile", "scripts")
PASS = []


def run(script, *args, cwd=None, ok=True):
    r = subprocess.run([sys.executable, script, *args], capture_output=True,
                       text=True, cwd=cwd)
    if ok and r.returncode != 0:
        raise SystemExit("FAILED %s %s\n%s\n%s" % (script, args, r.stdout, r.stderr))
    return r


def check(n, label, cond, detail=""):
    if not cond:
        raise SystemExit("CHECK %d FAILED — %s %s" % (n, label, detail))
    PASS.append(n)
    print("  ok %2d  %s" % (n, label))


W = tempfile.mkdtemp(prefix="real-regression-")
os.chdir(W)

# ───────────────────────── synthetic notebook ─────────────────────────
# In the notebook format, everything SPOKEN is an explicit <...> narration
# component and plain prose is production notes — stage directions are
# structurally outside the spoken count by design. The prose lines below are
# exactly the kind of thing that used to inflate the old pipeline's clock.
NOTEBOOK = """---
reel: Regression Reel
aspect: 9:16
target: 20s
---

## hook

Fast cuts here. Swap back to the dissonant overtone pic. text: practice drone.

<Have you ever heard two notes that seem to fight each other and beat.>
<show image of two sine waves drifting out of phase>
<caption: they interfere>

## payoff

Slow this down, one idea per visual — none of this sentence is spoken either.

<That fighting sound has a name and you can hear it right now.>
<video clip of the dissonance demo playing on a violin> !
"""
open("NOTEBOOK.md", "w").write(NOTEBOOK)

# 1 — components are not narration
r = run(os.path.join(BR, "ballpark.py"), "NOTEBOOK.md", "--json")
bp = json.loads(r.stdout[r.stdout.index("{"):])
t = bp["totals"]
check(1, "only bracketed narration counts as spoken; prose notes & visual "
         "components excluded", t["words"] == 27 and t["counts"]["narration"] == 2,
      "got %r words / %r narration components (want 27 / 2)"
      % (t["words"], t["counts"]["narration"]))

# ───────────────────────── parse + clock ─────────────────────────
run(os.path.join(SB, "notebook.py"), "parse", "NOTEBOOK.md", "-o", "notebook.json")
run(os.path.join(SB, "clock.py"), "time", "notebook.json", "-o", "clock.json")
clock = json.load(open("clock.json"))
check(2, "clock starts estimated and says so",
      clock.get("mode") == "estimated" and "estimat" in (clock.get("note") or "").lower())

# ───────────────────────── synthetic catalogue folder ─────────────────────────
os.makedirs("media/Videos", exist_ok=True)
os.makedirs("media/Images", exist_ok=True)
# a real 6s test video
run_ff = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                         "-i", "testsrc=duration=6:size=320x568:rate=30",
                         "media/Videos/demo-clip.mp4"], capture_output=True)
assert run_ff.returncode == 0, run_ff.stderr
# two near-identical images + one different (shot grouping)
from PIL import Image, ImageDraw
def img(path, base, jitter):
    im = Image.new("RGB", (320, 568), base)
    d = ImageDraw.Draw(im)
    d.rectangle([40, 40, 280, 300], fill=(200, 200, 210))
    d.ellipse([100 + jitter, 350, 220 + jitter, 470], fill=(30, 30, 40))
    im.save(path)
img("media/Images/take-a.png", (18, 22, 30), 0)
img("media/Images/take-b.png", (18, 22, 30), 4)          # same setup, tiny shift
Image.effect_noise((320, 568), 64).convert("RGB").save("media/Images/other.png")

# 5/6 — partial inspection with a creator window
r = run(os.path.join(CAT, "scan.py"), "media", "work", "--budget", "500",
        "--window", "demo-clip.mp4=0:02-0:04")
inv = json.load(open("work/inventory.json"))
vid = inv["Videos/demo-clip.mp4"]
check(5, "windowed clip marked partial, never presented as fully analyzed",
      vid["inspection"]["level"] == "partial")
w0 = vid["inspection"]["windows"][0]
check(6, "creator window recorded structurally (t0/t1/by)",
      abs(w0["t0"] - 2) < 0.1 and abs(w0["t1"] - 4) < 0.1 and w0["by"] == "creator")

# 7 — temporal evidence
check(7, "temporal evidence in catalogue JSON (duration, sampled times, method)",
      vid["temporal"]["duration"] > 5.5 and len(vid["temporal"]["sampled_at"]) >= 8
      and vid["temporal"]["method"] == "seek-sample"
      and all(2 <= t <= 4 for t in vid["temporal"]["sampled_at"]))

# 8 — shot grouping: confident same-setup pair grouped; uncertain band asks
ia, ib = inv["Images/take-a.png"], inv["Images/take-b.png"]
check(8, "near-identical takes share a shot_group; uncertain pairs go to review",
      ia.get("shot_group") and ia.get("shot_group") == ib.get("shot_group")
      and os.path.exists("work/shot-groups.json")
      and inv["Images/other.png"].get("shot_group_verdict") != "same-setup")
# unit-check the uncertain band directly
sys.path.insert(0, CAT)
import scan as _scan
g, v, review, _ = _scan.shot_groups({"x": [0], "y": [(1 << 15) - 1]})  # d=15
check(8, "distance in the 11-20 band is 'uncertain', never asserted",
      review and review[0]["distance"] == 15 and v.get("x") == "uncertain")

# 13 — canonical ids survive a rename
ids1 = json.load(open("work/asset-ids.json"))
old_id = ids1["Images/take-a.png"]
shutil.move("media/Images/take-a.png", "media/Images/practice-pov-takeA.png")
json.dump({"Images/take-a.png": "Images/practice-pov-takeA.png"},
          open("work/rename-map.json", "w"))
run(os.path.join(CAT, "scan.py"), "media", "work", "--budget", "500", "--force",
    "--window", "demo-clip.mp4=0:02-0:04")
ids2 = json.load(open("work/asset-ids.json"))
check(13, "asset_id survives a rename via rename-map.json",
      ids2["Images/practice-pov-takeA.png"] == old_id)

# ───────────────────────── catalogue → bind → build ─────────────────────────
skel = json.load(open("work/skeleton.json"))
by_f = {a["f"]: a for a in skel["assets"]}
by_f["Videos/demo-clip.mp4"].update(
    role="★ dissonance demo", shows="6s test pattern",
    use="the demo the reel proves", beat="payoff",
    binds_to="a `<video clip of the dissonance demo>` type component",
    tags=["demo"])
by_f["Images/practice-pov-takeA.png"].update(
    role="sine waves", shows="two waves drifting",
    binds_to="a `<show image of two sine waves>` type component", tags=["waves"])
# 14 — deliberately leave the video's w/h unresolved in the catalogue rows
cat = {"project": "Regression", "root": os.path.abspath("media"),
       "generated": "2026-08-29", "script_beats": skel["script_beats"],
       "assets": [dict(a, dur=(6.0 if a["k"] == "video" else None))
                  for a in skel["assets"]]}
json.dump(cat, open("asset-catalog.json", "w"), indent=1)

run(os.path.join(SB, "bind.py"), "bind", "notebook.json", "asset-catalog.json",
    "-o", "bindings.json")
run(os.path.join(SB, "build.py"), "build", "notebook.json", "clock.json",
    "bindings.json", "-o", "reel.json", "--assets-root", os.path.abspath("media"),
    "--stubs-dir", "stubs")
reel = json.load(open("reel.json"))

# 15 — the finalized handoff is reel.json with the full editorial statement
check(15, "storyboarding emits the authoritative reel.json (beats+audio+open)",
      reel["beats"] and "open" in reel and "clock" in reel)

# 14 — unresolved specs surfaced in editorial language
un = reel["open"].get("unresolved_specs") or []
check(14, "unresolved technical properties surfaced before handoff",
      any("frame size" in " ".join(u["missing"]) for u in un))

# 3/4 — textual anchors + creator revision by word text
lay = next(l for b in reel["beats"] for l in b["layers"] if l.get("anchor_text"))
check(3, "layers carry anchor_text (the word is the identity)",
      isinstance(lay["anchor_text"], str) and lay["anchor_text"])
text_layer = next(l for b in reel["beats"] for l in b["layers"]
                  if l["kind"] == "text")
bid = next(b["id"] for b in reel["beats"] for l in b["layers"]
           if l["id"] == text_layer["id"])
slot = text_layer["id"].split(".")[-1]
open("revisions.txt", "w").write(
    "%s: %s anchor = fight\n%s: %s style = subtitle\n" % (bid, slot, bid, slot))
run(os.path.join(SB, "revise.py"), "apply", "reel.json", "revisions.txt",
    "-o", "reel.json", "--clock", "clock.json")
reel = json.load(open("reel.json"))
tl = next(l for b in reel["beats"] for l in b["layers"]
          if l["id"] == text_layer["id"])
check(4, "creator anchor-by-word applied; anchor_text follows",
      tl["anchor_text"].lower().startswith("fight")
      and tl["chosen_by"] == "creator")
check(12, "creator text-type classification (subtitle) recorded",
      tl["style"] == "subtitle" and tl["style_by"] == "creator")

# 2/3 — measured swap: times move, anchors do not
words = clock["words"]
measured = {"words": [{"i": w["i"], "start": round(w["start"] * 1.15, 3),
                       "end": round(w["end"] * 1.15, 3)} for w in words]}
json.dump(measured, open("measured.json", "w"))
run(os.path.join(SB, "clock.py"), "swap", "clock.json", "measured.json",
    "-o", "clock.json")
old_t0, old_anchor = tl["t0"], (tl["anchor_word"], tl["anchor_text"])
run(os.path.join(SB, "build.py"), "retime", "reel.json", "clock.json",
    "-o", "reel.json")
reel = json.load(open("reel.json"))
tl = next(l for b in reel["beats"] for l in b["layers"]
          if l["id"] == text_layer["id"])
check(2, "measured clock swaps in and mode says measured",
      reel["clock"]["mode"] == "measured")
check(3, "timing replacement moved t0 but not the textual anchor",
      abs(tl["t0"] - old_t0) > 0.05
      and (tl["anchor_word"], tl["anchor_text"]) == old_anchor)

# 9 — creator placement survives an automated rebuild
run(os.path.join(SB, "build.py"), "build", "notebook.json", "clock.json",
    "bindings.json", "-o", "reel2.json", "--assets-root", os.path.abspath("media"),
    "--stubs-dir", "stubs", "--preserve", "reel.json")
reel2 = json.load(open("reel2.json"))
tl2 = next(l for b in reel2["beats"] for l in b["layers"]
           if l["id"] == text_layer["id"])
check(9, "creator-selected placement survives the rebuild via --preserve",
      tl2["chosen_by"] == "creator" and tl2["style"] == "subtitle"
      and tl2["anchor_text"] == tl["anchor_text"])

# ───────────────────────── compile: parity + no editorial decisions ─────────────────────────
# fill the unresolved specs the way the question says to (probe facts), so the
# build has what it refuses to guess
for a in reel2["assets"]:
    if a["kind"] == "video":
        a["w"], a["h"], a["dur_s"] = 320, 568, a.get("dur_s") or 6.0
    if a["kind"] == "image" and not (a.get("w") and a.get("h")):
        a["w"], a["h"] = 320, 568
json.dump(reel2, open("reel2.json", "w"), indent=1)
r = run(os.path.join(CO, "adapt.py"), "reel2.json", "-o", "story.json",
        "--local-root", os.path.abspath("media"))
story = json.load(open("story.json"))
par = story["_parity"]
check(10, "parity: every storyboard layer represented, nothing dropped",
      par["layers_in"] == par["visual_elements_out"] and not par["dropped"],
      json.dumps(par))
check(11, "audio placement survives the handoff (lanes -> connected/unvoiced)",
      par["audio_lanes_in"] >= 1
      and (par["connected_out"] >= 1 or story.get("unvoiced")))
subs = [b for b in story["beats"]
        for o in (b.get("overlays") or []) if o.get("font_size") == 58]
check(12, "subtitle maps to its own distinct FCP styling in story.json",
      len(subs) == 1)
check(16, "compile made no editorial decisions (generated marker + clock passthrough)",
      story["_generated_by"].startswith("adapt.py")
      and story["_clock"]["mode"] == "measured")

# negative: unclassified text is refused, not defaulted
bad = json.load(open("reel2.json"))
for b in bad["beats"]:
    for l in b["layers"]:
        if l["kind"] == "text":
            l.pop("style", None)
json.dump(bad, open("bad.json", "w"))
r = run(os.path.join(CO, "adapt.py"), "bad.json", "-o", "badstory.json",
        "--local-root", os.path.abspath("media"), ok=False)
check(12, "REFUSES unclassified text (no silent caption default)",
      r.returncode != 0 and "no style" in (r.stdout + r.stderr))

# 17 — a visual description ending in a full stop is still a visual, and a
# spoken sentence that mentions a media word is still narration
sys.path.insert(0, SB)
import notebook as _nb
check(17, "directive openings beat the full-sentence rule; spoken sentences stay spoken",
      _nb.classify("video clip of One line. Many connections.") == "video"
      and _nb.classify("show image of caption one line, large and centred.") == "image"
      and _nb.classify("audio of rain on a tin roof, close and loud.") == "audio"
      and _nb.classify("That sound is called a drone, and you hear it.") == "narration"
      and _nb.classify("Every transformer is built on one line of math.") == "narration")

# 18 — the shipped example still rebuilds to the shipped example reel. The
# example files are documentation; if the scripts drift, the docs lie.
ex = os.path.join(W, "example")
os.makedirs(ex, exist_ok=True)
shutil.copy(os.path.join(ROOT, "real-brainstorm", "examples", "NOTEBOOK.example.md"),
            os.path.join(ex, "NOTEBOOK.md"))
run(os.path.join(SB, "notebook.py"), "parse", "NOTEBOOK.md", "-o", "nb.json", cwd=ex)
run(os.path.join(SB, "clock.py"), "time", "nb.json", "-o", "clock.json", cwd=ex)
shipped = json.load(open(os.path.join(ROOT, "real-storyboarding", "examples", "reel.example.json")))
ck = json.load(open(os.path.join(ex, "clock.json")))
check(18, "the example notebook still times to the shipped example reel (beats, runtime)",
      len(ck["beats"]) == len(shipped["beats"])
      and abs(ck["total_s"] - shipped["clock"]["total_s"]) < 0.01
      and all(abs(a["t0"] - b["t0"]) < 0.01 and abs(a["t1"] - b["t1"]) < 0.01
              for a, b in zip(ck["beats"], shipped["beats"])),
      "got %d beats / %.3fs, shipped %d / %.3fs"
      % (len(ck["beats"]), ck["total_s"], len(shipped["beats"]), shipped["clock"]["total_s"]))

# A1 — vendored code must remain identical; every repository notebook must
# use the same word identities at the timing and voice-export handoff.
from pathlib import Path
import clock as _clock
from real_core import words_of
check(19, "vendored real_core copies are byte-identical",
      len({Path(folder, "real_core.py").read_bytes() for folder in (SB, CO, CAT)}) == 1)
repo = Path(ROOT).parents[2]
if not (repo / ".git").exists():
    repo = Path(ROOT)  # the suite also works in an extracted standalone bundle
notebooks = []
for folder, dirs, files in os.walk(repo):
    dirs[:] = [d for d in dirs if d not in (".git", "work", "node_modules", ".venv", "__pycache__")]
    notebooks.extend(Path(folder, name) for name in files
                     if "NOTEBOOK" in name and name.endswith(".md"))
failures = []
for i, path in enumerate(sorted(notebooks)):
    plan = _clock.plan(_nb.parse(path.read_text()), _clock.load_rates())
    if not plan["words"]:
        continue
    fixture = Path(W, "tokens-%d.json" % i)
    exported = Path(W, "tokens-%d.txt" % i)
    fixture.write_text(json.dumps({
        "version": "1.0", "reel": {"title": "Token check", "width": 1080, "height": 1920, "fps": 30},
        "clock": {"mode": "estimated", "total_s": 0}, "assets": [], "open": {},
        "beats": [{**b, "t0": 0, "t1": 0, "layers": [], "audio": []} for b in plan["beats"]]}))
    result = run(os.path.join(CO, "voice.py"), "script", str(fixture),
                 "-o", str(exported), ok=False)
    if result.returncode or words_of(exported.read_text()) != [w["w"] for w in plan["words"]]:
        failures.append(str(path))
    elif exported.read_text().strip() != "\n".join(
            b["narration"].strip() for b in plan["beats"] if b.get("narration")):
        failures.append(str(path) + " (recording punctuation changed)")
check(20, "voice export matches clock tokens across %d repository notebooks" % len(notebooks),
      bool(notebooks) and not failures, ", ".join(failures))
check(21, "narration token identities handle punctuation without whitespace boundaries",
      words_of("Wait—don't cut.Now re-enter; 16:9, Q/K, it’s ready!")
      == ["Wait", "don't", "cut", "Now", "re-enter", "16:9", "Q/K", "it’s", "ready"])

# Defect 13 — moving a previously clipped caption must recover the requested
# duration. Repeated late/early moves must not progressively shorten it.
import build as _build
import revise as _revise
from types import SimpleNamespace
n13 = _nb.parse("## beat\n\n<Lantern ferry cobalt signal willow dune nickel yarrow pepper glacier basalt lotus quiver.>\n<caption: candle oyster ~1.6s>\n")
c13 = _clock.plan(n13, _clock.load_rates())
for w in c13["words"]:
    w["start"], w["end"] = w["i"] * 0.25, (w["i"] + 1) * 0.25
c13["mode"] = "measured"
_clock.derive(c13, _clock.load_rates())
# Pin the original cue late, exactly as the reported failure does.
p13 = next(p for p in c13["placements"] if p["type"] == "text")
p13["t0"], p13["t1"] = 2.5, 3.25
r13 = _build.assemble(n13, c13, {"assets": [], "bindings": {
                           p13["component"]: {"confidence": "high"}}},
                       SimpleNamespace(stubs_dir=None, fps=30,
                                       assets_root="", assets_root_local=""))
b13 = r13["beats"][0]
l13 = b13["layers"][0]
check(22, "build retains a caption's explicit duration after clipping",
      l13.get("dur_s") == 1.6 and l13["t1"] - l13["t0"] < 1.6)
for anchor in (2, 11, 2):
    l13["anchor_word"] = anchor
    _revise.reanchor(l13, b13, c13, [])
    expected = min(l13["t0"] + 1.6, b13["t1"])
    assert abs(l13["t1"] - expected) < 1e-8
check(23, "reanchoring restores requested duration while respecting beat bounds",
      abs(l13["t1"] - l13["t0"] - 1.6) < 1e-8)

# A2 — each handoff accepts real producer output and refuses a damaged
# nested field before its consumer can overwrite the previous result.
import copy
from real_core import validate_document, write_json, SchemaError
contracts = {
    "notebook": json.load(open("notebook.json")),
    "clock": json.load(open("clock.json")),
    "measured": json.load(open("measured.json")),
    "asset-catalog": json.load(open("asset-catalog.json")),
    "reel": json.load(open("reel2.json")),
    "story": json.load(open("story.json")),
}
broken = copy.deepcopy(contracts)
broken["notebook"]["cells"][0]["groups"][0]["components"][0]["type"] = "naration"
broken["clock"]["words"][0]["start"] = "yesterday"
for word in broken["measured"]["words"]:
    word["starts_at"] = word.pop("start")
broken["asset-catalog"]["assets"][0]["dur"] = -1
broken["reel"]["beats"][0]["layers"][0].pop("t1")
broken["story"]["beats"][0]["duration"] = -1
fields = {"notebook": ".type", "clock": ".start", "measured": "start",
          "asset-catalog": ".dur", "reel": ".t1", "story": ".duration"}
for n, (name, data) in enumerate(contracts.items(), 24):
    validate_document(data, name)
    bad_path = "contract-bad-" + name + ".json"
    output = "contract-protected-" + name
    Path(bad_path).write_text(json.dumps(broken[name]))
    sentinel = "previous successful output\n"
    Path(output).write_text(sentinel)
    commands = {
        "notebook": (os.path.join(SB, "clock.py"), "time", bad_path, "-o", output),
        "clock": (os.path.join(SB, "build.py"), "retime", "reel2.json", bad_path, "-o", output),
        "measured": (os.path.join(SB, "clock.py"), "swap", "clock.json", bad_path, "-o", output),
        "asset-catalog": (os.path.join(SB, "bind.py"), "bind", "notebook.json", bad_path, "-o", output),
        "reel": (os.path.join(CO, "adapt.py"), bad_path, "-o", output),
        "story": (os.path.join(CO, "compile.py"), "build", bad_path, output, "--no-probe"),
    }
    result = run(*commands[name], ok=False)
    message = result.stdout + result.stderr
    check(n, name + " schema accepts producer output and refuses its damaged handoff",
          result.returncode != 0 and "REFUSED" in message and fields[name] in message
          and "Traceback" not in message and Path(output).read_text() == sentinel,
          message)

# Documentation examples must satisfy the same contracts as generated files.
examples = list(Path(ROOT).glob("*/examples/*.json"))
for path in examples:
    validate_document(json.loads(path.read_text()), "reel" if "reel" in path.name else "asset-catalog")
check(30, "every shipped JSON example validates", len(examples) == 4)
schema_copies = {}
for path in Path(ROOT).glob("*/references/schemas/*.schema.json"):
    schema_copies.setdefault(path.name, []).append(path.read_bytes())
check(31, "all six schema definitions are vendored without drift",
      len(schema_copies) == 6 and all(len(set(copies)) == 1 for copies in schema_copies.values()))

# The writer must refuse BEFORE opening a destination, including when updating
# an existing handoff in place. Test every schema, not only a toy schema.
protected = Path("contract-write-protected.json")
for name, data in broken.items():
    protected.write_text(sentinel)
    try:
        write_json(protected, data, name)
    except SystemExit as error:
        assert "REFUSED" in str(error) and fields[name] in str(error)
    else:
        raise AssertionError("invalid " + name + " was written")
    assert protected.read_text() == sentinel
check(32, "invalid handoff writes preserve all previous outputs", True)

# Measured-word consumers must agree on both aliases and use index identity,
# even if the provider emits its word entries out of order.
original = contracts["measured"]
alias = {"words": [{"i": w["i"], "s": w["start"], "e": w["end"]}
                   for w in reversed(original["words"])]}
Path("measured-alias.json").write_text(json.dumps(alias))
for measured_path, out in (("measured.json", "delta-long.json"), ("measured-alias.json", "delta-short.json")):
    result = run(os.path.join(CO, "voice.py"), "delta", "reel2.json", measured_path,
                 "-o", out, "--tolerance", "100", ok=False)
    assert result.returncode == 0, result.stdout + result.stderr
check(33, "voice delta accepts either timestamp spelling and shuffled word entries",
      json.load(open("delta-long.json")) == json.load(open("delta-short.json")))

# Numeric, union and reference validation must not let non-finite values,
# booleans-as-times, duplicate indices or conflicting aliases slip through.
invalid_measurements = [
    {"words": [{"i": 0, "s": True, "e": 1}]},
    {"words": [{"i": 0, "s": float("nan"), "e": 1}]},
    {"words": [{"i": 0, "s": 0, "e": float("inf")}]},
    {"words": [{"i": 0, "s": 2, "e": 1}]},
    {"words": [{"i": 0, "s": 0, "e": 1}, {"i": 0, "s": 1, "e": 2}]},
    {"words": [{"i": 0, "start": 0, "s": 1, "end": 2}]},
]
for bad_measurement in invalid_measurements:
    try:
        validate_document(bad_measurement, "measured")
    except SchemaError:
        pass
    else:
        raise AssertionError("malformed word alignment was accepted")
for legacy in ({"beats": {"B1": 2.0}}, {"sections": {"0": 2.0}}):
    validate_document(legacy, "measured")
check(34, "measured contract rejects ambiguous or invalid times and keeps legacy beat durations", True)

# Standalone packaging: each executable must find its own core and schemas
# without any sibling skill directories or repository imports.
for skill, args in (
    ("real-storyboarding", ("clock.py", "time", os.path.join(W, "notebook.json"), "-o", os.path.join(W, "isolated-clock.json"))),
    ("real-compile", ("fcpxml.py", "build", os.path.join(W, "story.json"), os.path.join(W, "isolated.fcpxml"), "--no-probe")),
    ("real-create-catalogue", ("build_catalog.py", os.path.join(W, "asset-catalog.json"), os.path.join(W, "isolated-catalog"))),
):
    isolated = Path(W, "standalone-" + skill)
    shutil.copytree(Path(ROOT, skill), isolated, ignore=shutil.ignore_patterns("__pycache__"))
    run(str(isolated / "scripts" / args[0]), *args[1:], cwd=str(isolated))
check(35, "standalone skills load their own vendored core and schemas", True)

print("\nALL %d CHECKS PASS (spec items covered: %s)"
      % (len(PASS), sorted(set(PASS))))
print("workdir: " + W)
