#!/usr/bin/env python3
"""
retarget.py — point an .fcpxml's media at a different folder.

    python3 retarget.py timeline.fcpxml /new/media/root [out.fcpxml]

Rewrites every <media-rep src="file://..."> so the basename (and any
sub-path below the old common root) hangs off the new root instead.
Use this when the file was generated somewhere the media wasn't, or when
the footage moved. Final Cut matches media by path, so a wrong root is the
single most common reason an import lands with red "Missing Media" clips.

With --flat, every file is looked up by basename directly under the new
root (handy when a folder got reorganised).
"""

import os
import re
import sys
from urllib.parse import quote, unquote

SRC_RE = re.compile(r'(<media-rep\b[^>]*\bsrc=")(file://[^"]*)(")')


def main(argv):
    path = argv[1]
    new_root = os.path.abspath(os.path.expanduser(argv[2]))
    out = argv[3] if len(argv) > 3 and not argv[3].startswith("--") else path
    flat = "--flat" in argv

    xml = open(path).read()
    olds = [unquote(m.group(2)[7:]) for m in SRC_RE.finditer(xml)]
    if not olds:
        print("no media-rep src attributes found")
        return 1
    # deepest folder every source shares — sub-structure below it is preserved
    common = os.path.commonpath(olds) if len(olds) > 1 else os.path.dirname(olds[0])
    if os.path.splitext(common)[1]:
        common = os.path.dirname(common)

    n_ok = n_missing = 0
    report = []

    def sub(m):
        nonlocal n_ok, n_missing
        old = unquote(m.group(2)[7:])
        rel = os.path.basename(old) if flat else os.path.relpath(old, common)
        new = os.path.join(new_root, rel)
        if os.path.exists(new):
            n_ok += 1
        else:
            n_missing += 1
            report.append(new)
        return m.group(1) + "file://" + quote(new) + m.group(3)

    xml = SRC_RE.sub(sub, xml)
    open(out, "w").write(xml)
    print("wrote %s — %d media found, %d missing" % (out, n_ok, n_missing))
    for r in report:
        print("  missing: " + r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
