#!/bin/sh
# Rebuild the trailer from this folder's media with the four REAL skills.
# Run from demo/real-trailer:   sh scripts/build.sh
#
# The notebook (source/NOTEBOOK.md) and the creator's revisions
# (source/revisions.txt) are the inputs a person wrote; everything under
# catalogue/, storyboard/ and timeline/ is produced here. The two captures of
# REAL's own pages (media/Images/T-catalogue.png, media/Videos/T-tracks-washi.mov)
# were taken from an earlier pass of this same build, before they existed as
# assets (see PROMPTS.md); with --captures they are taken again from the
# catalogue and tracks page this run writes, and the build runs once more so
# the catalogue describes them.
set -e
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
ST=$ROOT/skills/batch-2/skills/real-storyboarding/scripts
CAT=$ROOT/skills/batch-2/skills/real-create-catalogue/scripts
COMPILE=$ROOT/skills/batch-2/skills/real-compile/scripts
ASSETS_ROOT=${ASSETS_ROOT:-/Users/Shared/REAL/demo/real-trailer/media}   # the path the editors will see
NAME=real-trailer
TITLE="REAL in 30 seconds"
mkdir -p catalogue storyboard timeline preview

one_pass() {
  # 2. catalogue: measure, judge, build
  python3 "$CAT/scan.py" media catalogue/work --budget 60 --force >/dev/null
  python3 scripts/catalogue_judgement.py catalogue/work/skeleton.json catalogue/catalog_data.json
  (cd media && python3 "$CAT/build_catalog.py" ../catalogue/catalog_data.json ../catalogue | tail -1)
  # 3. storyboard: the measured clock first, then bind, build, revise, tracks page
  python3 "$ST/notebook.py" parse source/NOTEBOOK.md -o storyboard/notebook.json
  python3 "$ST/clock.py" time storyboard/notebook.json -o storyboard/clock.json \
      --measured storyboard/measured.json --pauses hold
  python3 "$ST/bind.py" bind storyboard/notebook.json catalogue/asset-catalog.json -o storyboard/bindings.json
  python3 "$ST/build.py" build storyboard/notebook.json storyboard/clock.json storyboard/bindings.json \
      -o storyboard/reel.json --stubs-dir storyboard/stubs --assets-root "$ASSETS_ROOT"
  python3 "$ST/revise.py" apply storyboard/reel.json source/revisions.txt -o storyboard/reel.json --clock storyboard/clock.json
  python3 "$ST/build.py" validate storyboard/reel.json
  # every caption line fits the frame; the bottom captions sit in the middle of the
  # paper quarter, closer to the edge than the default 5 % margin
  python3 scripts/check_captions.py storyboard/reel.json --margin 0.025
  python3 "$ST/tracks.py" tracks storyboard/reel.json storyboard/REEL-TRACKS.html --clock storyboard/clock.json
}

# 0. the narration: media/Audio/take-01..06.wav, one per line of source/narration.txt,
#    each starting on its first word. scripts/narrate.py writes them (ElevenLabs, Kokoro
#    or edge); the other reads tried are kept under source/narration/<engine>/.
# 1. the measured clock: the six takes, concatenated with 0.4 s between them and
#    3 s of silence after the last, force-aligned to the script
A=media/Audio
ffmpeg -v error -y -f lavfi -t 0.4 -i anullsrc=r=48000:cl=mono -c:a pcm_s16le storyboard/gap.wav
: > storyboard/takes.txt
for n in 01 02 03 04 05 06; do
  [ "$n" != 01 ] && printf "file '%s'\n" "$(pwd)/storyboard/gap.wav" >> storyboard/takes.txt
  printf "file '%s'\n" "$(pwd)/$A/take-$n.wav" >> storyboard/takes.txt
done
ffmpeg -v error -y -f concat -safe 0 -i storyboard/takes.txt -af "apad=pad_dur=3" -c:a pcm_s16le storyboard/narration-master.wav
python3 "$COMPILE/voice.py" measure --script source/narration.txt --audio storyboard/narration-master.wav \
    -o storyboard/measured.json --oov source/oov.json | head -1
rm -f storyboard/gap.wav storyboard/takes.txt

one_pass
if [ "$1" = "--captures" ]; then
  python3 scripts/capture_pages.py page catalogue/ASSET-CATALOG.html media/Images/T-catalogue.png
  TMPC=$(mktemp -d)
  python3 scripts/capture_pages.py tracks storyboard/REEL-TRACKS.html "$TMPC/tracks.mov" --from 0 --to 7.17
  # the preview pane and the start of the lanes, where the playhead moves, as a
  # framed panel on washi (転 storyboard)
  python3 scripts/make_panel_frame.py "$TMPC/frame.png" --step 転 --label STORYBOARD --of "3 / 4" --tag tracks \
      --headline "THE TRACKS PAGE" --deck "this trailer's own storyboard"
  python3 scripts/panel.py "$TMPC/tracks.mov" media/Videos/T-tracks-washi.mov --crop 280:1090 --opacity 0.85 \
      --frame "$TMPC/frame.png"
  rm -rf "$TMPC"
  one_pass
fi

# 4. compile to both targets and check them against each other
python3 "$COMPILE/adapt.py" storyboard/reel.json -o timeline/story.json --assets-root-local "$(pwd)/media"
python3 "$COMPILE/compile.py" build timeline/story.json "timeline/$NAME.fcpxml"
python3 "$COMPILE/compile.py" report "timeline/$NAME.fcpxml" timeline/report.html
python3 "$COMPILE/compile.py" build timeline/story.json "timeline/$NAME.otio" --target otio --titles raster
python3 "$ROOT/bench/otio_edl.py" "timeline/$NAME.otio" --against "timeline/$NAME.fcpxml" --report timeline/equivalence.json | tail -1

# 5. a preview movie of the compiled timeline (the editors make the real renders)
python3 scripts/render_preview.py "timeline/$NAME.otio" "preview/$NAME-preview.mp4" --media-root media
