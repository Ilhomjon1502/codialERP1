from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core import audit
from apps.core.models import AuditLog
from apps.core.permissions import is_top
from apps.core.viewsets import AuditedModelViewSet

from . import services
from .models import Role, User
from .serializers import RoleSerializer, UserSerializer, me_payload


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Front-end birinchi so'rovda shu yerdan CSRF cookie oladi."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"ok": True})


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = authenticate(request, email=s.validated_data["email"].strip(), password=s.validated_data["password"])
        if user is None:
            return Response({"detail": "Pochta yoki parol noto'g'ri"}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        audit.record(user, AuditLog.Action.LOGIN, "Foydalanuvchi", user.pk, user)
        return Response(me_payload(user))


class LogoutView(APIView):
    def post(self, request):
        audit.record(request.user, AuditLog.Action.LOGOUT, "Foydalanuvchi", request.user.pk, request.user)
        logout(request)
        return Response({"ok": True})


class MeView(APIView):
    def get(self, request):
        return Response(me_payload(request.user))


class PasswordResetView(APIView):
    """Parolni unutganlar uchun: pochta tizimda bo'lsa havola yuboriladi (bor-yo'qligi oshkor qilinmaydi)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password"

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        user = User.objects.filter(email__iexact=email, is_active=True).first() if email else None
        if user:
            services.send_password_link(user)
        return Response({"detail": "Agar bu pochta tizimda bo'lsa, unga parol o'rnatish havolasi yuborildi"})


class PasswordSetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password"

    def post(self, request):
        services.set_password_by_token(str(request.data.get("uid", "")), str(request.data.get("token", "")), str(request.data.get("password", "")))
        return Response({"detail": "Parol o'rnatildi. Endi pochta va yangi parol bilan kiring"})


class UserViewSet(AuditedModelViewSet):
    """Xodimlar (Sozlamalar → Foydalanuvchilar). O'chirilmaydi — «Ishdan ketgan» qilinadi."""

    section = "settings"
    serializer_class = UserSerializer
    queryset = User.objects.select_related("role").prefetch_related("branches").order_by("full_name")
    http_method_names = ["get", "post", "patch", "head", "options"]
    action_ops = {"send_invite": "e"}

    @transaction.atomic
    def perform_create(self, serializer):
        actor = self.request.user
        user = serializer.save(created_by=actor, updated_by=actor)
        user.set_unusable_password()
        user.save(update_fields=["password"])
        audit.log_create(actor, user)
        if user.email:
            transaction.on_commit(lambda: services.send_password_link(user, invited_by=actor))

    @action(detail=True, methods=["post"], url_path="send-invite")
    def send_invite(self, request, pk=None):
        user = self.get_object()
        services.send_password_link(user, invited_by=request.user)
        return Response({"detail": f"{user.email} manziliga parol o'rnatish havolasi yuborildi"})


class RoleViewSet(AuditedModelViewSet):
    section = "settings"
    serializer_class = RoleSerializer
    queryset = Role.objects.prefetch_related("permissions", "can_assign")
    lookup_field = "code"
    http_method_names = ["get", "post", "head", "options"]
    action_ops = {"toggle": "v"}

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Yangi rol keyingi bosqichda qo'shiladi"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"])
    def toggle(self, request, code=None):
        """Faqat Admin va Bosh menejer ruxsatlar matritsasini o'zgartiradi (CLAUDE.md 6.1)."""
        if not is_top(request.user):
            return Response({"detail": "Ruxsatlarni faqat Admin va Bosh menejer o'zgartiradi"}, status=status.HTTP_403_FORBIDDEN)
        role = self.get_object()
        services.toggle_permission(request.user, role, str(request.data.get("section", "")), str(request.data.get("op", "")))
        role.refresh_from_db()
        return Response(RoleSerializer(Role.objects.prefetch_related("permissions", "can_assign").get(pk=role.pk)).data)

