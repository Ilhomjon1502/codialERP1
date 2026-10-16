"""Topshiriqlar qoidalari va bot eslatmalari.

- Beruvchi (yoki Admin, Bosh menejer): tahrirlaydi, muddatni uzaytiradi, bekor qiladi.
- Bajaruvchi (yoki Admin, Bosh menejer): «Bajarildi» deydi — eslatmalar to'xtaydi, beruvchiga xabar boradi.
- Eslatma: muddatdan `remind_before` daqiqa oldin boshlanadi, `remind_every` daqiqada takrorlanadi (0 — bir marta),
  muddat o'tsa ham topshiriq yopilmaguncha davom etadi. Bot jarayoni har daqiqada `due_reminders()` ni chaqiradi."""

import datetime
from html import escape

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core import audit
from apps.core.permissions import is_top
from apps.core.roles import RoleCode
from apps.core.scoping import branch_ids

from .models import StaffTask

S = StaffTask.Status
BEFORE_CHOICES = [0, 15, 60, 180, 1440, 2880]  # daqiqa
EVERY_CHOICES = [0, 30, 60, 180, 1440]
MAX_LOOKAHEAD = max(BEFORE_CHOICES)


def scope(qs, user):
    """Admin, Bosh menejer — hammasi; boshqalar — o'zi bergan va o'ziga berilgan."""
    return qs if is_top(user) else qs.filter(Q(created_by=user) | Q(assignee=user))


def is_giver(task, user):
    return task.created_by_id == user.pk or is_top(user)


def assignable(user):
    """Topshiriq berish mumkin bo'lgan faol xodimlar: o'z filiallaridagilar (Admin, BM — hammasi), «Boshqa» rolidan tashqari."""
    qs = User.objects.filter(employment_status=User.Employment.ACTIVE).exclude(role__code=RoleCode.BOSHQA)
    ids = branch_ids(user)
    if ids is not None:
        qs = qs.filter(Q(branches__in=ids) | Q(role__code__in=[RoleCode.ADMIN, RoleCode.BOSH_MENEJER]) | Q(pk=user.pk)).distinct()
    return qs


def validate(user, data, task=None):
    get = lambda k: data.get(k, getattr(task, k, None))  # noqa: E731
    errors = {}
    if not (get("title") or "").strip():
        errors["title"] = "Mavzuni yozing"
    assignee = get("assignee")
    if assignee is None:
        errors["assignee"] = "Bajaruvchini tanlang"
    elif "assignee" in data and not assignable(user).filter(pk=assignee.pk).exists():
        errors["assignee"] = "Bu xodimga topshiriq berib bo'lmaydi"
    due = get("due_at")
    if due is None:
        errors["due_at"] = "Muddatni kiriting"
    elif "due_at" in data and due <= timezone.now():
        errors["due_at"] = "Muddat hozirgi vaqtdan keyin bo'lishi kerak"
    if get("remind_before") not in BEFORE_CHOICES:
        errors["remind_before"] = "Noto'g'ri qiymat"
    if get("remind_every") not in EVERY_CHOICES:
        errors["remind_every"] = "Noto'g'ri qiymat"
    if errors:
        raise ValidationError(errors)


# ------------------------------------------------------------------ amallar

@transaction.atomic
def create(user, data):
    validate(user, data)
    task = StaffTask.objects.create(created_by=user, updated_by=user, **data)
    audit.log_create(user, task)
    # Berilgan zahoti: bajaruvchiga (o'ziga bergan bo'lsa ham) va beruvchiga tasdiq
    notify_one(task, task.assignee, f"📌 <b>Yangi topshiriq</b>\n{_card(task)}", done_button=True)
    if task.assignee_id != user.pk:
        warn = "" if linked(task.assignee) else "\n⚠️ Bajaruvchi Telegram botga ulanmagan — unga xabar bormaydi. Profil → «Telegram» orqali bog'lashini ayting"
        notify_one(task, user, f"📤 <b>Topshiriq berildi</b>\n{_card(task)}{warn}")
    return task


def linked(user):
    """Xodim Telegram botga bog'langanmi (xabar yetib boradimi)."""
    from apps.notifications.models import TelegramLink

    return TelegramLink.objects.filter(user=user, chat_id__isnull=False).exists()


@transaction.atomic
def update(user, task, data):
    if not is_giver(task, user):
        raise PermissionDenied("Topshiriqni faqat uni bergan xodim o'zgartiradi")
    if task.status != S.OPEN:
        raise ValidationError({"detail": "Yopilgan topshiriqni o'zgartirib bo'lmaydi"})
    validate(user, data, task)
    before = audit.snapshot(task)
    old_due, old_assignee = task.due_at, task.assignee_id
    for k, v in data.items():
        setattr(task, k, v)
    if task.due_at != old_due or any(k.startswith("remind_") for k in data):
        task.last_reminded_at = None  # eslatmalar yangi jadval bo'yicha
    task.updated_by = user
    task.save()
    audit.log_update(user, task, before)
    if task.assignee_id != old_assignee and task.assignee_id != user.pk:
        notify_one(task, task.assignee, f"📌 <b>Sizga topshiriq berildi</b>\n{_card(task)}", done_button=True)
    elif task.due_at != old_due and task.assignee_id != user.pk:
        notify_one(task, task.assignee, f"⏰ <b>Muddat o'zgartirildi</b>: {_due(task.due_at)}\n{_card(task)}", done_button=True)
    return task


