"""Tekshiruv: berilgan matnli qadamlarning o'rtasidagi kadrlarni bitta varaqqa yig'adi.

  python moments.py 06 "To'xtatish" "Formada:"  → out/check/06_moments.jpg
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

HERE = Path(__file__).resolve().parent
num, needles = sys.argv[1], sys.argv[2:]
timeline = json.loads((HERE / "out" / "raw" / f"{num}.json").read_text(encoding="utf-8"))
video = next((HERE.parents[1] / "docs" / "video").glob(f"{num}_*.mp4"))
ff = imageio_ffmpeg.get_ffmpeg_exe()
tiles = []
for n in needles:
    hit = next((s, e) for s, e, text, _ in timeline if n in text)
    for frac in (0.35, 0.85):
        t = hit[0] + (hit[1] - hit[0]) * frac
        out = HERE / "out" / "check" / f"_m{len(tiles)}.jpg"
        subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=800:-1", "-y", str(out)], check=True)
        tiles.append(Image.open(out))
w, h = tiles[0].size
sheet = Image.new("RGB", (w * 2, h * ((len(tiles) + 1) // 2)))
for i, im in enumerate(tiles):
    sheet.paste(im, ((i % 2) * w, (i // 2) * h))
dest = HERE / "out" / "check" / f"{num}_moments.jpg"
sheet.save(dest, quality=82)
print(dest)
