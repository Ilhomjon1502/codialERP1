from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.core import audit
from apps.core.pagination import Pagination
from apps.core.permissions import role_code, today
from apps.core.roles import MANAGER_ROLES
from apps.core.scoping import scope_branch
from apps.core.viewsets import AuditedModelViewSet
from apps.crm.views import default_branch, search_q
from apps.education.models import Contract, MakeupRequest
from apps.education.services import teacher_scope, with_balance
from apps.references.models import LessonFrequency

from . import receipt, services
from .models import CashType, Confirm, Creditor, CreditorComment, CreditorTransaction, Exchange, Expense, Payment, Transfer
from .serializers import (
    CreditorCommentSerializer,
    CreditorSerializer,
    CreditorTxSerializer,
    ExchangeSerializer,
    ExpenseSerializer,
    PaymentSerializer,
    TransferSerializer,
)

PAYMENT_QS = Payment.objects.select_related("contract__student", "contract__group__course", "discount_type", "branch", "created_by")


def _sum(qs, field="amount"):
    return qs.aggregate(s=Sum(field))["s"] or 0


class PaymentViewSet(AuditedModelViewSet):
    """To'lovlar (bo'lim «payments»). ?month=, ?date=, ?type=, ?search=, ?contract=, ?disc_status=, ?nc_status=. Sahifalangan + jami summalar."""

    section = "payments"
    queryset = PAYMENT_QS
    serializer_class = PaymentSerializer
    branch_field = "branch"
    pagination_class = Pagination
    action_ops = {"approve_discount": "p", "approve_noncash": "p", "receipt": "v", "summary": "v"}

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("month"):
            qs = qs.filter(date__gte=services.month_bounds(p["month"])[0], date__lt=services.month_bounds(p["month"])[1])
        if p.get("date"):
            qs = qs.filter(date=p["date"])
        if p.get("type"):
            qs = qs.filter(cash_type=p["type"])
        if p.get("contract"):
            qs = qs.filter(contract=p["contract"])
        if p.get("disc_status"):
            qs = qs.filter(discount_status=p["disc_status"])
        if p.get("nc_status"):
            qs = qs.filter(noncash_status=p["nc_status"])
        if p.get("search"):
            s = p["search"].strip()
            qs = qs.filter(search_q(s, "contract__student__") | (Q(contract__number=int(s)) | Q(number=int(s)) if s.isdigit() else Q(pk__in=[])))
        return qs.order_by("-date", "-created_at")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        resp = self.get_paginated_response(self.get_serializer(page, many=True).data)
        dates = {x.date for x in page}
        months = {x.date.replace(day=1) for x in page}
        plain = qs.order_by()
        resp.data["total"] = _sum(plain)
        resp.data["by_day"] = {d.isoformat(): s for d, s in plain.filter(date__in=dates).values_list("date").annotate(s=Sum("amount")).values_list("date", "s")}
        resp.data["by_month"] = {m.strftime("%Y-%m"): _sum(plain.filter(date__gte=m, date__lt=services.month_bounds(m.strftime("%Y-%m"))[1])) for m in months}
        return resp

    def _contract(self, cid):
        c = teacher_scope(scope_branch(Contract.objects.select_related("branch__noncash_cashbox", "group"), self.request.user), self.request.user).filter(pk=cid).first()
        if c is None:
            raise ValidationError({"contract": "Shartnoma topilmadi"})
        return c

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data)
        d["contract"] = self._contract(d["contract"].pk)
        d.setdefault("date", today())
        p = services.save_payment(request.user, d)
        return Response(self.get_serializer(PAYMENT_QS.get(pk=p.pk)).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        p = self.get_object()
        ser = self.get_serializer(p, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        services.save_payment(request.user, dict(ser.validated_data), instance=p)
        return Response(self.get_serializer(PAYMENT_QS.get(pk=p.pk)).data)

    def perform_destroy(self, instance):
        services.delete_payment(self.request.user, instance)

    @action(detail=True, methods=["post"])
    def approve_discount(self, request, pk=None):
        return Response(self.get_serializer(services.approve_discount(request.user, self.get_object())).data)

    @action(detail=True, methods=["post"])
    def approve_noncash(self, request, pk=None):
        return Response(self.get_serializer(services.approve_noncash(request.user, self.get_object())).data)

    @action(detail=True)
    def receipt(self, request, pk=None):
        """PDF chek. Tasdiqlanmagan to'lov chekini faqat Admin, Bosh menejer va Filial menejeri ko'radi (prototipdagidek)."""
        p = self.get_object()
        if Confirm.PENDING in (p.discount_status, p.noncash_status) and role_code(request.user) not in MANAGER_ROLES:
            raise PermissionDenied("To'lov hali tasdiqlanmagan (naqdsiz yoki chegirma). Chek tasdiqlangandan keyin chiqadi")
        bal = with_balance(Contract.objects.filter(pk=p.contract_id)).values_list("balance", flat=True).first()
        resp = HttpResponse(receipt.build(p, bal or 0), content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="chek-{p.number}.pdf"'
        return resp

    @action(detail=False)
    def summary(self, request):
        """Bosh sahifa: bugungi naqd va naqdsiz to'lovlar, shu oy jami."""
        qs = super().get_queryset().order_by()
        d = today()
        todays = qs.filter(date=d)
        start, end = services.month_bounds(f"{d:%Y-%m}")
        return Response({"cash": _sum(todays.filter(cash_type=CashType.CASH)), "noncash": _sum(todays.exclude(cash_type=CashType.CASH)),
                         "count": todays.count(), "month": _sum(qs.filter(date__gte=start, date__lt=end))})


def scoped_transfers(user):
    ids = services.scoped_account_ids(user)
    qs = Transfer.objects.select_related("sender_account", "receiver_account")
    return qs if ids is None else qs.filter(Q(sender_account__in=ids) | Q(receiver_account__in=ids))


class TransferViewSet(AuditedModelViewSet):
    """Ichki pul oqimi (bo'lim «transfers»). Tasdiq — qabul qiluvchi g'azna mas'uli yoki Admin."""

    section = "transfers"
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    pagination_class = Pagination
    action_ops = {"confirm": "v"}

    def get_queryset(self):
        qs = scoped_transfers(self.request.user)
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs.order_by("-date", "-created_at")

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        t = services.save_transfer(request.user, ser.validated_data)
        return Response(self.get_serializer(t).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        t = self.get_object()
        ser = self.get_serializer(t, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(self.get_serializer(services.save_transfer(request.user, ser.validated_data, instance=t)).data)

    def perform_destroy(self, instance):
        services.delete_transfer(self.request.user, instance)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return Response(self.get_serializer(services.confirm_transfer(request.user, self.get_object())).data)


class ExchangeViewSet(AuditedModelViewSet):
    """Pul ayirboshlash (bo'lim «exchange» — Admin va Bosh menejer)."""

    section = "exchange"
    queryset = Exchange.objects.select_related("account").order_by("-date", "-created_at")
    serializer_class = ExchangeSerializer
    pagination_class = Pagination
    http_method_names = ["get", "post", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(self.get_serializer(services.save_exchange(request.user, ser.validated_data)).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        services.delete_exchange(self.request.user, instance)


class ExpenseViewSet(AuditedModelViewSet):
    """Xarajatlar (bo'lim «expenses»). ?month= (hisob davri), ?category=, ?search=. /names/?category= — nom takliflari, /summary/ — oy → kategoriya."""

    section = "expenses"
    queryset = Expense.objects.select_related("category", "account")
    serializer_class = ExpenseSerializer
    branch_field = "branch"
    pagination_class = Pagination
    action_ops = {"names": "v", "summary": "v"}

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("month"):
            y, m = (int(x) for x in p["month"].split("-")[:2])
            qs = qs.filter(period_year=y, period_month=m)
        if p.get("category"):
            qs = qs.filter(category=p["category"])
        if p.get("search"):
            qs = qs.filter(name__icontains=p["search"])
        return qs.order_by("-date", "-created_at")

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        resp.data["total"] = _sum(self.get_queryset().order_by(), "total")
        return resp

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data, branch=default_branch(request.user, request.data.get("branch")))
        return Response(self.get_serializer(services.save_expense(request.user, d)).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        e = self.get_object()
        ser = self.get_serializer(e, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(self.get_serializer(services.save_expense(request.user, dict(ser.validated_data), instance=e)).data)

    def perform_destroy(self, instance):
        services.delete_expense(self.request.user, instance)

    @action(detail=False)
    def names(self, request):
        cat = request.query_params.get("category")
        qs = super().get_queryset().filter(category=cat) if cat else super().get_queryset().none()
        return Response(sorted(set(qs.values_list("name", flat=True)))[:100])

    @action(detail=False)
    def summary(self, request):
        """Hisob davri → kategoriya bo'yicha jami (filtrlar hisobga olinadi)."""
        rows = (self.get_queryset().order_by().values("period_year", "period_month", "category", "category__name", "category__kind")
                .annotate(s=Sum("total"), n=Count("id")))
        return Response([{"month": f"{r['period_year']}-{r['period_month']:02d}", "category": r["category"], "name": r["category__name"],
                          "kind": r["category__kind"], "n": r["n"], "sum": r["s"]} for r in rows])


class CreditorViewSet(AuditedModelViewSet):
    """Kreditorlar (bo'lim «creditors» — Admin va Bosh menejer). Joriy haqqi = boshlang'ich − Σ amallar."""

    section = "creditors"
    queryset = Creditor.objects.all()
    serializer_class = CreditorSerializer
    action_ops = {"comments": "a"}
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Creditor.objects.annotate(current=F("initial_balance") - Coalesce(
            Sum("transactions__amount", filter=Q(transactions__is_deleted=False)), Value(0), output_field=DecimalField(max_digits=14, decimal_places=0)))

    def perform_update(self, serializer):
        services.check_creditor_update(self.request.user, serializer.instance, serializer.validated_data)
        super().perform_update(serializer)

    def retrieve(self, request, *args, **kwargs):
        c = self.get_object()
        data = self.get_serializer(c).data
        data["transactions"] = CreditorTxSerializer(c.transactions.order_by("-date", "-created_at"), many=True).data
        data["comments"] = CreditorCommentSerializer(c.comments.order_by("-created_at"), many=True).data
        return Response(data)

    @action(detail=True, methods=["post"])
    def comments(self, request, pk=None):
        text = (request.data.get("comment") or "").strip()
        if not text:
            raise ValidationError({"comment": "Izoh bo'sh"})
        cm = CreditorComment.objects.create(creditor=self.get_object(), comment=text, created_by=request.user, updated_by=request.user)
        audit.log_create(request.user, cm)
        return Response(CreditorCommentSerializer(cm).data, status=status.HTTP_201_CREATED)


class CreditorTxViewSet(AuditedModelViewSet):
    section = "creditors"
    queryset = CreditorTransaction.objects.select_related("creditor", "account").order_by("-date", "-created_at")
    serializer_class = CreditorTxSerializer
    pagination_class = Pagination
    http_method_names = ["get", "post", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data={**request.data, "date": request.data.get("date") or today().isoformat()})
        ser.is_valid(raise_exception=True)
        return Response(self.get_serializer(services.save_creditor_tx(request.user, ser.validated_data)).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        services.delete_creditor_tx(self.request.user, instance)


@api_view(["GET"])
def approvals(request):
    """Qo'ng'iroqcha va Tasdiqlashlar sahifasi uchun: foydalanuvchi tasdiqlay oladigan yozuvlar soni."""
    u = request.user
    makeups = scope_branch(MakeupRequest.objects.all(), u, "attendance__branch")
    return Response(services.pending_counts(u, scope_branch(Payment.objects.all(), u), scoped_transfers(u), makeups,
                                            scope_branch(LessonFrequency.objects.all(), u)))
