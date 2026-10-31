from django.conf import settings
from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import me_payload
from apps.core import audit
from apps.core.models import AuditLog
from apps.core.permissions import is_top

from . import services, webapp
from .models import EVENT_KEYS, ExtraRecipient, TelegramLink, new_code


def _payload(link, user):
    bot = settings.TELEGRAM_BOT_USERNAME
    return {
        "configured": bool(settings.TELEGRAM_BOT_TOKEN),
        "bot": bot,
        "linked": bool(link.chat_id),
        "username": link.username,
        "linked_at": link.linked_at,
        "code": link.code,
        "url": f"https://t.me/{bot}?start={link.code}" if bot else "",
        "events": services.events_for(user, link),
        "extra": services.extra_payload() if is_top(user) else [],
    }


@api_view(["GET", "PATCH", "DELETE"])
def me(request):
    """Joriy xodimning Telegram bog'lanishi: GET — holat va bog'lash kodi; PATCH {prefs: {event: bool}} yoki {new_code: true}; DELETE — uzish."""
    link, _ = TelegramLink.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        prefs = request.data.get("prefs")
        if prefs is not None:
            if not isinstance(prefs, dict) or any(k not in EVENT_KEYS or not services.allowed(request.user, k) for k in prefs):
                raise ValidationError({"prefs": "Noma'lum xabar turi"})
            link.prefs = {**link.prefs, **{k: bool(v) for k, v in prefs.items()}}
        if request.data.get("new_code"):
            link.code = new_code()
        link.save()
    elif request.method == "DELETE":
        link.chat_id, link.linked_at, link.username = None, None, ""
        link.save()
    return Response(_payload(link, request.user))


@api_view(["PATCH"])
def extra(request):
    """Umumiy chat (masalan Codial admin) qaysi xabarlarni olishi: {id, events: [kalitlar]} — faqat Admin va Bosh menejer."""
    if not is_top(request.user):
        raise PermissionDenied("Umumiy chat xabarlarini faqat Admin va Bosh menejer o'zgartiradi")
    er = ExtraRecipient.objects.filter(pk=request.data.get("id")).first()
    events = request.data.get("events")
    if er is None or not isinstance(events, list) or any(k not in EVENT_KEYS for k in events):
        raise ValidationError({"events": "Noto'g'ri so'rov"})
    before = sorted(services.extra_events(er))
    er.events = [k for k in EVENT_KEYS if k in events]
    er.save(update_fields=["events"])
    audit.record(request.user, AuditLog.Action.UPDATE, "Telegram qabul qiluvchi", str(er.pk), er, detail=f"{er.label}: {before} → {er.events}")
    return Response(services.extra_payload())


@method_decorator(csrf_protect, name="dispatch")
class TelegramLoginView(APIView):
    """Telegram Mini App ichida parolsiz kirish: initData imzosi bot tokeni bilan tekshiriladi, so'ng shu Telegram
    foydalanuvchisi bog'lagan faol xodimga sessiya ochiladi (webapp.py)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        try:
            tg_user = webapp.validate(str(request.data.get("init_data") or ""))
        except webapp.InvalidInitData as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        link = TelegramLink.objects.filter(chat_id=tg_user["id"], user__employment_status=User.Employment.ACTIVE).select_related("user").first()
        if not link:
            return Response({"detail": "Telegram akkauntingiz tizimga bog'lanmagan. Saytga kirib, ismingiz → «Telegram» orqali bog'lang"},
                            status=status.HTTP_403_FORBIDDEN)
        user = link.user
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        audit.record(user, AuditLog.Action.LOGIN, "Foydalanuvchi", user.pk, user, detail="Telegram Mini App")
        return Response(me_payload(user))
