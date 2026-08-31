#!/usr/bin/env python3
"""
compile.py — the front door. Turn the internal story.json into a timeline file
for whichever editor is the target.

    python3 compile.py targets
    python3 compile.py build story.json out.fcpxml [--target fcpxml] [--no-probe]
    python3 compile.py validate out.fcpxml [--local-root /path]
    python3 compile.py report out.fcpxml report.html [--target fcpxml]

`--target` defaults to fcpxml, the only target implemented today. The point of
routing through here rather than calling fcpxml.py directly is that the
sequencing side (reel.json -> story.json, in adapt.py) stays format-blind:
adding Premiere XML or an EDL is one module in scripts/targets/ and one line in
its REGISTRY. See references/targets.md.

`build` validates by default and refuses to leave a file with errors in place —
delivering a broken timeline costs the creator a trip to Final Cut to find out.
Use --no-validate only when you are deliberately inspecting a bad build.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import targets  # noqa: E402


def _arg(argv, flag, default=None):
    return argv[argv.index(flag) + 1] if flag in argv else default


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    tname = _arg(argv, "--target", targets.DEFAULT)

    if cmd == "targets":
        print("export targets:")
        for name, ext, desc in targets.available():
            print("  %-10s %-9s %s%s"
                  % (name, ext, desc,
                     "   [default]" if name == targets.DEFAULT else ""))
        print("\nadd one: a module in scripts/targets/ + a line in "
              "targets/REGISTRY. See references/targets.md.")
        return 0

    try:
        target = targets.get(tname)
    except targets.UnknownTarget as e:
        print("ERROR %s" % e)
        return 2

    if cmd == "build":
        story_path, out_path = argv[2], argv[3]
        story = json.load(open(story_path))
        local_root = story.get("assets_root_local") or None
        if local_root == story.get("assets_root"):
            local_root = None  # same folder: the baked paths are the real ones
        res = target.build(
            story, out_path,
            base_dir=os.path.dirname(os.path.abspath(story_path)),
            probe="--no-probe" not in argv)
        print("wrote %s  (%s)" % (res.path, res.summary))
        if story.get("unvoiced"):
            import adapt
            print("\n" + adapt.badge_text(story["unvoiced"]) + "\n")
        for w in res.warnings:
            print("  warning: " + w)
        if "--no-validate" in argv:
            return 0
        v = target.validate(out_path, local_root)
        for w in v.warnings:
            print("  WARN  " + w)
        for e in v.errors:
            print("  ERROR " + e)
        print("validate: %d error(s), %d warning(s)"
              % (len(v.errors), len(v.warnings)))
        if not v.ok:
            print("NOT DELIVERABLE — fix the errors above before sending this "
                  "file anywhere.")
            return 1
        return 0

    if cmd == "validate":
        v = target.validate(argv[2], _arg(argv, "--local-root"))
        for w in v.warnings:
            print("WARN  " + w)
        for e in v.errors:
            print("ERROR " + e)
        print("\n%d error(s), %d warning(s)" % (len(v.errors), len(v.warnings)))
        return 0 if v.ok else 1

    if cmd == "report":
        fn = getattr(target, "report", None)
        if fn is None:
            print("target %r has no report renderer" % tname)
            return 2
        out = fn(argv[2], argv[3])
        print("wrote " + str(out))
        return 0

    print("unknown command %r" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
