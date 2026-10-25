#!/usr/bin/env bash
# Rebuild the Minuet explainer from this folder's media with the REAL skills.
# Run from demo/abc-minuet:   bash scripts/build.sh
#
# The notebook (source/NOTEBOOK.md), the seven narration takes (source/narration/vo-*.mp3)
# and the catalogue judgement (catalogue/catalog_data.json) are the inputs; the stills
# and the piano in media/ come from scripts/make_*.py. Everything under storyboard/
# and timeline/, and media/Audio/narration-master.mp3, is produced here.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(cd ../.. && pwd)
ST=$ROOT/skills/batch-2/skills/real-storyboarding/scripts
CAT=$ROOT/skills/batch-2/skills/real-create-catalogue/scripts
COMPILE=$ROOT/skills/batch-2/skills/real-compile/scripts
ASSETS_ROOT=${ASSETS_ROOT:-/Users/Shared/REAL/demo/abc-minuet/media}   # the path the editors will see
NAME=minuet-abc
mkdir -p storyboard timeline

catalogue_and_storyboard() {
  python3 "$CAT/scan.py" media catalogue/work --budget 35 --force >/dev/null
  (cd media && python3 "$CAT/build_catalog.py" ../catalogue/catalog_data.json ../catalogue | tail -1)
  python3 "$ST/bind.py" bind storyboard/notebook.json catalogue/asset-catalog.json -o storyboard/bindings.json | head -1
  python3 "$ST/build.py" build storyboard/notebook.json storyboard/clock.json storyboard/bindings.json \
      -o storyboard/reel.json --stubs-dir storyboard/stubs --assets-root "$ASSETS_ROOT" | head -1
}

# 1. the measured clock: the takes laid on one voice track at the estimated clock's
#    narration starts, then force-aligned to the script
python3 "$ST/notebook.py" parse source/NOTEBOOK.md -o storyboard/notebook.json | head -1
python3 "$ST/clock.py" time storyboard/notebook.json -o storyboard/clock-est.json > /dev/null
python3 scripts/layout_voice.py
python3 -c "import json;C=json.load(open('storyboard/clock-est.json'));print(' '.join(w['w'] for w in C['words']))" \
    > source/narration.txt
python3 "$COMPILE/voice.py" measure --script source/narration.txt --audio storyboard/voice-master.wav \
    -o storyboard/measured.json --oov source/oov.json | head -1
python3 "$ST/clock.py" time storyboard/notebook.json -o storyboard/clock.json \
    --measured storyboard/measured.json --pauses hold | grep -v plain-English

# 2. pass 1 on the untrimmed voice track, so the reel can say where its first narration clip starts
ffmpeg -v error -y -i storyboard/voice-master.wav -c:a libmp3lame -b:a 256k -ar 48000 media/Audio/narration-master.mp3
catalogue_and_storyboard
# pass 2: compile reads the narration file continuously from its first clip, so file time 0 must be
# that clip's start. Trim the voice track by exactly that much and rebuild, or every line plays late.
T0=$(python3 -c "import json;R=json.load(open('storyboard/reel.json'));print(min(a['t0'] for b in R['beats'] for a in b.get('audio',[]) if a['kind']=='narration'))")
ffmpeg -v error -y -ss "$T0" -i storyboard/voice-master.wav -c:a libmp3lame -b:a 256k -ar 48000 media/Audio/narration-master.mp3
echo "narration track trimmed by ${T0}s: file time 0 = the first narration clip"
catalogue_and_storyboard
python3 "$ST/tracks.py" tracks storyboard/reel.json storyboard/REEL-TRACKS.html --clock storyboard/clock.json | head -1

# 3. compile to both targets and check them against each other
python3 "$COMPILE/adapt.py" storyboard/reel.json -o timeline/story.json --assets-root-local "$(pwd)/media" | tail -2
python3 scripts/pad_narration.py timeline/story.json
python3 "$COMPILE/compile.py" build timeline/story.json "timeline/$NAME.fcpxml" | tail -2
python3 "$COMPILE/compile.py" report "timeline/$NAME.fcpxml" timeline/report.html | tail -1
python3 "$COMPILE/compile.py" build timeline/story.json "timeline/$NAME.otio" --target otio --titles raster | tail -1
python3 "$ROOT/bench/otio_edl.py" "timeline/$NAME.otio" --against "timeline/$NAME.fcpxml" --report timeline/equivalence.json | tail -1
python3 scripts/relative_paths.py "timeline/$NAME.fcpxml" "media/$NAME-relative.fcpxml"
rm -f storyboard/voice-master.wav
python3 scripts/check_narration.py
