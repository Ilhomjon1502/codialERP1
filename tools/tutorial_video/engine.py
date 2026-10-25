"""Yo'riqnoma videolarini yozib olish dvigateli.

Brauzer (Playwright, headless Chromium) lokal nusxa tizimni boshqaradi, ekran CDP screencast orqali
30 kadr/s bilan ffmpeg'ga yoziladi. Har bir «say» qadamida o'zbekcha ovoz (edge-tts, uz-UZ-MadinaNeural)
va pastda izoh yozuvi chiqadi; ovozlar keyin vaqt jadvali bo'yicha bitta audio yo'lakka qo'yiladi.
"""
import asyncio
import base64
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import time
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TTS_DIR = OUT / "tts"
RAW_DIR = OUT / "raw"
FINAL_DIR = HERE.parents[1] / "docs" / "video"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

BASE_URL = os.environ.get("TV_BASE_URL", "http://erp.localhost:8010")
COPY_DIR = Path(os.environ["TV_COPY_DIR"])  # nusxa baza papkasi (scratchpad)
VOICE = "uz-UZ-MadinaNeural"
RATE = "-4%"
VIEW_W, VIEW_H, DPR = 1280, 720, 1.5  # 1920x1080 kadr
FPS = 30
SAMPLE_RATE = 24000

# Ovoz uchun talaffuz: faqat TTS ga boradi, ekrandagi yozuv o'zgarmaydi
SPEAK = [
    (r"\bSMS\b", "es-em-es"),
    (r"\bERP\b", "e-er-pe"),
    (r"\bPDF\b", "pe-de-ef"),
    (r"\bExcel\b", "eksel"),
    (r"\bTelegram\b", "telegram"),
    (r"\bID\b", "ay-di"),
    (r"№", "raqam "),
    (r"\+", " plyus "),
    (r"→|➡️|›", ", "),
    (r"«|»|\"", ""),
]


def speak_text(text):
    t = text
    for pat, rep in SPEAK:
        t = re.sub(pat, rep, t)
    t = re.sub(r"(?<=[OoGg])['’`]", "ʻ", t)  # o' g' → oʻ gʻ
    t = re.sub(r"(?<=\w)['’`](?=\w)", "ʼ", t)  # tutuq belgisi: ta'lim → taʼlim
    return re.sub(r"\s+", " ", t).strip()


def media_duration(path):
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True, errors="ignore")
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


async def tts(text):
    """Matn → mp3 (keshlanadi). Qaytaradi: (yo'l, davomiylik)."""
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    spoken = speak_text(text)
    key = hashlib.sha1(f"{VOICE}|{RATE}|{spoken}".encode()).hexdigest()[:16]
    path = TTS_DIR / f"{key}.mp3"
    if not path.exists() or path.stat().st_size < 1000:
        for attempt in range(4):
            try:
                await asyncio.wait_for(edge_tts.Communicate(spoken, VOICE, rate=RATE).save(str(path)), 40)  # osilib qolmasin
                break
            except Exception:  # tarmoq uzilishi — qayta urinish
                if attempt == 3:
                    raise
                await asyncio.sleep(2 + attempt * 2)
    return path, media_duration(path)


def restore_copy():
    """Nusxa bazani boshlang'ich holatga qaytaradi (server ishlab turganda ham — sqlite backup API)."""
    src = sqlite3.connect(COPY_DIR / "pristine.sqlite3")
    dst = sqlite3.connect(COPY_DIR / "copy.sqlite3")
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


