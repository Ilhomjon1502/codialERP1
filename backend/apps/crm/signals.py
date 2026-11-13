"""Lidning yosh guruhi o'zgarsa — yosh bo'yicha alohida narxli kurslardagi qarz qayta hisoblanadi (2026-11-13)."""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Lead


@receiver(pre_save, sender=Lead, dispatch_uid="lead_age_before")
def _remember_age(sender, instance, **kw):
    instance._age_before = Lead.all_objects.filter(pk=instance.pk).values_list("age_group", flat=True).first() if instance.pk else None


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
