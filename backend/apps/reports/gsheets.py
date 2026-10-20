"""Google Sheets REST API — service account bilan (tashqi SDK'siz: urllib + cryptography).
Kalit va fayl ID'si `.env` da (deploy/set-google.sh); kod ularni faqat sozlamalardan oladi."""

import base64
import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings

log = logging.getLogger(__name__)

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://sheets.googleapis.com/v4/spreadsheets"
TIMEOUT = 25


class SheetsError(Exception):
    """Foydalanuvchiga ko'rsatiladigan o'zbekcha xabar."""


def configured():
    return bool(settings.GOOGLE_SERVICE_ACCOUNT_B64 and settings.GOOGLE_SHEET_ID)


def credentials():
    raw = settings.GOOGLE_SERVICE_ACCOUNT_B64
    if not raw:
        raise SheetsError("Google Sheets ulanmagan: administrator serverda `bash deploy/set-google.sh` ni ishga tushirishi kerak")
    try:
        info = json.loads(base64.b64decode(raw))
        info["client_email"], info["private_key"]  # noqa: B018 — mavjudligini tekshirish
    except (ValueError, KeyError, TypeError) as e:
        raise SheetsError("Google kalit fayli buzilgan: `deploy/set-google.sh` ni qayta ishga tushiring") from e
    return info


def service_email():
    return credentials()["client_email"]


def sheet_id():
    if not settings.GOOGLE_SHEET_ID:
        raise SheetsError("Google Sheets fayl ID'si kiritilmagan: `deploy/set-google.sh` ni ishga tushiring")
    return settings.GOOGLE_SHEET_ID


def sheet_url(gid=None):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id()}/edit" + (f"#gid={gid}" if gid is not None else "")


# ------------------------------------------------------------------ HTTP

def _http(method, url, body=None, headers=None, raw=False):
    data = body if raw else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 — faqat https://*.googleapis.com
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw_err = e.read().decode("utf-8", "replace")
        log.warning("Google API %s %s -> %s %s", method, url.split("?")[0], e.code, raw_err[:500])
        raise SheetsError(_human(e.code, raw_err)) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SheetsError("Google bilan aloqa o'rnatilmadi, birozdan keyin qayta urinib ko'ring") from e


def _human(code, raw):
    try:
        msg = json.loads(raw).get("error", {})
        msg = msg.get("message", "") if isinstance(msg, dict) else str(msg)
    except ValueError:
        msg = raw[:200]
    low = msg.lower()
    if "has not been used" in low or "is disabled" in low:
        return "Google Cloud'da «Google Sheets API» yoqilmagan (APIs & Services → Library → Google Sheets API → Enable)"
    if code == 403:
        try:
            who = service_email()
        except SheetsError:
            who = "service account"
        return f"Google faylga ruxsat yo'q: faylni {who} pochtasiga «Editor» qilib ulashing"
    if code == 404:
        return "Google Sheets fayl topilmadi: fayl ID'sini tekshiring (`deploy/set-google.sh`)"
    if code in (400, 401) and "invalid_grant" in low:
        return "Google kalit yaroqsiz (o'chirilgan yoki soat noto'g'ri): yangi kalit yaratib `deploy/set-google.sh` ni ishga tushiring"
    return f"Google Sheets xatosi ({code}): {msg[:200]}"


# ------------------------------------------------------------------ token

_lock = threading.Lock()
_token = {"value": None, "exp": 0}


def _b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def access_token():
    with _lock:
        now = int(time.time())
        if _token["value"] and _token["exp"] - 60 > now:
            return _token["value"]
        info = credentials()
        head = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        claim = _b64url(json.dumps({"iss": info["client_email"], "scope": SCOPE, "aud": TOKEN_URL, "iat": now, "exp": now + 3600}).encode())
        try:
            key = serialization.load_pem_private_key(info["private_key"].encode(), password=None)
            sig = key.sign(f"{head}.{claim}".encode(), padding.PKCS1v15(), hashes.SHA256())
        except (ValueError, TypeError) as e:
            raise SheetsError("Google kalit fayli buzilgan: `deploy/set-google.sh` ni qayta ishga tushiring") from e
        form = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": f"{head}.{claim}.{_b64url(sig)}"}).encode()
        r = _http("POST", TOKEN_URL, form, {"Content-Type": "application/x-www-form-urlencoded"}, raw=True)
        _token.update(value=r["access_token"], exp=now + int(r.get("expires_in", 3600)))
        return _token["value"]


def _call(method, path="", body=None, params=None):
    url = f"{API}/{sheet_id()}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    return _http(method, url, body, {"Authorization": f"Bearer {access_token()}", "Content-Type": "application/json"})


# ------------------------------------------------------------------ amallar

def tabs():
    """[{sheetId, title}] — fayldagi varaqlar."""
    r = _call("GET", params={"fields": "properties.title,sheets.properties(sheetId,title,gridProperties)"})
    return {"title": r["properties"]["title"], "sheets": [s["properties"] for s in r.get("sheets", [])]}


def batch_update(requests):
    return _call("POST", ":batchUpdate", {"requests": requests})


def values_get(ranges):
    """[[...], ...] har bir diapazon uchun (UNFORMATTED_VALUE)."""
    r = _call("GET", "/values:batchGet", params={"ranges": ranges, "valueRenderOption": "UNFORMATTED_VALUE"})
    return [vr.get("values", []) for vr in r.get("valueRanges", [])]


def values_update(data):
    """data = [{range: "'oktabr 2026'!C5", values: [[...]]}] — formulalar ham (USER_ENTERED)."""
    return _call("POST", "/values:batchUpdate", {"valueInputOption": "USER_ENTERED", "data": data})