class Lesson:
    """Bitta video. Ssenariy funksiyasi shu obyekt metodlarini chaqiradi."""

    def __init__(self, num, slug, title, dry=False, fast=False):
        """dry — faqat ovozlarni tayyorlash; fast — tezkor sinov: brauzerda amallar bajariladi, ovoz/kutish/yozish yo'q."""
        self.num, self.slug, self.title, self.dry, self.fast = num, slug, title, dry, fast
        self.timeline = []  # (boshlanish, tugash, matn, mp3)
        self.page = None
        self.t0 = None
        self.latest = None
        self.frames = 0
        self.ff = None
        self.stop_flag = False
        self.texts = []

    # ------------------------------------------------------------------ yozib olish
    async def run(self, script, login=True, on_camera_login=False, fresh=True, start=None):
        if self.dry:
            await script(self)
            return
        if fresh:
            restore_copy()
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none", "--lang=ru-RU"])
            ctx = await browser.new_context(viewport={"width": VIEW_W, "height": VIEW_H}, device_scale_factor=DPR,
                                            locale="ru-RU", timezone_id="Asia/Tashkent")  # sana maydonlari 23.10.2026 18:00 ko'rinishida
            await ctx.add_init_script(path=str(HERE / "overlay.js"))
            await ctx.add_init_script("try{localStorage.setItem('sideCollapsed','0')}catch(e){}")
            self.page = page = await ctx.new_page()
            await page.goto(BASE_URL + "/")
            await page.wait_for_selector("#lg-email, .layout", timeout=20000)
            if login and not on_camera_login:
                await self._login_quick()
            if start:
                await page.evaluate("h => location.hash = h", start(self) if callable(start) else start)
                await asyncio.sleep(1.5)
            raw = RAW_DIR / f"{self.num}.mp4"
            if self.fast:
                try:
                    await script(self)
                    print(f"{self.num}: sinov o'tdi")
                finally:
                    await page.screenshot(path=str(OUT / "check" / f"{self.num}_fast_end.png"))
                    await browser.close()
                return
            await self._start_capture(raw)
            try:
                await script(self)
                await asyncio.sleep(1.0)
            finally:
                await self._stop_capture()
                await browser.close()
        (RAW_DIR / f"{self.num}.json").write_text(json.dumps(self.timeline, ensure_ascii=False, indent=1), encoding="utf-8")
        self.assemble(raw)

    async def _login_quick(self):
        cred = json.loads((COPY_DIR / "video_login.json").read_text(encoding="utf-8"))
        p = self.page
        if await p.locator("#lg-email").count():
            await p.fill("#lg-email", cred["email"])
            await p.fill("#lg-pass", cred["password"])
            await p.click("#lg-btn")
        await p.wait_for_selector(".layout", timeout=20000)
        await p.wait_for_selector("#view .page-head", timeout=20000)
        await asyncio.sleep(1.2)

    @staticmethod
    def today():
        return time.strftime("%Y-%m-%d")

    def credentials(self):
        return json.loads((COPY_DIR / "video_login.json").read_text(encoding="utf-8"))

    async def _start_capture(self, raw):
        self.ff = await asyncio.create_subprocess_exec(
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
            "-vf", f"scale={int(VIEW_W * DPR)}:{int(VIEW_H * DPR)}:flags=lanczos,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "stillimage", str(raw),
            stdin=asyncio.subprocess.PIPE)
        self.cdp = await self.page.context.new_cdp_session(self.page)
        first = asyncio.Event()

        def on_frame(ev):
            self.latest = base64.b64decode(ev["data"])
            first.set()
            asyncio.ensure_future(self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]}))

        self.cdp.on("Page.screencastFrame", on_frame)
        await self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": int(VIEW_W * DPR),
                                                    "maxHeight": int(VIEW_H * DPR), "everyNthFrame": 1})
        # sahifa jim bo'lsa ham birinchi kadr kelsin
        await self.page.evaluate("document.body.style.outline='0px solid transparent'")
        await asyncio.wait_for(first.wait(), 10)
        self.t0 = time.perf_counter()
        self.writer = asyncio.ensure_future(self._writer())

    async def _writer(self):
        while not self.stop_flag:
            due = int((time.perf_counter() - self.t0) * FPS) + 1
            if due - self.frames > FPS * 1.5:
                # Jarayon to'xtab qolgan (kompyuter uyquga ketgan va h.k.): o'tgan vaqt videoga qotgan kadr bo'lib
                # tushmasin — soat suriladi, ovoz jadvali (now()) ham shunga moslashadi
                self.t0 += (due - self.frames - 1) / FPS
                due = self.frames + 1
            while self.frames < due:
                self.ff.stdin.write(self.latest)
                self.frames += 1
            await self.ff.stdin.drain()
            await asyncio.sleep(1 / (FPS * 2))

    async def _stop_capture(self):
        self.stop_flag = True
        await self.writer
        try:
            await self.cdp.send("Page.stopScreencast")
        except Exception:
            pass
        self.ff.stdin.close()
        await self.ff.wait()

    def now(self):
        return time.perf_counter() - self.t0

    # ------------------------------------------------------------------ yig'ish
    def assemble(self, raw):
        dur = media_duration(raw)
        n = int(dur * SAMPLE_RATE) + SAMPLE_RATE
        buf = bytearray(n * 2)
        for start, _end, _text, mp3 in self.timeline:
            pcm = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", mp3, "-f", "s16le", "-ac", "1",
                                  "-ar", str(SAMPLE_RATE), "-"], capture_output=True).stdout
            off = int(start * SAMPLE_RATE) * 2
            buf[off:off + len(pcm)] = pcm[: max(0, len(buf) - off)]
        wav = RAW_DIR / f"{self.num}.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(bytes(buf))
        FINAL_DIR.mkdir(parents=True, exist_ok=True)
        name = f"{self.num}_{self.slug}"
        out = FINAL_DIR / f"{name}.mp4"
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw), "-i", str(wav),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-shortest", "-movflags", "+faststart",
                        "-metadata", f"title={self.num}. {self.title}", str(out)], check=True)
        srt = []
        for i, (s, e, text, _mp3) in enumerate(self.timeline, 1):
            srt.append(f"{i}\n{_ts(s)} --> {_ts(e)}\n{text}\n")
        (FINAL_DIR / f"{name}.srt").write_text("\n".join(srt), encoding="utf-8")
        print(f"tayyor: {out} ({media_duration(out):.0f} s)")

    # ------------------------------------------------------------------ ssenariy amallari
    async def say(self, text, *acts, pause=0.45, keep=False):
        """Ovoz + izoh yozuvi; amallar shu vaqtda ketma-ket bajariladi. Ikkalasi tugagach davom etadi."""
        self.texts.append(text)
        if self.fast:
            for a in acts:
                await a
            return
        mp3, dur = await tts(text)
        if self.dry:
            for a in acts:
                a.close()
            return
        start = self.now()
        await self.page.evaluate("t => __tv.caption(t)", text)
        self.timeline.append([round(start, 3), round(start + dur, 3), text, str(mp3)])
        for a in acts:
            await a
        rest = start + dur - self.now()
        if rest > 0:
            await asyncio.sleep(rest)
        if not keep:
            await self.page.evaluate("() => __tv.caption('')")
        await asyncio.sleep(pause)

    async def card(self, kick, title, sub=None, items=None, text=None, hold=0.8):
        """Sarlavha kartochkasi (dars boshi/oxiri)."""
        if self.dry or self.fast:
            if text:
                await self.say(text)
            return
        await self.page.evaluate("o => __tv.card(o)", {"kick": kick, "title": title, "sub": sub, "items": items})
        await asyncio.sleep(0.6)
        if text:
            await self.say(text, pause=0)
        await asyncio.sleep(hold + (len(items or []) * 0.26 if not text else 0))

    async def uncard(self):
        if not self.dry:
            await self.page.evaluate("() => __tv.card(null)")
            await asyncio.sleep(0.6)

    async def keynote(self, title, small=None, text=None):
        if self.dry or self.fast:
            if text:
                await self.say(text)
            return
        await self.page.evaluate("([t,s]) => __tv.keynote(t,s)", [title, small])
        if text:
            await self.say(text, pause=0.2)
        else:
            await asyncio.sleep(2.5)
        await self.page.evaluate("() => __tv.keynote('')")
        await asyncio.sleep(0.4)

    def loc(self, sel):
        return self.page.locator(sel).first

    async def _rect(self, sel, scroll=True):
        loc = self.loc(sel)
        await loc.wait_for(state="visible", timeout=15000)
        if scroll:
            # Ko'rinib turibdimi va ustida boshqa element (masalan, modal pastki qatori) yo'qmi
            inview = await loc.evaluate("""el => { const r = el.getBoundingClientRect();
                if (r.top < 60 || r.bottom > innerHeight - 20) return false;
                const t = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return !!t && (t === el || el.contains(t) || t.contains(el)); }""")
            if not inview:
                await loc.evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'center'})")
                await asyncio.sleep(0.7)
        b = await loc.bounding_box()
        return {"x": b["x"], "y": b["y"], "w": b["width"], "h": b["height"]}

    async def move_to(self, r, fx=0.5, fy=0.5):
        x, y = r["x"] + r["w"] * fx, r["y"] + r["h"] * fy
        await self.page.evaluate("([x,y]) => __tv.move(x,y)", [x, y])
        await self.page.mouse.move(x, y, steps=8)
        await asyncio.sleep(0.8)
        return x, y

    async def point(self, sel, label=None, side=None, pad=6, soft=False, cursor=True, hold=0.0):
        if self.dry:
            return
        r = await self._rect(sel)
        await self.page.evaluate("([r,l,o]) => { __tv.highlight(r,l,o); __tv.capAvoid(r); }",
                                 [r, label, {"side": side, "pad": pad, "soft": soft}])
        if cursor:
            await self.move_to(r)
        await asyncio.sleep(hold)
        return r

    async def show(self, sel, label=None, side=None, pad=6, hold=0.0):
        """Faqat yoritish (kursor joyida qoladi)."""
        return await self.point(sel, label, side=side, pad=pad, cursor=False, hold=hold)

    async def clear(self):
        if not self.dry:
            await self.page.evaluate("() => __tv.clear()")

    async def click(self, sel, label=None, side=None, pad=6, wait=0.6, keep=False, fx=0.5, fy=0.5):
        if self.dry:
            return
        r = await self._rect(sel)
        await self.page.evaluate("([r,l,o]) => { __tv.highlight(r,l,o); __tv.capAvoid(r); }",
                                 [r, label, {"side": side, "pad": pad}])
        x, y = await self.move_to(r, fx, fy)
        await asyncio.sleep(0.35)
        await self.page.evaluate("([x,y]) => __tv.ripple(x,y)", [x, y])
        if not keep:
            await self.clear()
        await self.page.mouse.click(x, y)
        await asyncio.sleep(wait)

    async def click_xy(self, pt, label=None, wait=0.6):
        """Ekrandagi nuqtani bosish (pt = {x, y}, masalan jadvaldagi bo'sh joy)."""
        if self.dry or not pt:
            return
        r = {"x": pt["x"] - 36, "y": pt["y"] - 22, "w": 72, "h": 44}
        await self.page.evaluate("([r,l]) => { __tv.highlight(r,l,{side:'below'}); __tv.capAvoid(r); }", [r, label])
        x, y = await self.move_to(r)
        await asyncio.sleep(0.35)
        await self.page.evaluate("([x,y]) => __tv.ripple(x,y)", [x, y])
        await self.clear()
        await self.page.mouse.click(x, y)
        await asyncio.sleep(wait)

    async def type(self, sel, text, label=None, delay=75, clear=True, side=None):
        if self.dry:
            return
        await self.click(sel, label, side=side, wait=0.2, keep=True)
        await self.loc(sel).evaluate("el => { el.dataset.tvTyped = '1'; }")  # video uchun yozilgan qiymat yashirilmaydi
        if clear:
            await self.loc(sel).fill("")
        await self.loc(sel).press_sequentially(str(text), delay=delay)
        await asyncio.sleep(0.4)
        await self.clear()

    async def fill(self, sel, value, label=None, side=None):
        """Sana/vaqt kabi maydonlar: bir yo'la qiymat beriladi."""
        if self.dry:
            return
        await self.click(sel, label, side=side, wait=0.2, keep=True)
        await self.loc(sel).fill(str(value))
        await self.loc(sel).dispatch_event("change")
        await asyncio.sleep(0.6)
        await self.clear()

    async def choose(self, sel, value=None, text=None, label=None, side=None):
        """Ochiladigan ro'yxatdan tanlash: soxta ro'yxat chiziladi, kursor variantga boradi."""
        if self.dry:
            return
        loc = self.loc(sel)
        r = await self._rect(sel)
        if value is None:
            value = await loc.evaluate("(s,t) => { const o = [...s.options].find(o => o.value && o.textContent.includes(t)); return o ? o.value : null; }", text)
            if value is None:
                raise RuntimeError(f"Variant topilmadi: {text} ({sel})")
        await self.page.evaluate("([r,l,o]) => { __tv.highlight(r,l,o); __tv.capAvoid(r); }", [r, label, {"side": side}])
        x, y = await self.move_to(r)
        await asyncio.sleep(0.25)
        await self.page.evaluate("([x,y]) => __tv.ripple(x,y)", [x, y])
        await self.page.evaluate("() => __tv.highlight(null)")
        ir = await loc.evaluate("(s, v) => __tv.dropdown(s, v)", value)
        await asyncio.sleep(0.5)
        if ir:
            x, y = await self.move_to(ir, 0.3)
            await self.page.evaluate("([x,y,v]) => { __tv.ripple(x,y); __tv.ddPick(v); }", [x, y, value])
            await asyncio.sleep(0.45)
        await self.page.evaluate("() => __tv.ddHide()")
        await loc.select_option(value)
        await asyncio.sleep(0.5)

    async def seg(self, field, value, label=None, side=None):
        await self.click(f'[data-f="{field}"] button[data-val="{value}"]', label, side=side)

    async def scroll(self, sel=None, dy=None, wait=0.9):
        if self.dry:
            return
        if sel:
            await self.loc(sel).evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'start'})")
        else:
            await self.page.evaluate("dy => { const m = document.querySelector('.overlay:last-child .modal-body'); (m || window).scrollBy({top: dy, behavior: 'smooth'}); }", dy)
        await asyncio.sleep(wait)

    async def wait(self, s):
        if not self.dry:
            await asyncio.sleep(s)

    async def goto(self, hash_path, wait_sel="#view .page-head"):
        if self.dry:
            return
        await self.page.evaluate("h => location.hash = '#/' + h", hash_path)
        await self.page.wait_for_selector(wait_sel, timeout=20000)
        await asyncio.sleep(0.8)

    async def nav(self, section, label=None):
        """Chap menyudan bo'lim tanlash."""
        await self.click(f'#nav a[data-nav="{section}"]', label)
        if not self.dry:
            await self.page.wait_for_selector("#view .page-head", timeout=20000)
            await asyncio.sleep(0.6)

    async def js(self, expr, arg=None):
        if self.dry:
            return None
        return await self.page.evaluate(expr, arg)

    async def wait_for(self, sel, timeout=15000):
        if not self.dry:
            await self.page.wait_for_selector(sel, timeout=timeout)
            await asyncio.sleep(0.3)

    async def close_modal(self, label=None):
        await self.click(".overlay:last-child .modal-head [data-close]", label)

    async def show_pdf(self, title=None, url=None, hold=0.0):
        """Oxirgi ochilgan PDF'ni (masalan, to'lov cheki) rasmga aylantirib ekran ustida ko'rsatadi."""
        if self.dry:
            return
        import pypdfium2
        for _ in range(30):
            url = url or await self.page.evaluate("window.__tvOpened || null")
            if url:
                break
            await asyncio.sleep(0.2)
        resp = await self.page.request.get(BASE_URL + url if url.startswith("/") else url)
        pdf = pypdfium2.PdfDocument(await resp.body())
        img = pdf[0].render(scale=2.2).to_pil()
        import io
        buf = io.BytesIO()
        img.save(buf, "PNG")
        src = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        await self.page.evaluate("([s,t]) => __tv.image(s,t)", [src, title])
        await self.page.evaluate("() => { window.__tvOpened = null; }")
        await asyncio.sleep(0.5 + hold)

    async def hide_image(self):
        if not self.dry:
            await self.page.evaluate("() => __tv.image(null)")
            await asyncio.sleep(0.4)

    async def exists(self, sel):
        if self.dry:
            return True
        return await self.page.locator(sel).count() > 0


def _ts(s):
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h):02}:{int(m):02}:{int(sec):02},{int(round((sec % 1) * 1000)):03}"