@transaction.atomic
def complete(user, task, comment=""):
    if task.assignee_id != user.pk and not is_top(user):
        raise PermissionDenied("Topshiriqni bajaruvchi «Bajarildi» deb belgilaydi")
    if task.status != S.OPEN:
        raise ValidationError({"detail": f"Topshiriq allaqachon «{task.status}»"})
    before = audit.snapshot(task)
    task.status, task.done_at, task.done_comment, task.updated_by = S.DONE, timezone.now(), (comment or "").strip(), user
    task.save()
    audit.log_update(user, task, before, detail="Bajarildi")
    if task.created_by_id and task.created_by_id != user.pk:
        extra = f"\n💬 {escape(task.done_comment)}" if task.done_comment else ""
        notify_one(task, task.created_by, f"✅ <b>Bajarildi</b>: {escape(task.title)}\n👤 {escape(str(user))}{extra}")
    return task


@transaction.atomic
def cancel(user, task, reason=""):
    if not is_giver(task, user):
        raise PermissionDenied("Topshiriqni faqat uni bergan xodim bekor qiladi")
    if task.status != S.OPEN:
        raise ValidationError({"detail": f"Topshiriq allaqachon «{task.status}»"})
    before = audit.snapshot(task)
    task.status, task.cancelled_at, task.cancel_reason, task.updated_by = S.CANCELLED, timezone.now(), (reason or "").strip(), user
    task.save()
    audit.log_update(user, task, before, detail="Bekor qilindi")
    if task.assignee_id != user.pk:
        extra = f"\nSabab: {escape(task.cancel_reason)}" if task.cancel_reason else ""
        notify_one(task, task.assignee, f"❌ <b>Topshiriq bekor qilindi</b>: {escape(task.title)}{extra}")
    return task


# ------------------------------------------------------------------ Telegram

def _due(dt):
    dt = timezone.localtime(dt)
    return f"{dt:%d.%m.%Y %H:%M}"


def _left(task, now=None):
    now = now or timezone.now()
    sec = int((task.due_at - now).total_seconds())
    m = abs(sec) // 60
    span = f"{m // 1440} kun {m % 1440 // 60} soat" if m >= 1440 else (f"{m // 60} soat {m % 60} daqiqa" if m >= 60 else f"{m} daqiqa")
    return f"{span} qoldi" if sec >= 0 else f"⚠️ muddati {span} oldin o'tdi"


def _card(task, now=None):
    desc = f"\n{escape(task.description[:600])}" if task.description else ""
    return (f"<b>{escape(task.title)}</b>{desc}\n⏰ Muddat: {_due(task.due_at)} ({_left(task, now)})\n"
            f"👤 Bajaruvchi: {escape(str(task.assignee))} · beruvchi: {escape(str(task.created_by or '—'))}")


def notify_one(task, user, text, done_button=False):
    from apps.notifications import services as notif
    from apps.notifications import webapp

    rows = []
    if done_button:
        rows.append([{"text": "✅ Bajarildi", "callback_data": f"td:{task.pk}"}])
    if webapp.enabled():
        rows.append([{"text": "📋 Topshiriqni ochish", "web_app": {"url": webapp.url("tasks", id=task.pk)}}])
    notif.notify("task", text, default_users=[user], only=lambda u: u.pk == user.pk, markup={"inline_keyboard": rows} if rows else None)


def due_reminders(now=None):
    """Eslatma vaqti kelgan ochiq topshiriqlar → bajaruvchi va/yoki beruvchiga. Qaytaradi: yuborilganlar soni."""
    now = now or timezone.now()
    qs = (StaffTask.objects.filter(status=S.OPEN, due_at__lte=now + datetime.timedelta(minutes=MAX_LOOKAHEAD))
          .filter(Q(remind_assignee=True) | Q(remind_giver=True)).select_related("assignee", "created_by"))
    n = 0
    for t in qs:
        if now < t.due_at - datetime.timedelta(minutes=t.remind_before):
            continue
        if t.last_reminded_at and (not t.remind_every or now - t.last_reminded_at < datetime.timedelta(minutes=t.remind_every)):
            continue
        StaffTask.all_objects.filter(pk=t.pk).update(last_reminded_at=now)
        if t.remind_assignee:
            notify_one(t, t.assignee, f"🔔 <b>Eslatma — topshiriq</b>\n{_card(t, now)}", done_button=True)
        if t.remind_giver and t.created_by_id and t.created_by_id != t.assignee_id:
            notify_one(t, t.created_by, f"🔔 <b>Eslatma — siz bergan topshiriq</b>\n{_card(t, now)}")
        n += 1
    return n


def done_from_telegram(chat_id, task_id):
    """Botdagi «✅ Bajarildi» tugmasi. Qaytaradi: foydalanuvchiga ko'rsatiladigan qisqa javob."""
    from apps.notifications.models import TelegramLink

    link = TelegramLink.objects.filter(chat_id=chat_id, user__employment_status=User.Employment.ACTIVE).select_related("user").first()
    task = StaffTask.objects.filter(pk=task_id).first() if link else None
    if not link or not task:
        return "Topshiriq topilmadi"
    try:
        complete(link.user, task, comment="")
    except (ValidationError, PermissionDenied) as e:
        detail = e.detail.get("detail") if isinstance(e.detail, dict) else e.detail
        return str(detail)[:190]
    return "✅ Bajarildi deb belgilandi"

