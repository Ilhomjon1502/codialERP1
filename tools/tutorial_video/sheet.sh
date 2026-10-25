#!/usr/bin/env bash
# Tekshiruv uchun kontakt varaq: bash sheet.sh 01 [oraliq_s] → out/check/01_sheet_N.jpg (har birida 12 kadr)
cd "$(dirname "$0")"
FF=$(.venv/Scripts/python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
n=$1; step=${2:-10}
vid=$(ls ../../docs/video/${n}_*.mp4 | head -1)
mkdir -p out/check
rm -f out/check/${n}_sheet_*.jpg
"$FF" -hide_banner -loglevel error -i "$vid" -vf "fps=1/${step},scale=640:-1,drawtext=text='%{pts\:hms}':x=8:y=8:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=3x4" -q:v 4 "out/check/${n}_sheet_%d.jpg" -y
ls out/check/${n}_sheet_*.jpg
