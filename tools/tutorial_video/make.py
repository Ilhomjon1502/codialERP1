"""Yo'riqnoma videolarini yasash.

  python make.py list            — darslar ro'yxati
  python make.py tts 03 05       — faqat ovozlarni oldindan tayyorlash (tez yozib olish uchun)
  python make.py rec 03 05       — yozib olish → docs/video/NN_nom.mp4 + .srt
  python make.py rec all

Muhit: TV_COPY_DIR — nusxa baza papkasi (copy.sqlite3, pristine.sqlite3, video_login.json),
lokal server: launch.json dagi «video-copy» (http://erp.localhost:8010).
"""
import asyncio
import sys

from engine import Lesson
from lessons import LESSONS


async def main(cmd, nums):
    if nums == ["all"]:
        nums = [n for n in LESSONS if n != "00"]
    for n in nums:
        slug, title, fn = LESSONS[n]
        opts = getattr(fn, "opts", {})
        if cmd == "tts":
            L = Lesson(n, slug, title, dry=True)
            await L.run(fn)
            print(f"{n}: {len(L.texts)} ta ovoz tayyor")
        elif cmd == "check":
            await Lesson(n, slug, title, fast=True).run(fn, **opts)
        elif cmd == "rec":
            await Lesson(n, slug, title, dry=True).run(fn)
            await Lesson(n, slug, title).run(fn, **opts)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "list":
        for n, (slug, title, _) in LESSONS.items():
            print(n, slug, "—", title)
    else:
        asyncio.run(main(sys.argv[1], sys.argv[2:]))
