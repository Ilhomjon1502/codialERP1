"""ERP -> sayt: «Sayt» manbali kiruvchi lid holati o'zgarsa, saytning admin paneli «Arizalar» bo'limiga xabar beriladi (2026-11-11).

Saytga FAQAT shu bitta ariza haqida ketadi: ariza ID'si (`site:<id>`), holat va xodim yozgan izoh. ERP bazasiga sayt hech qachon murojaat
qilmaydi (u faqat so'rov qabul qiladi). So'rov HMAC-SHA256 imzo (`SITE_SYNC_KEY`) va vaqt belgisi bilan himoyalangan, javobsiz fon oqimida
yuboriladi (ERP so'rovi sayt ishlamasa ham sekinlashmaydi). `SITE_SYNC_URL` yoki `SITE_SYNC_KEY` bo'sh bo'lsa — hech narsa yuborilmaydi.
"""

import hashlib
import hmac
import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

EXTERNAL_ID = re.compile(r"^site:\d{1,12}$")
ATTEMPTS = (0, 2, 10)  # urinishlar orasidagi kutish (soniya)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # kalitli so'rov boshqa manzilga yo'naltirilmasin
        return None


def sign(key, timestamp, body):
    return hmac.new(key.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def _post(url, key, payload):
    body = json.dumps(payload, ensure_ascii=False).encode()
    for wait in ATTEMPTS:
        if wait:
            time.sleep(wait)
        ts = str(int(time.time()))
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Content-Type": "application/json", "X-Sync-Timestamp": ts, "X-Sync-Signature": sign(key, ts, body),
            "User-Agent": "codial-erp-sync/1"})
        try:
            with urllib.request.build_opener(_NoRedirect).open(req, timeout=8) as res:
                if 200 <= res.status < 300:
                    return True
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500 and e.code != 429:
                logger.warning("site_sync: sayt rad etdi (%s) %s", e.code, payload.get("id"))
                return False
        except Exception as e:  # noqa: BLE001 — tarmoq xatosi: qayta uriniladi
            logger.warning("site_sync: ulanib bo'lmadi: %s", e)
    return False


def _send(payload):
    url, key = getattr(settings, "SITE_SYNC_URL", ""), getattr(settings, "SITE_SYNC_KEY", "")
    if url and key:
        threading.Thread(target=_post, args=(url, key, payload), daemon=True).start()


def notify(item, note=""):
    """Saytdan kelgan lid holati o'zgarganda (tranzaksiya saqlangach) saytga xabar beradi."""
    ext = item.external_id or ""
    if not EXTERNAL_ID.match(ext):
        return
    payload = {"id": ext, "status": item.status, "note": (note or "")[:500]}
    transaction.on_commit(lambda: _send(payload))
