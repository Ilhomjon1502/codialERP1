"""Xodimlar: parol o'rnatish havolasi (taklif), parolni tiklash, rol ruxsatlarini o'zgartirish."""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core import audit
from apps.core.models import AuditLog
from apps.core.roles import OPS, SECTION_KEYS, RoleCode

from .models import RolePermission, User


def password_link(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.FRONTEND_URL.rstrip('/')}/#/set-password?uid={uid}&token={token}"


def send_password_link(user, *, invited_by=None, invite=False):
    """Yangi xodimga (yoki parolni unutganga) bir martalik parol o'rnatish havolasini yuboradi.
    invite=True — o'tish kuni AppSheet'dan ko'chgan xodimlarga taklif (send_invites)."""
    if not user.email or not user.is_active:
        raise ValidationError({"detail": "Xodimda pochta yo'q yoki u ishdan ketgan"})
    hours = settings.PASSWORD_RESET_TIMEOUT // 3600
    if invited_by or invite:
        subject = "Codial ERP: tizimga kirish uchun parol o'rnating"
        who = f"{invited_by.full_name} sizni Codial ERP tizimiga qo'shdi." if invited_by else "Codial endi AppSheet o'rniga yangi Codial ERP tizimida ishlaydi."
        intro = f"Assalomu alaykum, {user.full_name}!\n\n{who}"
    else:
        subject = "Codial ERP: parolni tiklash"
        intro = f"Assalomu alaykum, {user.full_name}!\n\nParolingizni tiklash so'raldi."
    body = (
        f"{intro}\n\nParol o'rnatish uchun quyidagi havolani oching (havola {hours} soat amal qiladi va bir marta ishlaydi):\n"
        f"{password_link(user)}\n\nKeyin pochtangiz ({user.email}) va yangi parolingiz bilan kirasiz.\n"
        "Agar bu xat sizga tegishli bo'lmasa, uni e'tiborsiz qoldiring."
    )
    send_mail(subject, body, None, [user.email])
    audit.record(invited_by or user, AuditLog.Action.PASSWORD, "Xodim", user.pk, user, detail="Parol o'rnatish havolasi yuborildi")


def user_from_uid(uid):
    try:
        return User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


@transaction.atomic
def set_password_by_token(uid, token, password):
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError as DjangoValidationError

    user = user_from_uid(uid)
    if not user or not default_token_generator.check_token(user, token):
        raise ValidationError({"detail": "Havola eskirgan yoki noto'g'ri. Administratordan yangi havola so'rang"})
    try:
        validate_password(password, user)
    except DjangoValidationError as e:
        raise ValidationError({"password": list(e.messages)}) from e
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])
    audit.record(user, AuditLog.Action.PASSWORD, "Xodim", user.pk, user, detail="Parol o'rnatildi")
    return user


@transaction.atomic
def toggle_permission(actor, role, section, op):
    """Rol ruxsatini yoqish/o'chirish. Admin roli o'zgarmaydi (tizimdan qulflanib qolmaslik uchun)."""
    if role.code == RoleCode.ADMIN:
        raise PermissionDenied("Admin rolining ruxsatlari o'zgarmaydi")
    if section not in SECTION_KEYS or op not in OPS:
        raise ValidationError({"detail": "Noto'g'ri bo'lim yoki ruxsat"})
    perm, _ = RolePermission.objects.get_or_create(role=role, section=section)
    before = perm.ops
    perm.ops = "".join(o for o in OPS if (o in before) != (o == op))
    perm.save(update_fields=["ops"])
    audit.record(actor, AuditLog.Action.UPDATE, "Rol ruxsati", role.pk, f"{role.name} · {section}", [["ops", before or "∅", perm.ops or "∅"]])
    return perm
