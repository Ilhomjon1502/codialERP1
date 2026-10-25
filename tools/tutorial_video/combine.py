"""14 ta darsni bitta to'liq darslikka birlashtiradi (alohida videolar o'zgarmaydi).

  python combine.py
Natija (docs/video/):
  Codial_ERP_toliq_darslik.mp4  — boblar (chapter) bilan, pleyerda darsdan darsga o'tish mumkin
  Codial_ERP_toliq_darslik.srt  — barcha subtitrlar vaqti surilgan holda
  Codial_ERP_toliq_darslik_boblar.txt — YouTube tavsifi uchun vaqtlar ro'yxati
Barcha darslar bitta dvigatelda bir xil sozlama bilan yozilgani uchun qayta kodlanmaydi (-c copy).
"""
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

from engine import media_duration
from lessons import LESSONS

HERE = Path(__file__).resolve().parent
VIDEO = HERE.parents[1] / "docs" / "video"
NAME = "Codial_ERP_toliq_darslik"
FF = imageio_ffmpeg.get_ffmpeg_exe()


def ts(sec, srt=False):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if srt:
        return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)):03}"
    return f"{int(h)}:{int(m):02}:{int(s):02}" if h else f"{int(m):02}:{int(s):02}"


def srt_blocks(path):
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.strip().split("\n")
        m = re.match(r"(\S+) --> (\S+)", lines[1])
        yield m[1], m[2], "\n".join(lines[2:])


def to_sec(t):
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def main():
    parts = []
    for num in sorted(n for n in LESSONS if n != "00"):
        slug, title, _ = LESSONS[num]
        mp4 = VIDEO / f"{num}_{slug}.mp4"
        assert mp4.exists(), f"yo'q: {mp4}"
        parts.append((num, title, mp4, mp4.with_suffix(".srt")))

    lst = HERE / "out" / "concat.txt"
    lst.write_text("".join(f"file '{p[2].as_posix()}'\n" for p in parts), encoding="utf-8")

    chapters, srt, desc, offset, idx = [";FFMETADATA1", f"title=Codial ERP — Administrator+Hisobchi uchun to'liq darslik"], [], [], 0.0, 1
    for num, title, mp4, sub in parts:
        dur = media_duration(mp4)
        chapters += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(offset * 1000)}", f"END={int((offset + dur) * 1000)}",
                     f"title={int(num)}-dars. {title}"]
        desc.append(f"{ts(offset)} {int(num)}-dars. {title}")
        for a, b, text in srt_blocks(sub):
            srt.append(f"{idx}\n{ts(to_sec(a) + offset, True)} --> {ts(to_sec(b) + offset, True)}\n{text}\n")
            idx += 1
        offset += dur
    meta = HERE / "out" / "chapters.txt"
    meta.write_text("\n".join(chapters) + "\n", encoding="utf-8")

    out = VIDEO / f"{NAME}.mp4"
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-i", str(meta), "-map", "0", "-map_metadata", "1", "-map_chapters", "1", "-c", "copy",
                    "-movflags", "+faststart", str(out)], check=True)
    (VIDEO / f"{NAME}.srt").write_text("\n".join(srt), encoding="utf-8")
    (VIDEO / f"{NAME}_boblar.txt").write_text(
        "Codial ERP — Administrator+Hisobchi uchun to'liq darslik\n\n" + "\n".join(desc) + "\n", encoding="utf-8")
    print(f"tayyor: {out} ({ts(media_duration(out))}, {out.stat().st_size // 1048576} MB, {len(parts)} dars, {idx - 1} subtitr)")


if __name__ == "__main__":
    main()
