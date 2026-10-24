#!/bin/sh
# How the source media in ../media/Videos was cut. Run from this folder.
#
# The studio-background recording (3:41, 540x960, 30 fps; the creator's BiRefNet
# re-render of the original bedroom recording, with a band across the bottom
# tenth that hides the matte edge; same audio sample for sample) is not in the
# repository; only the five excerpts the tutorial uses are. The windows are the
# ones chosen for the earlier edit (../source/TRANSCRIPT.md).
set -e
SRC=${1:-$HOME/Downloads/paganini_no23_fingering_studio_band.mp4}
CLOSURE=${2:-$HOME/Downloads/paganini_no23_closure.mov}
OUT=../media/Videos
i=0
for w in 0.2:8.1 29.0:45.5 61.2:72.4 150.4:163.2 201.3:220.3; do
  i=$((i+1))
  ffmpeg -v error -y -ss ${w%%:*} -to ${w##*:} -i "$SRC" \
    -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 160k "$OUT/P-studio-0$i.mov"
done
# The closing clip arrived as 584x978 at 60 fps; cropped once to 550x978 (9:16)
# so that neither editor needs a transform. Audio copied untouched.
ffmpeg -v error -y -i "$CLOSURE" -vf "crop=550:978:17:0" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy "$OUT/P-closure.mov"
# The opening performance (P-intro-performance-30fps.mov), the five narration
# takes (../media/Audio, the same audio as the excerpts, used for the measured
# word clock) and the three stills (../media/Images) are carried over from the
# earlier edit unchanged.
for f in "$OUT"/P-studio-0?.mov "$OUT"/P-closure.mov; do
  printf '%-22s ' "$(basename "$f")"; ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"
done
