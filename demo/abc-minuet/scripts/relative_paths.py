"""Write a copy of the FCPXML whose media paths are relative to the .fcpxml itself (Audio/x.mp3, Images/x.png), so the
media folder can be copied anywhere and imported without relinking. FCPXML 1.10+ resolves a relative media-rep src
against the document's own location (the mechanism .fcpxmld bundles rely on); REAL's generator always writes absolute
file:// URLs. Untested on Final Cut until the owner imports it (REAL finding 9)."""
import re, sys
src = sys.argv[1] if len(sys.argv) > 1 else "timeline/minuet-abc.fcpxml"
out = sys.argv[2] if len(sys.argv) > 2 else "media/minuet-abc-relative.fcpxml"
s = open(src).read()
s, n = re.subn(r'src="(?:file://)?[^"]*?/media/((?:Audio|Images)/[^"]+)"', r'src="\1"', s)
open(out, "w").write(s)
print(f"{n} media paths made relative -> {out}")
