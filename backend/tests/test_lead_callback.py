"""Lid: qayta bog'lanish sanasi va vaqti (1- va 8-statuslar) + shu vaqtda bot eslatmasi (2026-10-21)."""

import datetime

import pytest
from django.utils import timezone

from apps.crm.models import Lead, LeadComment, Student
from apps.notifications import reminders, services
from apps.notifications.models import Outbox, TelegramLink
from apps.references.models import LeadSource
from tests.test_finance import fin  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db
H = datetime.timedelta


def student(f, first, last, phone):
    return Student.objects.create(branch=f["branch"], first_name=first, last_name=last, phone1=phone)


def iso(delta):
    return (timezone.now() + delta).isoformat()


@pytest.fixture
def lead(fin):  # noqa: F811
    c = fin["contract"]
    return Lead.objects.create(branch=fin["branch"], student=c.student, source=LeadSource.objects.create(name="Instagram"), course=c.course, status="2")


def test_callback_time_required_and_validated(api, fin, lead):  # noqa: F811
    c = api(fin["cashier"])
    url = f"/api/v1/leads/{lead.pk}/"
    r = c.patch(url, {"status": "1"}, format="json")  # vaqtsiz
    assert r.status_code == 400 and "callback_at" in r.json()
    assert "o'tib ketgan" in c.patch(url, {"status": "1", "callback_at": iso(-H(hours=2))}, format="json").json()["callback_at"][0]
    r = c.patch(url, {"status": "1", "callback_at": iso(H(days=1))}, format="json")
    assert r.status_code == 200 and r.json()["callback_at"]
    lead.refresh_from_db()
    assert lead.callback_at and lead.callback_reminded_at is None
    # 1 → 8: yangi vaqt kerak
    assert c.patch(url, {"status": "8"}, format="json").status_code == 400
    assert c.patch(url, {"status": "8", "callback_at": iso(H(days=3))}, format="json").status_code == 200
    # holatni o'zgartirmasdan vaqtni surish
    assert c.patch(url, {"callback_at": iso(H(days=5))}, format="json").status_code == 200
    assert c.patch(url, {"callback_at": None}, format="json").status_code == 400
    # boshqa holatga o'tsa vaqt tozalanadi
    assert c.patch(url, {"status": "3"}, format="json").status_code == 200
    lead.refresh_from_db()
    assert lead.callback_at is None and lead.callback_reminded_at is None
    # eski (vaqtsiz) 1-status lidni boshqa maydon bilan tahrirlash to'sqinlik qilmaydi
    Lead.objects.filter(pk=lead.pk).update(status="1", callback_at=None)
    assert c.patch(url, {"age_group": "16-18"}, format="json").status_code == 200


def test_reminder_goes_to_administrator_hisobchi_once(api, make_user, fin, lead, django_capture_on_commit_callbacks):  # noqa: F811
    ah2 = make_user("ADMINISTRATOR_HISOBCHI")
    adm = make_user("ADMINISTRATOR")
    for u, chat in ((fin["cashier"], 1001), (ah2, 1002), (adm, 1003)):
        TelegramLink.objects.create(user=u, chat_id=chat)
    now = timezone.localtime()
    Lead.objects.filter(pk=lead.pk).update(status="1", callback_at=now - H(minutes=2))
    stale = Lead.objects.create(branch=fin["branch"], student=student(fin, "Eski", "Lid", "901110000"), source=lead.source, course=lead.course,
                                status="1", callback_at=now - H(hours=20))
    future = Lead.objects.create(branch=fin["branch"], student=student(fin, "Kelgusi", "Lid", "901110001"), source=lead.source, course=lead.course,
                                 status="8", callback_at=now + H(hours=3))
    with django_capture_on_commit_callbacks(execute=True):
        assert reminders.lead_callbacks(now) == 1  # faqat vaqti kelgan; 20 soatlik eskisi va kelajakdagisi emas
    msgs = Outbox.objects.filter(event="lead_callback")
    assert {m.user_id for m in msgs} == {fin["cashier"].pk, ah2.pk}  # hamma Administrator+Hisobchiga; oddiy Administratorga emas
    m = msgs.first()
    assert "Qayta bog'lanish vaqti keldi" in m.text and lead.student.full_name in m.text
    data = [b["callback_data"] for row in m.markup["inline_keyboard"] for b in row]
    assert data == [f"lc:done:{lead.pk}", f"lc:h1:{lead.pk}", f"lc:tm:{lead.pk}"]
    lead.refresh_from_db()
    assert lead.callback_reminded_at is not None
    with django_capture_on_commit_callbacks(execute=True):
        assert reminders.lead_callbacks(now) == 0  # qayta yuborilmaydi
    assert Outbox.objects.filter(event="lead_callback").count() == 2
    stale.refresh_from_db()
    future.refresh_from_db()
    assert stale.callback_reminded_at is None and future.callback_reminded_at is None
    # vaqt surilsa (reminded tozalanadi) — yangi vaqtda yana eslatadi
    Lead.objects.filter(pk=lead.pk).update(callback_at=now + H(hours=1), callback_reminded_at=None)
    with django_capture_on_commit_callbacks(execute=True):
        assert reminders.lead_callbacks(now + H(hours=1, minutes=1)) == 1
    # holat o'zgargan lidga eslatma yo'q
    Lead.objects.filter(pk=future.pk).update(status="2")
    Lead.objects.filter(pk=lead.pk).update(status="5", callback_at=now + H(hours=2), callback_reminded_at=None)
    assert reminders.lead_callbacks(now + H(hours=3)) == 0


