"""seed_demo uchun M6: ustozlarni baholash, guruh baholash (oy yakuni), ota-onalar bilan aloqa. Qayta ishga tushirilsa dublikat yaratmaydi."""

import datetime
import random

from django.utils import timezone

from .models import Contract, GradingSession, Group, ParentCall, StudentGrade, TeacherEvaluation

CALLS = ["Darsga 2 marta kelmadi, ota-onasi bilan gaplashildi", "Uy vazifasini bajarmayapti — ota-onaga aytildi", "To'lov muddati eslatildi",
         "Yaxshi o'qiyapti, ota-onasi minnatdor", "Kechikib kelyapti, sababini bilib olindi"]


def seed(cmd, branch, users):
    if TeacherEvaluation.all_objects.filter(legacy_id__startswith="demo:").exists():
        return
    R = random.Random(20261016)
    today = timezone.localdate()
    staff = users["u4"]
    n = 0
    for g in Group.objects.filter(branch=branch, legacy_id__startswith="demo:").exclude(start_date__gt=today):
        active = list(Contract.objects.filter(group=g, start_date__lte=today).exclude(end_date__lt=today).select_related("student"))
        if not active:
            continue
        for i, c in enumerate(active[:3]):
            s = [R.randint(6, 10) for _ in range(5)]
            TeacherEvaluation.objects.create(branch=branch, date=today - datetime.timedelta(days=R.randint(1, 20)), contract=c, group=g, teacher=g.teacher,
                                             s1=s[0], s2=s[1], s3=s[2], s4=s[3], s5=s[4], comment=R.choice(["", "Darslar qiziq", "Ba'zan tez tushuntiradi"]),
                                             created_by=staff, updated_by=staff, legacy_id=f"demo:ev-{g.pk}-{i}")
            n += 1
        sess = GradingSession.objects.create(branch=branch, teacher=g.teacher, course=g.course, group=g, date=today.replace(day=1) - datetime.timedelta(days=1),
                                             comment="Oy yakuni", created_by=g.teacher, updated_by=g.teacher, legacy_id=f"demo:gs-{g.pk}")
        for c in active:
            StudentGrade.objects.create(session=sess, contract=c, attendance_score=R.randint(12, 20), task_score=R.randint(20, 40), final_score=R.randint(250, 480),
                                        created_by=g.teacher, updated_by=g.teacher)
        for i, c in enumerate(R.sample(active, min(2, len(active)))):
            ParentCall.objects.create(branch=branch, course=g.course, group=g, contract=c, date=today - datetime.timedelta(days=R.randint(0, 10)),
                                      comment=R.choice(CALLS), created_by=staff, updated_by=staff, legacy_id=f"demo:pc-{g.pk}-{i}")
            n += 1
        n += 1
    cmd.created += n
