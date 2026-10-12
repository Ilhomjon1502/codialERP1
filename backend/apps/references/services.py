"""Ma'lumotnomalar servislari: kurs narxi (oy bo'yicha), oydagi dars soni (kalendar bo'yicha taklif va tasdiq)."""

import calendar
import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core import audit
from apps.core.models import Status

from .models import CoursePrice, DayPattern, LessonFrequency


def month_start(ym):
    """'2026-10' → date(2026, 10, 1)"""
    try:
        y, m = (int(x) for x in str(ym).split("-")[:2])
        return datetime.date(y, m, 1)
    except (TypeError, ValueError) as e:
        raise ValidationError({"month": "Oy formati: YYYY-MM"}) from e


def prev_month(d):
    return (d.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)


def lesson_days_in_month(year, month, weekdays):
    """Kalendar bo'yicha shu oydagi dars kunlari soni (weekdays — ISO, Dushanba=1)."""
    days = calendar.monthrange(year, month)[1]
    return sum(1 for d in range(1, days + 1) if datetime.date(year, month, d).isoweekday() in weekdays)


@transaction.atomic
def set_course_price(user, branch, course, effective_from, price):
    """Narx faqat o'zgarganda yangi yozuv; shu oy uchun yozuv bo'lsa — yangilanadi. Qaytaradi: (yozuv, yangimi)."""
    obj = CoursePrice.objects.filter(branch=branch, course=course, effective_from=effective_from).first()
    if obj:
        before = audit.snapshot(obj)
        obj.price = price
        obj.updated_by = user
        obj.save()
        audit.log_update(user, obj, before)
        created = False
    else:
        obj = CoursePrice.objects.create(branch=branch, course=course, effective_from=effective_from, price=price, created_by=user, updated_by=user)
        audit.log_create(user, obj)
        created = True
    # M3: shu oydan boshlab davomat qatorlaridagi qarz va Foiz-KPI qayta hisoblanadi
    return obj, created


def check_frequency_overlap(branch, day_pattern, year, month, courses, exclude_pk=None):
    """(filial, dars kunlari, kurs, yil, oy) takrorlanmasin (CLAUDE.md 7.2)."""
    qs = LessonFrequency.objects.filter(branch=branch, day_pattern=day_pattern, year=year, month=month).exclude(pk=exclude_pk)
    taken = {c.name for f in qs.prefetch_related("courses") for c in f.courses.all() if c in courses}
    if taken:
        raise ValidationError({"courses": f"Bu oy va dars kunlari uchun dars soni allaqachon kiritilgan: {', '.join(sorted(taken))}"})


@transaction.atomic
def propose_month(branch, year, month, user=None):
    """Har bir faol dars kunlari jadvali uchun kalendardan dars sonini hisoblab «Taklif» yaratadi.
    O'tgan oydagi kurs tanlovi nusxalanadi. Shu oy uchun yozuvi bor jadval o'tkazib yuboriladi. Qaytaradi: yaratilganlar soni."""
    prev = prev_month(datetime.date(year, month, 1))
    created = 0
    for pattern in DayPattern.objects.filter(status=Status.ACTIVE):
        if LessonFrequency.objects.filter(branch=branch, day_pattern=pattern, year=year, month=month).exists():
            continue
        freq = lesson_days_in_month(year, month, pattern.weekdays)
        if not 4 <= freq <= 26:
            continue
        previous = list(LessonFrequency.objects.filter(branch=branch, day_pattern=pattern, year=prev.year, month=prev.month).prefetch_related("courses"))
        for src in previous or [None]:
            f = LessonFrequency.objects.create(branch=branch, day_pattern=pattern, year=year, month=month, frequency=freq, created_by=user, updated_by=user)
            if src:
                f.courses.set(src.courses.all())
            audit.log_create(user, f, detail="Kalendar bo'yicha taklif")
            created += 1
    return created


@transaction.atomic
def approve_frequency(user, freq):
    if freq.status == LessonFrequency.FreqStatus.APPROVED:
        raise ValidationError({"detail": "Allaqachon tasdiqlangan"})
    if not freq.courses.exists():
        raise ValidationError({"courses": "Avval kurslarni belgilang"})
    before = audit.snapshot(freq)
    freq.status = LessonFrequency.FreqStatus.APPROVED
    freq.approved_by = user
    freq.approved_at = timezone.now()
    freq.updated_by = user
    freq.save()
    audit.log_update(user, freq, before)
    # M3: shu oyning davomat qatorlari (qarz va KPI) qayta hisoblanadi
    return freq
