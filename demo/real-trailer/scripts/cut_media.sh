#!/bin/sh
# How the media in ../media was made. Run from the demo folder (demo/real-trailer).
#
# Every picture in the trailer is a real output of REAL or a capture of one of
# REAL's own pages; nothing was generated. The sources (the creator's Final Cut
# export of the Paganini No. 23 tutorial, the two-panel comparison movie, the
# creator's screen recording of the .fcpxml import, the creator's recording of
# the Paganini performance) are not in the repository; only the excerpts are.
#
#   Videos/T-tutorial-render.mov   18.8–24.6 s of the Final Cut Pro export of demo/paganini-no23
#   Videos/T-side-by-side.mov      33.4–41.4 s of that demo's two-panel comparison movie (silent)
#   Videos/T-finalcut-editor.mov   16.0–22.0 s of the creator's screen recording of the import (silent, 30 fps)
#   Videos/T-tracks.mov            this reel's own tracks page, captured frame by frame (capture_pages.py)
#   Images/T-notebook.png          this reel's own notebook, rendered in an editor-style page (capture_pages.py)
#   Images/T-catalogue.png         this reel's own catalogue page (capture_pages.py)
#   Images/T-title-made-with-real.png  the closing card (make_title_card.py)
#   Audio/bed-paganini-performance.wav the creator's own performance: the recording's opening
#                                  passage (0.2–8.1 s) and closing passage (201.3–220.3 s), joined
#                                  with 1 s crossfades, repeated once, 3 s fade-out
#   Audio/take-01..06.wav          the six narration lines, one per beat, each file starting on its
#                                  first word (measured), 48 kHz mono
#
# The narration is a synthesized read (edge-tts, voice en-US-AndrewMultilingualNeural,
# rate +12 %), a stand-in for a human recording: replace the six files, re-run
# the build, and every placement follows its word.
set -e
FCP_EXPORT=${1:-$HOME/Downloads/paganini-no23-finalcutpro.mov}
SIDE_BY_SIDE=${2:-../../bench/work/media/paganini-23-octaves-60s/v5-studio/comparison-v5.4/side-by-side-demo.mp4}
FCP_RECORDING=${3:-$HOME/Desktop/final_cut_pro_fcpxml_paganini_no_23_tutorial.mov}
RECORDING=${4:-$HOME/Downloads/paganini_no23_fingering_studio_band.mp4}
V=media/Videos; A=media/Audio; I=media/Images
ffmpeg -v error -y -ss 18.8 -to 24.6 -i "$FCP_EXPORT" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 160k "$V/T-tutorial-render.mov"
ffmpeg -v error -y -ss 33.4 -to 41.4 -i "$SIDE_BY_SIDE" -c:v libx264 -crf 18 -pix_fmt yuv420p -an "$V/T-side-by-side.mov"
ffmpeg -v error -y -ss 16.0 -to 22.0 -i "$FCP_RECORDING" -r 30 -c:v libx264 -crf 18 -pix_fmt yuv420p -an "$V/T-finalcut-editor.mov"
ffmpeg -v error -y -ss 0.2 -to 8.1 -i "$RECORDING" -vn -ac 1 -ar 48000 -c:a pcm_s16le /tmp/bed-a.wav
ffmpeg -v error -y -ss 201.3 -to 220.3 -i "$RECORDING" -vn -ac 1 -ar 48000 -c:a pcm_s16le /tmp/bed-b.wav
ffmpeg -v error -y -i /tmp/bed-a.wav -i /tmp/bed-b.wav -i /tmp/bed-a.wav -i /tmp/bed-b.wav \
  -filter_complex "[0][1]acrossfade=d=1[ab];[ab][2]acrossfade=d=1[abc];[abc][3]acrossfade=d=1,atrim=0:48,afade=t=out:st=45:d=3" \
  -ac 1 -ar 48000 -c:a pcm_s16le "$A/bed-paganini-performance.wav"
python3 scripts/make_title_card.py "$I/T-title-made-with-real.png"
python3 scripts/capture_pages.py notebook source/NOTEBOOK.md "$I/T-notebook.png"
# Narration: one line per beat, in source/narration.txt order, then each file
# trimmed to start on its first measured word (see PROMPTS.md):
#   edge-tts --voice en-US-AndrewMultilingualNeural --rate=+12% --text "<line>" --write-media take.mp3
#   ffmpeg -i take.mp3 -af "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,areverse" -ac 1 -ar 48000 -c:a pcm_s16le take-0N.wav
# The two page captures need the pipeline's own outputs and are made by build.sh.
for f in "$V"/T-*.mov "$A"/*.wav; do
  printf '%-34s ' "$(basename "$f")"; ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"
done