def test_bot_buttons(api, make_user, fin, lead):  # noqa: F811
    TelegramLink.objects.create(user=fin["cashier"], chat_id=2001)
    Lead.objects.filter(pk=lead.pk).update(status="1", callback_at=timezone.now() - H(minutes=1), callback_reminded_at=timezone.now())
    call = lambda act, chat=2001: services.lead_callback_from_telegram(chat, f"lc:{act}:{lead.pk}")  # noqa: E731

    assert call("done", chat=9999) == "Siz botga ulanmagansiz"
    msg = call("h1")
    lead.refresh_from_db()
    assert msg.startswith("✅") and H(minutes=58) < lead.callback_at - timezone.now() < H(minutes=61) and lead.callback_reminded_at is None

    Lead.objects.filter(pk=lead.pk).update(callback_at=timezone.make_aware(datetime.datetime.combine(timezone.localdate(), datetime.time(15, 30))))
    assert call("tm") == "✅ Ertaga 15:30 ga ko'chirildi"
    lead.refresh_from_db()
    assert timezone.localtime(lead.callback_at).date() == timezone.localdate() + H(days=1) and timezone.localtime(lead.callback_at).strftime("%H:%M") == "15:30"

    assert call("done").startswith("✅")
    lead.refresh_from_db()
    assert lead.callback_at is None and LeadComment.objects.filter(lead=lead, comment__startswith="📞 Qo'ng'iroq qilindi").count() == 1

    Lead.objects.filter(pk=lead.pk).update(status="5")  # boshqa holatga o'tgan
    assert "holati o'zgargan" in call("done")
    assert services.lead_callback_from_telegram(2001, "lc:xx") == "Noma'lum amal"
    # Administrator uchun 7 kunlik lid muddati saqlanadi (Administrator+Hisobchi — muddatsiz)
    old = make_user("ADMINISTRATOR")
    TelegramLink.objects.create(user=old, chat_id=2002)
    Lead.objects.filter(pk=lead.pk).update(status="1", created_at=timezone.now() - H(days=30))
    assert "oxirgi 7 kun" in services.lead_callback_from_telegram(2002, f"lc:h1:{lead.pk}")
    assert call("h1").startswith("✅")


def test_morning_plan_lists_overdue_and_today(fin, lead):  # noqa: F811
    now = timezone.localtime()
    day = now.date()
    Lead.objects.filter(pk=lead.pk).update(status="1", callback_at=timezone.make_aware(datetime.datetime.combine(day - H(days=2), datetime.time(11, 0))))
    st2 = student(fin, "Bugun", "Qayta", "901112222")
    Lead.objects.create(branch=fin["branch"], student=st2, source=lead.source, course=lead.course, status="8",
                        callback_at=timezone.make_aware(datetime.datetime.combine(day, datetime.time(16, 0))))
    st3 = student(fin, "Vaqtsiz", "Lid", "901113333")
    Lead.objects.create(branch=fin["branch"], student=st3, source=lead.source, course=lead.course, status="1")
    text = reminders.plan_text(fin["branch"], day)
    assert "Muddati o'tgan qayta bog'lanishlar</b> — 1 ta" in text and f"{day - H(days=2):%d.%m} 11:00" in text
    assert "Bugun qayta bog'lanish rejalashtirilgan</b> — 1 ta" in text and "16:00 · Bugun Qayta" in text
    assert "vaqti belgilanmagan" in text and "Vaqtsiz Lid" in text
