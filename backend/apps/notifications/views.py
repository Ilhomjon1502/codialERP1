from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import EVENT_KEYS, EVENTS, TelegramLink, new_code


def _payload(link):
    bot = settings.TELEGRAM_BOT_USERNAME
    return {
        "configured": bool(settings.TELEGRAM_BOT_TOKEN),
        "bot": bot,
        "linked": bool(link.chat_id),
        "username": link.username,
        "linked_at": link.linked_at,
        "code": link.code,
        "url": f"https://t.me/{bot}?start={link.code}" if bot else "",
        "events": [{"key": k, "label": label, "on": link.wants(k)} for k, label in EVENTS],
    }


@api_view(["GET", "PATCH", "DELETE"])
def me(request):
    """Joriy xodimning Telegram bog'lanishi: GET — holat va bog'lash kodi; PATCH {prefs: {event: bool}} yoki {new_code: true}; DELETE — uzish."""
    link, _ = TelegramLink.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        prefs = request.data.get("prefs")
        if prefs is not None:
            if not isinstance(prefs, dict) or any(k not in EVENT_KEYS for k in prefs):
                raise ValidationError({"prefs": "Noma'lum xabar turi"})
            link.prefs = {**link.prefs, **{k: bool(v) for k, v in prefs.items()}}
        if request.data.get("new_code"):
            link.code = new_code()
        link.save()
    elif request.method == "DELETE":
        link.chat_id, link.linked_at, link.username = None, None, ""
        link.save()
    return Response(_payload(link))
