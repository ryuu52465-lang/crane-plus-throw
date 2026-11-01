#!/bin/bash
# コンテナ内で実行: ai_throw_node の record_dir に保存した録画とAIの判断画像から、提出用の動画を作る
#   1. 1投を通しで(throw_2)  2. スナップのスロー再生(1/4倍速)  3. 近・中・遠の3投(右にAIの判断画面)
# 使い方: make_video.sh 録画フォルダ 出力mp4 [スロー開始秒 スロー終了秒]
set -e
DIR=${1:-/tmp/video}
OUT=${2:-/tmp/pai_throw_demo.mp4}
SLOW_FROM=${3:-8.0}
SLOW_TO=${4:-10.2}

# 画面いっぱい(1920x1080)に収める。Gazeboの録画は1502x942
FULL="scale=-2:1080,pad=1920:1080:(ow-iw)/2:0,setsar=1,fps=25,format=yuv420p"
# 左にGazebo(幅1280)、右にAIの判断画面(640x480)
SIDE="[0:v]scale=1280:-2[g];[1:v]scale=640:480[d];color=black:s=1920x1080:r=25[bg];\
[bg][g]overlay=0:(H-h)/2:shortest=1[t];[t][d]overlay=1280:300:shortest=1,setsar=1,format=yuv420p"

ffmpeg -v error -y -i "$DIR/throw_2.mp4" -vf "$FULL" -an /tmp/seg1.mp4
ffmpeg -v error -y -ss "$SLOW_FROM" -to "$SLOW_TO" -i "$DIR/throw_2.mp4" \
  -vf "setpts=4.0*PTS,$FULL" -an /tmp/seg2.mp4
for i in 1 2 3; do
  ffmpeg -v error -y -i "$DIR/throw_$i.mp4" -loop 1 -i "$DIR/debug_$i.png" \
    -filter_complex "$SIDE" -r 25 -an "/tmp/seg3_$i.mp4"
done

printf "file '/tmp/seg1.mp4'\nfile '/tmp/seg2.mp4'\nfile '/tmp/seg3_1.mp4'\nfile '/tmp/seg3_2.mp4'\nfile '/tmp/seg3_3.mp4'\n" > /tmp/segs.txt
ffmpeg -v error -y -f concat -safe 0 -i /tmp/segs.txt -c:v libx264 -crf 20 -pix_fmt yuv420p "$OUT"
ffprobe -v error -show_entries format=duration -show_entries stream=width,height -of default=nw=1 "$OUT"
