"""LLM provayderlari (CLAUDE.md 13): AI_PROVIDER=gemini|anthropic|openai. Hammasi bitta `complete(system, user) -> str` (JSON matn).
Kalit faqat `deploy/.env` da (AI_API_KEY), so'rov URL'iga qo'shilmaydi — sarlavhada yuboriladi."""

import json
import time
import urllib.error
import urllib.request

from django.conf import settings

DEFAULT_MODELS = {"gemini": "gemini-3.8-flash", "anthropic": "claude-sonnet-5-5", "openai": "gpt-4.1-mini"}


class ProviderError(Exception):
    pass


def configured():
    return bool(settings.AI_API_KEY) and settings.AI_PROVIDER in DEFAULT_MODELS


def model_name():
    return settings.AI_MODEL or DEFAULT_MODELS.get(settings.AI_PROVIDER, "")


BUSY = (500, 502, 503, 504)


def _post(url, headers, body, retries=2):
    """Provayder vaqtincha band bo'lsa (5xx) — 2 va 4 soniyadan keyin qayta urinadi."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=settings.AI_HTTP_TIMEOUT_S) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code in BUSY and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            if e.code in BUSY:
                raise ProviderError("AI xizmati hozir band (Google serverlari). Bir-ikki daqiqadan keyin qayta urinib ko'ring") from None
            if e.code == 429:
                raise ProviderError("AI xizmati limiti tugadi (429). Birozdan keyin qayta urinib ko'ring") from None
            if e.code in (401, 403):
                raise ProviderError("AI kaliti qabul qilinmadi. Serverda deploy/set-ai.sh bilan kalitni qayta kiriting") from None
            if e.code == 404:
                raise ProviderError(f"AI modeli ({model_name()}) mavjud emas. Serverda deploy/set-ai.sh ni qayta ishga tushiring yoki .env dagi AI_MODEL ni yangilang") from None
            raise ProviderError(f"AI xizmati xatosi {e.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            raise ProviderError(f"AI xizmatiga ulanib bo'lmadi: {getattr(e, 'reason', e)}") from None


def _gemini(system, user):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name()}:generateContent"
    data = _post(url, {"x-goog-api-key": settings.AI_API_KEY}, {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    })
    try:
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        raise ProviderError("AI javob bermadi (bo'sh javob)") from None


def _anthropic(system, user):
    data = _post("https://api.anthropic.com/v1/messages", {"x-api-key": settings.AI_API_KEY, "anthropic-version": "2023-06-01"}, {
        "model": model_name(), "max_tokens": 2000, "temperature": 0, "system": system,
        "messages": [{"role": "user", "content": user}],
    })
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _openai(system, user):
    data = _post("https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {settings.AI_API_KEY}"}, {
        "model": model_name(), "temperature": 0, "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    })
    return data["choices"][0]["message"]["content"]


PROVIDERS = {"gemini": _gemini, "anthropic": _anthropic, "openai": _openai}


def complete(system, user):
    if not configured():
        raise ProviderError("AI yordamchi hali sozlanmagan: serverda deploy/set-ai.sh bilan API kalitini kiriting")
    return PROVIDERS[settings.AI_PROVIDER](system, user)


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
