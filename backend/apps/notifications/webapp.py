"""Telegram Mini App (buyurtmachi so'rovi 2026-10-14): ustoz botdagi tugma orqali davomat sahifasini Telegram ichida ochadi.

Kirish parolsiz: Telegram Mini App'ga `initData` beradi — uni bot tokeni bilan imzolangan (HMAC-SHA256).
Server imzoni tekshiradi (https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app),
so'ng shu Telegram foydalanuvchisi bog'lagan faol xodim akkauntiga kiritadi. Bog'lanmagan bo'lsa — kirish yo'q."""

import hashlib
import hmac
import json
import time
import urllib.parse

from django.conf import settings

MAX_AGE = 24 * 3600  # initData shu muddatdan eski bo'lsa qabul qilinmaydi


class InvalidInitData(Exception):
    pass


def validate(init_data, token=None, max_age=MAX_AGE, now=None):
    """initData (query-string) → Telegram foydalanuvchisi (dict). Imzo yoki muddat noto'g'ri bo'lsa — InvalidInitData."""
    token = token or settings.TELEGRAM_BOT_TOKEN
    if not token or not init_data:
        raise InvalidInitData("Telegram ma'lumoti yo'q")
    pairs = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    got = pairs.pop("hash", "")
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    want = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not got or not hmac.compare_digest(got, want):
        raise InvalidInitData("Telegram imzosi noto'g'ri")
    try:
        age = (now or time.time()) - int(pairs.get("auth_date", "0"))
    except ValueError:
        age = max_age + 1
    if age > max_age:
        raise InvalidInitData("Telegram ma'lumoti eskirgan — ilovani qayta oching")
    try:
        user = json.loads(pairs.get("user", "{}"))
    except ValueError:
        user = {}
    if not user.get("id"):
        raise InvalidInitData("Telegram foydalanuvchisi aniqlanmadi")
    return user


def url(page="attendance", **params):
    """Mini App manzili. Telegram o'z parametrlarini URL # qismiga qo'shadi, shuning uchun sahifa ?tg= bilan beriladi."""
    q = urllib.parse.urlencode({"tg": page, **{k: v for k, v in params.items() if v}})
    return f"{settings.FRONTEND_URL.rstrip('/')}/?{q}"


def enabled():
    """Mini App faqat HTTPS manzilda ishlaydi (Telegram talabi)."""
    return bool(settings.TELEGRAM_BOT_TOKEN) and settings.FRONTEND_URL.startswith("https://")


def button(text, page="attendance", **params):
    return {"inline_keyboard": [[{"text": text, "web_app": {"url": url(page, **params)}}]]}
