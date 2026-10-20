from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.core.permissions import NO_PERMISSION, can, role_code, today
from apps.core.roles import MANAGER_ROLES, TOP_ROLES
from apps.references.services import month_start

from . import gsheets, services, sheet_report


def _manager(user):
    if role_code(user) not in MANAGER_ROLES:
        raise PermissionDenied("Hisobotlarni Admin, Bosh menejer va Filial menejeri ko'radi")


def _months(request, default=6):
    """?months=2026-09,2026-10 yoki ?count=6 (joriy oy bilan tugaydi)."""
    raw = request.query_params.get("months")
    if raw:
        ms = sorted({month_start(x) for x in raw.split(",") if x})
        if len(ms) > 36:
            raise ValidationError({"months": "Ko'pi bilan 36 oy"})
        return ms
    n = min(int(request.query_params.get("count") or default), 36)
    return services.month_list(today(), n)


@api_view(["GET"])
def profit(request):
    """Foyda oyma-oy (bo'lim «profit» — Admin, Bosh menejer). ?months=YYYY-MM,..."""
    if not can(request.user, "profit"):
        raise PermissionDenied(NO_PERMISSION)
    return Response(services.profit(request.user, _months(request)))


@api_view(["GET"])
def stats(request):
    """Oylik statistika: lidlar, shartnomalar, pul, davomat foizi. Pul qismi — faqat «Foyda» ruxsati borlarga."""
    _manager(request.user)
    data = services.monthly_stats(request.user, _months(request))
    if not can(request.user, "profit"):
        data["money"] = None
    return Response(data)


@api_view(["GET"])
def funnel(request):
    """Sotuv voronkasi: ?from=YYYY-MM-DD&to=&source=&course=&owner= (lidni kiritgan xodim)."""
    _manager(request.user)
    p = request.query_params
    return Response(services.funnel(request.user, p.get("from") or None, p.get("to") or None, p.get("source"), p.get("course"), p.get("owner")))


@api_view(["GET"])
def first_payers(request):
    """Tanlangan oyda birinchi marta to'lov qilganlar: ?month=YYYY-MM"""
    _manager(request.user)
    return Response(services.first_payers(request.user, month_start(request.query_params.get("month") or f"{today():%Y-%m}")))


def _top(user):
    if not can(user, "profit") or role_code(user) not in TOP_ROLES:
        raise PermissionDenied("Moliyaviy hisobotni faqat Admin va Bosh menejer oladi")


@api_view(["GET", "POST"])
def sheet(request):
    """Oylik moliyaviy hisobot — Google Sheets (Admin, Bosh menejer).
    GET — ulanganmi; POST {month: "YYYY-MM"} — shu oy varag'ini yaratadi/yangilaydi va havolani qaytaradi."""
    _top(request.user)
    if request.method == "GET":
        return Response({"configured": gsheets.configured()})
    month = month_start(request.data.get("month") or f"{today():%Y-%m}")
    try:
        return Response(sheet_report.generate(request.user, month))
    except gsheets.SheetsError as e:
        return Response({"detail": str(e)}, status=502)
