#!/bin/sh
# How the source media in ../media was cut. Run from this folder.
#
# The studio-background recording (3:41, 540x960, 30 fps; the creator's BiRefNet
# re-render of the original bedroom recording, with a band across the bottom
# tenth that hides the matte edge; same audio sample for sample) is not in the
# repository; only the five excerpts the tutorial uses are. The windows are the
# ones chosen for the earlier edit (../source/TRANSCRIPT.md) with the creator's
# revisions applied (../source/revisions.json): beat 2 starts on "for example",
# beat 3 ends after "smaller", beat 4 starts just before "interval", and the
# dissolve from beat 3 into beat 4 borrows half a second of picture on each
# side, so those two excerpts carry that much extra file beyond the window
# (beat 4's shot then starts 0.5 s into its file). Every edge is a whole frame.
#
# The five narration takes in ../media/Audio are the exact windows of the
# original recording's audio (the measured word clock was taken on them), with
# a 12 ms fade on each edge that falls inside speech so the cut cannot click.
set -e
SRC=${1:-$HOME/Downloads/paganini_no23_fingering_studio_band.mp4}
CLOSURE=${2:-$HOME/Downloads/paganini_no23_closure.mov}
RECORDING=${3:-$HOME/Downloads/paganini_no23_fingering.mov}
OUT=../media/Videos
TAKES=../media/Audio
FADE=0.012
cut_video() {  # n start end
  ffmpeg -v error -y -ss "$2" -to "$3" -i "$SRC" \
    -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 160k "$OUT/P-studio-0$1.mov"
}
cut_take() {   # n start end fade(in|out)
  len=$(echo "$3 - $2" | bc -l)
  if [ "$4" = in ]; then af="afade=t=in:st=0:d=$FADE"; else af="afade=t=out:st=$(echo "$len - $FADE" | bc -l):d=$FADE"; fi
  [ -f "$RECORDING" ] && ffmpeg -v error -y -ss "$2" -to "$3" -i "$RECORDING" -vn -af "$af" \
    -ac 1 -ar 48000 -c:a pcm_s16le "$TAKES/take-0$1.wav"
}
cut_video 2 32.0       45.5        ; cut_take 2 32.0       45.5      in     # beat 2: window 32.0-45.5
cut_video 3 61.2       72.533333   ; cut_take 3 61.2       72.033333 out    # beat 3: window 61.2-72.0333 + 0.5 s tail handle
cut_video 4 150.466667 163.2       ; cut_take 4 150.966667 163.2     in     # beat 4: 0.5 s head handle + window 150.9667-163.2
# Beats 1 and 5 keep their original windows, cut the same way without fades:
#   cut_video 1 0.2 8.1 ; cut_video 5 201.3 220.3   (takes: the same windows of $RECORDING)
# The closing clip arrived as 584x978 at 60 fps; cropped once to 550x978 (9:16)
# so that neither editor needs a transform. Audio copied untouched.
[ -f "$CLOSURE" ] && ffmpeg -v error -y -i "$CLOSURE" -vf "crop=550:978:17:0" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy "$OUT/P-closure.mov"
# The opening performance (P-intro-performance-30fps.mov) and the three stills
# (../media/Images) are carried over from the earlier edit unchanged.
for f in "$OUT"/P-studio-0?.mov "$OUT"/P-closure.mov "$TAKES"/take-0?.wav; do
  printf '%-22s ' "$(basename "$f")"; ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"
done
