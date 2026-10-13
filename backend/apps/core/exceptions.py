"""API xatolari o'zbek tilida. Javob shakli: {"detail": "..."} yoki {"maydon": ["..."]}."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Amalni bajarib bo'lmaydi"
    default_code = "conflict"


def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(exc.message_dict if hasattr(exc, "error_dict") else {"detail": exc.messages})
    if isinstance(exc, ProtectedError):
        exc = Conflict("Bu yozuv boshqa yozuvlarda ishlatilgan, o'chirib bo'lmaydi")
    if isinstance(exc, exceptions.NotAuthenticated):
        return Response({"detail": "Tizimga kiring", "code": "not_authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
    if isinstance(exc, exceptions.AuthenticationFailed):
        return Response({"detail": "Sessiya tugagan. Qaytadan kiring", "code": "not_authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
    if isinstance(exc, exceptions.Throttled):
        wait = int(exc.wait or 60)
        return Response({"detail": f"Juda ko'p urinish. {wait} soniyadan keyin qayta urinib ko'ring"}, status=429)
    if isinstance(exc, exceptions.PermissionDenied) and str(exc.detail) == str(exceptions.PermissionDenied.default_detail):
        exc = exceptions.PermissionDenied("Sizning rolingizda bu amalga ruxsat yo'q")
    if isinstance(exc, exceptions.NotFound) and str(exc.detail) == str(exceptions.NotFound.default_detail):
        exc = exceptions.NotFound("Yozuv topilmadi")
    if isinstance(exc, exceptions.ValidationError) and isinstance(exc.detail, dict):
        # Servislardan kelgan {"maydon": "xato"} ham serializer kabi {"maydon": ["xato"]} bo'lsin
        exc.detail = {k: v if isinstance(v, (list, dict)) or k == "detail" else [v] for k, v in exc.detail.items()}
    return drf_handler(exc, context)
