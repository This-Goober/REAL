#!/usr/bin/env python3
"""The `fcpxml` target — Final Cut Pro 11, FCPXML 1.13.

This is a thin adapter. All of the real work is in ../fcpxml.py, ../validate.py
and ../report.py, which are verified against Final Cut Pro 11 and are not to be
rewritten. If something here needs changing, it is almost certainly the adapter
and not the generator.
"""

import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fcpxml  # noqa: E402
import report as report_mod  # noqa: E402
import validate as validate_mod  # noqa: E402

from . import BuildResult, ValidateResult  # noqa: E402


class FCPXMLTarget:
    name = "fcpxml"
    extension = ".fcpxml"
    description = ("Final Cut Pro 11 timeline (FCPXML 1.13) — import with "
                   "File > Import > XML…")

    def build(self, story, out_path, base_dir=".", probe=True):
        s = fcpxml.Story(story, base_dir=base_dir, do_probe=probe)
        xml = s.build()
        with open(out_path, "w") as f:
            f.write(xml)
        summary = ("%dx%d, %.2fs, %d frames @ %s fps"
                   % (s.width, s.height, s.clock.seconds(s.total_frames),
                      s.total_frames, s.clock.key))
        return BuildResult(out_path, s.warnings, summary)

    def validate(self, path, local_root=None):
        # validate.py keeps its findings in module globals; clear them so a
        # second call in the same process doesn't inherit the first one's.
        validate_mod.errors[:] = []
        validate_mod.warns[:] = []
        argv = ["validate.py", path]
        if local_root:
            argv += ["--local-root", local_root]
        with redirect_stdout(io.StringIO()):
            validate_mod.main(argv)
        return ValidateResult(list(validate_mod.errors),
                              list(validate_mod.warns))

    def report(self, path, out_html):
        with redirect_stdout(io.StringIO()):
            report_mod.main(["report.py", path, out_html])
        return out_html


TARGET = FCPXMLTarget()
