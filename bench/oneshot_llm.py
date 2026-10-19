#!/usr/bin/env python3
"""oneshot_llm.py — the direct model-as-compiler baseline.

The same brief REAL gets (the notebook, the human-labelled catalogue, the
measured word times, the documented placement semantics and the FCPXML rules
REAL's own generator follows) is handed to a language model in ONE prompt, and
the model is asked to write the complete .fcpxml itself. The first answer is
the deliverable, with no scripted compilation or validation loop. The supplied
notebook and catalogue are intermediate representations, so this is not an
ablation that removes them.

    python3 oneshot_llm.py PROJECT_DIR --model claude-sonnet-5-5 [--out DIR]

Uses the `claude` CLI in print mode with no tools. Writes DIR/timeline.fcpxml
(whatever the model produced, extracted from a code fence if there is one),
DIR/prompt.txt, DIR/response.txt and DIR/run.json (wall time, token usage
when the CLI reports it).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.join(HERE, "..", "skills", "batch-2", "skills", "real-compile",
                     "references", "fcpxml-notes.md")

SEMANTICS = """\
PLACEMENT SEMANTICS (the reference edit is defined by exactly these rules):
- The sequence is 1080x1920, 30 fps (frameDuration 100/3000s). Every time
  value must be a whole number of frames.
- Each `## beat` cell is one beat. Its narration line is the <...> component
  with no leading verb; the words are timed by the measured alignment below
  (word index i runs over all narration words of the notebook in order).
- A beat occupies [start of its first word, end of its last word]. Between
  beats the screen is black (a gap on the spine). The timeline ends at the end
  of the last word.
- The `<video clip of ... #clipNN>` component is the beat's base shot: it runs
  on the primary storyline for the whole beat, from source frame 0 of the file.
- Every other visual component (`<show image ... ~Ds #imgNN>`, `<caption: ...
  ~Ds>`) is an overlay on a lane above the base shot. With k overlays in a beat
  of L narration words starting at word index w0, overlay number g (1-based, in
  written order) is anchored to word w0 + floor(g * L / (k + 1)). An overlay
  starts 40% of the way into its anchor word, lasts its explicit `~Ds`
  duration, and is cut at the end of the beat if it would outlive it.
- The creator's revisions (below) override anchors by naming the word, and may
  set a text style. "L2" means the first overlay of that beat, "L3" the second.
- Text style "caption": fontSize 96, position 0 -620. Style "title": fontSize
  132, position 0 0. Font Helvetica Neue Bold, white, centred.
- Images are 1080x1080 stills and are placed to FIT (letterboxed, no scaling).
- Narration audio is not recorded yet: emit no audio clips.
- Times are snapped to the nearest frame: frame = round(seconds * 30).
"""


def prompt_for(project, rules=True):
    nb = open(os.path.join(project, "NOTEBOOK.md")).read()
    cat = json.load(open(os.path.join(project, "asset-catalog.json")))
    wt = json.load(open(os.path.join(project, "measured.json")))["words"]
    rev = open(os.path.join(project, "revisions.txt")).read().strip()
    notes = open(NOTES).read()
    root = os.path.abspath(os.path.join(project, "media"))
    cat_lines = "\n".join("- %s: %s (%s%s)" % (
        a["id"], a["f"], a["k"],
        ", %.1fs, %dx%d" % (a["dur"], a["w"], a["h"]) if a["k"] == "video"
        else ", %dx%d" % (a["w"], a["h"])) for a in cat["assets"])
    words = " ".join("%d:%s[%.3f-%.3f]" % (w["i"], w["w"], w["start"], w["end"]) for w in wt)
    return """You are a video editor's assistant. Produce a complete Final Cut Pro
FCPXML 1.13 timeline for the reel described below. Output ONLY the XML
document (you may wrap it in a single ```xml fence), nothing else. Do not ask
questions; do not explain.

%s
NOTEBOOK.md (the creator's script):
----------------------------------
%s
----------------------------------

ASSET CATALOGUE (assets_root = %s; every media-rep src must be
file://%s/<relative path>):
%s

MEASURED WORD TIMES (index:word[start-end] in seconds):
%s

CREATOR REVISIONS:
%s

%s
""" % (SEMANTICS, nb, root, root, cat_lines, words, rev or "(none)",
       ("FCPXML RULES (these are the generator notes REAL's own compile step "
        "follows;\nFinal Cut DTD-validates on import):\n"
        "----------------------------------\n" + notes) if rules else
       "Write FCPXML 1.13 that Final Cut Pro 11 will import without error.")


def extract_xml(text):
    m = re.search(r"```(?:xml)?\s*(<\?xml.*?</fcpxml>)\s*```", text, re.S)
    if m:
        return m.group(1)
    m = re.search(r"(<\?xml.*?</fcpxml>)", text, re.S)
    if m:
        return m.group(1)
    m = re.search(r"(<fcpxml.*?</fcpxml>)", text, re.S)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + m.group(1)) if m else None


def run(project, model, out=None, timeout=900, rules=True):
    out = out or os.path.join(project, "oneshot-" + model)
    os.makedirs(out, exist_ok=True)
    prompt = prompt_for(project, rules=rules)
    open(os.path.join(out, "prompt.txt"), "w").write(prompt)
    t0 = time.time()
    cmd = ["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence",
           "--output-format", "json"]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
    wall = round(time.time() - t0, 2)
    text, usage, cost = r.stdout, None, None
    try:
        j = json.loads(r.stdout)
        text = j.get("result", "")
        usage = j.get("usage")
        cost = j.get("total_cost_usd")
    except Exception:  # noqa: BLE001
        pass
    open(os.path.join(out, "response.txt"), "w").write(text)
    xml = extract_xml(text)
    if xml:
        open(os.path.join(out, "timeline.fcpxml"), "w").write(xml)
    rec = {"project": project, "model": model, "rules": rules, "wall_s": wall, "rc": r.returncode,
           "got_xml": bool(xml), "usage": usage, "cost_usd": cost,
           "stderr": r.stderr[-500:]}
    json.dump(rec, open(os.path.join(out, "run.json"), "w"), indent=1)
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-rules", action="store_true")
    a = ap.parse_args()
    rec = run(a.project, a.model, a.out, rules=not a.no_rules)
    print(json.dumps({k: v for k, v in rec.items() if k != "stderr"}, indent=1))
