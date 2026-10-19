#!/usr/bin/env python3
"""run_real.py — drive the REAL batch-2 scripts over one benchmark project.

    python3 run_real.py PROJECT_DIR [--clock measured|estimated] [--skills DIR]

Writes everything into PROJECT_DIR/real-<clock>/ and returns a JSON record of
every stage: command, exit code, wall time, stdout tail. Nothing here decides
anything editorial; it only calls the skills' own scripts in the documented
order (the same commands SKILL.md tells the agent to run).
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# Evaluate a FROZEN copy of the skills, never the live tree another agent may
# be editing: REAL_SKILLS, else the eval worktree, else the live tree.
_FROZEN = os.path.join(HERE, "work", "eval-skills", "skills", "batch-2", "skills")
SKILLS = os.path.abspath(os.environ.get("REAL_SKILLS") or (
    _FROZEN if os.path.isdir(_FROZEN) else os.path.join(HERE, "..", "skills", "batch-2", "skills")))


def sh(log, name, *cmd, cwd=None, ok=True):
    t = time.time()
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True, cwd=cwd)
    rec = {"stage": name, "cmd": " ".join(os.path.basename(c) if i == 0 else c
                                           for i, c in enumerate(cmd)),
           "rc": r.returncode, "s": round(time.time() - t, 3),
           "out": (r.stdout + r.stderr)[-1500:]}
    log.append(rec)
    if ok and r.returncode != 0:
        raise RuntimeError("%s failed (rc=%d)\n%s" % (name, r.returncode, r.stdout + r.stderr))
    return r


def run(project, clock="measured", skills=SKILLS):
    SB = os.path.join(skills, "real-storyboarding", "scripts")
    CO = os.path.join(skills, "real-compile", "scripts")
    media = os.path.abspath(os.path.join(project, "media"))
    out = os.path.abspath(os.path.join(project, "real-" + clock))
    os.makedirs(out, exist_ok=True)
    log, t0 = [], time.time()
    P = lambda *a: os.path.abspath(os.path.join(project, *a))  # noqa: E731
    try:
        sh(log, "parse", os.path.join(SB, "notebook.py"), "parse", P("NOTEBOOK.md"),
           "-o", "notebook.json", cwd=out)
        # Measure first when the scripts support it (SKILL.md: "if the
        # narration is already recorded, measure it before placing anything");
        # the published scripts can only estimate and swap later.
        measure_first = (clock == "measured" and "--measured" in
                         open(os.path.join(SB, "clock.py")).read())
        if measure_first:
            sh(log, "clock", os.path.join(SB, "clock.py"), "time", "notebook.json",
               "-o", "clock.json", "--measured", P("measured.json"), cwd=out)
        else:
            sh(log, "clock", os.path.join(SB, "clock.py"), "time", "notebook.json",
               "-o", "clock.json", cwd=out)
        sh(log, "bind", os.path.join(SB, "bind.py"), "bind", "notebook.json",
           P("asset-catalog.json"), "-o", "bindings.json", cwd=out)
        sh(log, "build", os.path.join(SB, "build.py"), "build", "notebook.json",
           "clock.json", "bindings.json", "-o", "reel.json",
           "--assets-root", media, "--stubs-dir", "stubs", cwd=out)
        rev = P("revisions.txt")
        if os.path.exists(rev) and open(rev).read().strip():
            sh(log, "revise", os.path.join(SB, "revise.py"), "apply", "reel.json", rev,
               "-o", "reel.json", "--clock", "clock.json", cwd=out)
        if clock == "measured" and not measure_first:
            sh(log, "swap", os.path.join(SB, "clock.py"), "swap", "clock.json",
               P("measured.json"), "-o", "clock.json", cwd=out)
            sh(log, "retime", os.path.join(SB, "build.py"), "retime", "reel.json",
               "clock.json", "-o", "reel.json", cwd=out)
        sh(log, "reel-validate", os.path.join(SB, "build.py"), "validate", "reel.json", cwd=out)
        sh(log, "adapt", os.path.join(CO, "adapt.py"), "reel.json", "-o", "story.json",
           "--assets-root-local", media, cwd=out)
        sh(log, "compile", os.path.join(CO, "compile.py"), "build", "story.json",
           "timeline.fcpxml", "--target", "fcpxml", cwd=out)
        v = sh(log, "validate", os.path.join(CO, "compile.py"), "validate",
               "timeline.fcpxml", "--local-root", media, cwd=out, ok=False)
        ok = v.returncode == 0
        err = None
    except RuntimeError as e:
        ok, err = False, str(e)[:2000]
    rec = {"project": project, "clock": clock, "ok": ok, "error": err,
           "wall_s": round(time.time() - t0, 3), "stages": log,
           "fcpxml": os.path.join(out, "timeline.fcpxml")
           if os.path.exists(os.path.join(out, "timeline.fcpxml")) else None}
    json.dump(rec, open(os.path.join(out, "run.json"), "w"), indent=1)
    return rec


if __name__ == "__main__":
    clock = sys.argv[sys.argv.index("--clock") + 1] if "--clock" in sys.argv else "measured"
    rec = run(sys.argv[1], clock)
    print(json.dumps({k: v for k, v in rec.items() if k != "stages"}, indent=1))
    for s in rec["stages"]:
        print("  %-14s rc=%d %.2fs" % (s["stage"], s["rc"], s["s"]))
    if rec["error"]:
        print(rec["error"])
