"""LLM provayderlari (CLAUDE.md 13): AI_PROVIDER=gemini|anthropic|openai. Hammasi bitta `complete(system, user) -> str` (JSON matn).
Kalit faqat `deploy/.env` da (AI_API_KEY), so'rov URL'iga qo'shilmaydi — sarlavhada yuboriladi."""

import json
import threading
import time
import urllib.error
import urllib.request

from django.conf import settings

DEFAULT_MODELS = {"gemini": "gemini-3.7-flash", "anthropic": "claude-sonnet-5-5", "openai": "gpt-4.1-mini"}
DEFAULT_FALLBACKS = {"gemini": ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest"]}


class ProviderError(Exception):
    pass


def configured():
    return bool(settings.AI_API_KEY) and settings.AI_PROVIDER in DEFAULT_MODELS


def model_name():
    return settings.AI_MODEL or DEFAULT_MODELS.get(settings.AI_PROVIDER, "")


def model_chain():
    """Asosiy model + zaxira modellar (AI_MODEL_FALLBACKS): asosiysi band yoki yopilgan bo'lsa navbatdagisi ishlatiladi."""
    fallbacks = settings.AI_MODEL_FALLBACKS if settings.AI_MODEL_FALLBACKS is not None else DEFAULT_FALLBACKS.get(settings.AI_PROVIDER, [])
    out = []
    for m in [model_name(), *fallbacks]:
        if m and m not in out:
            out.append(m)
    return out


class Unavailable(ProviderError):
    """Model band (5xx), javob kechikdi yoki model yopilgan (404) — keyingi modelni sinash mumkin."""


_state = threading.local()


def used_model():
    return getattr(_state, "model", "") or model_name()


BUSY = (500, 502, 503, 504)


def _post(url, headers, body, retries=1):
    """5xx bo'lsa — 2 soniyadan keyin bir marta qayta urinadi, keyin Unavailable."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=settings.AI_HTTP_TIMEOUT_S) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code in BUSY and attempt < retries:
                time.sleep(2)
                continue
            if e.code in BUSY:
                raise Unavailable("AI xizmati hozir band (Google serverlari). Bir-ikki daqiqadan keyin qayta urinib ko'ring") from None
            if e.code == 404:
                raise Unavailable("AI modeli mavjud emas. Serverda deploy/set-ai.sh ni qayta ishga tushiring yoki .env dagi AI_MODEL ni yangilang") from None
            if e.code == 429:
                raise ProviderError("AI xizmati limiti tugadi (429). Birozdan keyin qayta urinib ko'ring") from None
            if e.code in (401, 403):
                raise ProviderError("AI kaliti qabul qilinmadi. Serverda deploy/set-ai.sh bilan kalitni qayta kiriting") from None
            raise ProviderError(f"AI xizmati xatosi {e.code}: {detail}") from None
        except TimeoutError:
            raise Unavailable(f"AI {settings.AI_HTTP_TIMEOUT_S:g} soniyada javob bermadi") from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise Unavailable(f"AI {settings.AI_HTTP_TIMEOUT_S:g} soniyada javob bermadi") from None
            raise ProviderError(f"AI xizmatiga ulanib bo'lmadi: {e.reason}") from None


def _gemini(system, user, model, thinking=True):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    config = {"temperature": 0, "responseMimeType": "application/json"}
    if settings.AI_THINKING and thinking:
        config["thinkingConfig"] = {"thinkingLevel": settings.AI_THINKING}  # «low» — SQL uchun yetarli va 3–4 barobar tez
    try:
        data = _post(url, {"x-goog-api-key": settings.AI_API_KEY}, {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": config,
        })
    except ProviderError as e:
        if thinking and "thinkingConfig" in config and " 400:" in str(e):  # model bu sozlamani qo'llamasa — sozlamasiz
            return _gemini(system, user, model, thinking=False)
        raise
    try:
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"] if not p.get("thought"))
    except (KeyError, IndexError):
        raise ProviderError("AI javob bermadi (bo'sh javob)") from None


def _anthropic(system, user, model):
    data = _post("https://api.anthropic.com/v1/messages", {"x-api-key": settings.AI_API_KEY, "anthropic-version": "2023-06-01"}, {
        "model": model, "max_tokens": 2000, "temperature": 0, "system": system,
        "messages": [{"role": "user", "content": user}],
    })
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _openai(system, user, model):
    data = _post("https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {settings.AI_API_KEY}"}, {
        "model": model, "temperature": 0, "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    })
    return data["choices"][0]["message"]["content"]


PROVIDERS = {"gemini": _gemini, "anthropic": _anthropic, "openai": _openai}


def complete(system, user):
    if not configured():
        raise ProviderError("AI yordamchi hali sozlanmagan: serverda deploy/set-ai.sh bilan API kalitini kiriting")
    _state.model = ""
    deadline = time.monotonic() + settings.AI_TOTAL_TIMEOUT_S
    err = None
    for model in model_chain():
        if err and time.monotonic() + 5 > deadline:  # sahifa kutib qolmasin (gunicorn 60 s)
            break
        try:
            text = PROVIDERS[settings.AI_PROVIDER](system, user, model)
            _state.model = model
            return text
        except Unavailable as e:
            err = e
    raise err


def complete_json(system, user):
    text = complete(system, user).strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        return json.loads(text[start:end])
    except ValueError:
        raise ProviderError("AI javobi JSON emas") from None
