"""Kunlik hisobot: shartnomalar «+ yangi / − to'xtatildi» va lidlar holat o'zgarishi (audit jurnalidan)."""

import datetime

import pytest
from django.utils import timezone

from apps.core import audit
from apps.crm.models import Lead
from apps.education.models import Contract
from apps.notifications.management.commands.daily_report import build, lead_moves, stopped_contracts
from apps.references.models import LeadSource
from tests.test_finance import fin  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db
TODAY = timezone.localdate()


def test_contract_plus_and_minus(fin):  # noqa: F811
    c = fin["contract"]  # bugun yaratilgan, bugun boshlangan → +1
    Contract.objects.create(branch=fin["branch"], student=c.student, course=c.course, group=c.group, number=2, start_date=TODAY - datetime.timedelta(days=3))
    Contract.objects.filter(number=2).update(created_at=timezone.now() - datetime.timedelta(days=3))  # eski shartnoma: «yangi» emas
    # eski sana bilan to'xtatilgan (kecha) — eskicha hisob buni sanamas edi
    audit.record(fin["boss"], "update", "Shartnoma", c.pk, c, [["end_date", None, str(TODAY - datetime.timedelta(days=1))], ["stop_reason", "", "Kursni tamomladi"]])
    # oddiy tahrir (tugash sanasi o'zgarmagan) va sanani surish — to'xtatish emas
    audit.record(fin["boss"], "update", "Shartnoma", "x1", "", [["comment", "", "izoh"]])
    audit.record(fin["boss"], "update", "Shartnoma", "x2", "", [["end_date", "2026-10-30", "2026-11-05"]])
    assert stopped_contracts(TODAY) == 1
    text = build(TODAY)
    assert "(bugun +1 yangi, −1 to'xtatildi)" in text
    assert stopped_contracts(TODAY - datetime.timedelta(days=1)) == 0


def test_planned_contract_starting_today_counts_as_new(fin):  # noqa: F811
    c = fin["contract"]
    Contract.objects.filter(pk=c.pk).update(created_at=timezone.now() - datetime.timedelta(days=5))  # oldin yaratilgan, bugun boshlanadi (Rejada → Faol)
    assert "(bugun +1 yangi, −0 to'xtatildi)" in build(TODAY)


def test_lead_status_moves(fin):  # noqa: F811
    c = fin["contract"]
    for i, sid in enumerate(("a", "b", "c")):
        audit.record(fin["boss"], "update", "Lid", sid, "", [["status", "2", "3"]] if i < 2 else [["status", "1", "6"]])
    audit.record(fin["boss"], "update", "Lid", "a", "", [["status", "3", "5"]])  # bir lid kun ichida 2 marta: 2 → 3 → 5
    audit.record(fin["boss"], "update", "Lid", "d", "", [["status", "4", "4"], ["comment", "", "x"]])  # holat o'zgarmagan
    assert lead_moves(TODAY) == {"5": 1, "3": 1, "6": 1}
    Lead.objects.create(branch=fin["branch"], student=c.student, source=LeadSource.objects.create(name="Instagram"), course=c.course, status="5")
    text = build(TODAY)
    assert "Bugun holati o'zgardi: 3 ta" in text and "5. O'qishni boshladi — 1" in text and "6. Ma'qul kelmadi — 1" in text
    assert "bugun +1 yangi" in text  # yangi lid
