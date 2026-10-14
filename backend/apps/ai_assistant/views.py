from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.core.permissions import can

from . import providers, services
from .models import AIQuery


def _check(user):
    if not can(user, "ai", "v"):
        raise PermissionDenied("AI yordamchi faqat Bosh menejer uchun")


@api_view(["GET"])
def info(request):
    """Holat: sozlanganmi, limit, namunaviy savollar va mening oxirgi savollarim."""
    _check(request.user)
    return Response({
        "configured": providers.configured(), "provider": settings.AI_PROVIDER, "model": providers.model_name(),
        "limit": settings.AI_DAILY_LIMIT, "used": services.used_today(request.user), "max_rows": settings.AI_MAX_ROWS,
        "examples": [q for q, _, _ in services.examples()], "history": services.history(request.user),
    })


@api_view(["POST"])
def ask(request):
    _check(request.user)
    return Response(services.ask(request.user, request.data.get("question")))


@api_view(["POST"])
def rerun(request, pk):
    _check(request.user)
    return Response(services.rerun(request.user, get_object_or_404(AIQuery, pk=pk, user=request.user, kind=AIQuery.Kind.ASK)))


@api_view(["POST"])
def analyze(request, pk):
    _check(request.user)
    return Response(services.analyze(request.user, get_object_or_404(AIQuery, pk=pk, user=request.user, kind=AIQuery.Kind.ASK)))
