#!/bin/sh
# How the source media in ../media was cut. Run from this folder.
#
# The studio-background recording (3:41, 540x960, 30 fps; the creator's BiRefNet
# re-render of the original bedroom recording, with a band across the bottom
# tenth that hides the matte edge; same audio sample for sample) is not in the
# repository; only the five excerpts the tutorial uses are. The windows are the
# ones chosen for the earlier edit (../source/TRANSCRIPT.md) with the creator's
# narration trims applied (../source/narration-trims.json): beat 2 starts on
# "for example", beat 3 ends after "smaller", beat 4 starts just before
# "interval". Every window edge is a whole frame at 30 fps.
#
# The five narration takes in ../media/Audio are the same windows of the
# original recording's audio (the measured word clock was taken on them).
# A 12 ms fade at each edge that falls inside speech keeps the cut from clicking.
set -e
SRC=${1:-$HOME/Downloads/paganini_no23_fingering_studio_band.mp4}
CLOSURE=${2:-$HOME/Downloads/paganini_no23_closure.mov}
RECORDING=${3:-$HOME/Downloads/paganini_no23_fingering.mov}
OUT=../media/Videos
TAKES=../media/Audio
FADE=0.012
i=0
for w in 31.5:45.5:in 61.2:72.033333:out 150.966667:163.2:in; do
  i=$((i+1))
  a=${w%%:*}; rest=${w#*:}; b=${rest%%:*}; edge=${rest##*:}
  len=$(echo "$b - $a" | bc -l)
  if [ "$edge" = in ]; then af="afade=t=in:st=0:d=$FADE"; else af="afade=t=out:st=$(echo "$len - $FADE" | bc -l):d=$FADE"; fi
  n=$((i+1))
  ffmpeg -v error -y -ss "$a" -to "$b" -i "$SRC" -af "$af" \
    -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 160k "$OUT/P-studio-0$n.mov"
  [ -f "$RECORDING" ] && ffmpeg -v error -y -ss "$a" -to "$b" -i "$RECORDING" -vn -af "$af" \
    -ac 1 -ar 48000 -c:a pcm_s16le "$TAKES/take-0$n.wav"
done
# Beats 1 and 5 keep their original windows, cut the same way without fades:
#   ffmpeg -ss 0.2 -to 8.1 -i "$SRC" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 160k P-studio-01.mov
#   ffmpeg -ss 201.3 -to 220.3 -i "$SRC" ... P-studio-05.mov
# The closing clip arrived as 584x978 at 60 fps; cropped once to 550x978 (9:16)
# so that neither editor needs a transform. Audio copied untouched.
[ -f "$CLOSURE" ] && ffmpeg -v error -y -i "$CLOSURE" -vf "crop=550:978:17:0" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy "$OUT/P-closure.mov"
# The opening performance (P-intro-performance-30fps.mov) and the three stills
# (../media/Images) are carried over from the earlier edit unchanged.
for f in "$OUT"/P-studio-0?.mov "$OUT"/P-closure.mov "$TAKES"/take-0?.wav; do
  printf '%-22s ' "$(basename "$f")"; ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"
done
