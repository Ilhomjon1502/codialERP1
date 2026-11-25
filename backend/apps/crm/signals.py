"""Lid signallari: yosh guruhi o'zgarsa yosh narxli kurslardagi qarz qayta hisoblanadi (2026-11-13); yangi kiruvchi lidga avtomatik SMS (2026-11-16)."""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import InboxLead, Lead

DEMO_FIELDS = ("status", "group_id", "demo_date")


@receiver(pre_save, sender=Lead, dispatch_uid="lead_age_before")
def _remember_age(sender, instance, **kw):
    old = Lead.all_objects.filter(pk=instance.pk).values("age_group", *DEMO_FIELDS).first() if instance.pk else None
    instance._age_before = old["age_group"] if old else None
    instance._demo_before = tuple(old[f] for f in DEMO_FIELDS) if old else None


@receiver(post_save, sender=Lead, dispatch_uid="lead_demo_sms")
def _demo_sms(sender, instance, **kw):
    """«Sinov darsga yozildi»ga o'tdi yoki sinov kuni/guruhi o'zgardi — kelish vaqti SMS'i (avtomatik SMS qoidasi `demo_signup`)."""
    if getattr(instance, "_demo_before", None) != tuple(getattr(instance, f) for f in DEMO_FIELDS) and not instance.is_deleted:
        from apps.calls import auto_sms

        auto_sms.demo_signed_up(instance)


@receiver(post_save, sender=Lead, dispatch_uid="lead_age_recalc")
def _recalc_age(sender, instance, created, **kw):
    if created or getattr(instance, "_age_before", None) == instance.age_group or not instance.student_id:
        return
    from apps.education import calc
    from apps.education.models import Attendance
    from apps.references.models import CoursePrice

    first = {}
    for course_id, eff in CoursePrice.objects.filter(branch_id=instance.branch_id, min_age__gt=0).values_list("course_id", "effective_from"):
        first[course_id] = min(eff, first.get(course_id, eff))
    for course_id, eff in first.items():
        qs = Attendance.objects.filter(branch_id=instance.branch_id, course_id=course_id, contract__student_id=instance.student_id, date__gte=eff)
        if qs.exists():
            calc.recalculate(qs)


@receiver(post_save, sender=InboxLead, dispatch_uid="inbox_lead_sms")
def _inbox_sms(sender, instance, created, **kw):
    """Instagram/Facebook/saytdan yangi lid — Kompyuter savodxonligi bo'lsa, darhol SMS (avtomatik SMS qoidasi `inbox_lead`)."""
    if created:
        from apps.calls import auto_sms

        auto_sms.inbox_created(instance)
