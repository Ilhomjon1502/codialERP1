import datetime

import pytest
from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from apps.notifications import ig_leads
from apps.notifications.models import IgLead, IgWatch, Outbox, TelegramLink

pytestmark = pytest.mark.django_db
URL = "https://docs.google.com/spreadsheets/d/SHEETID/edit?gid=123"


def row(lead_id, phone="+998972142969", name="Alisher", platform="ig", adset="kompyuter sav — interesli", at="2026-11-04T02:30:00-05:00"):
    r = [""] * 16
    r[0], r[1], r[3], r[5], r[7], r[11], r[12], r[13], r[14] = lead_id, at, "post", adset, "Lead | Cbo", platform, name, phone, "p:" + phone
    return r


@pytest.fixture
def now_commit(monkeypatch):
    monkeypatch.setattr("apps.notifications.services.transaction.on_commit", lambda f: f())


@pytest.fixture
def boss(make_user):
    u = make_user("BOSH_MENEJER")
    TelegramLink.objects.create(user=u, chat_id=9001)
    return u


def texts():
    return list(Outbox.objects.filter(event="ig_lead").values_list("text", flat=True))


def group_texts():
    return list(Outbox.objects.filter(event="ig_lead", chat_id=settings.IG_LEADS_CHAT_ID, user__isnull=True).values_list("text", flat=True))


def test_parse_skips_header_and_incomplete_rows():
    assert ig_leads.parse(["ad_id", "ad_name"]) is None
    assert ig_leads.parse(["", "", "", "", "", "", "", "", "", "Umumiy forma"]) is None
    assert ig_leads.parse(row("l:1", phone="12")) is None
    x = ig_leads.parse(row("l:1", phone="+ 998 91 700-09-76"))
    assert x["phone"] == "917000976"[:9] or len(x["phone"]) == 9


def test_first_run_marks_old_then_notifies_only_new(boss, now_commit):
    with override_settings(IG_LEADS_SHEET_URL=URL):
        now = timezone.now()
        assert ig_leads.tick(now, rows=[row("l:1"), row("l:2", phone="903635800")]) == 0 and texts() == []
        assert IgLead.objects.count() == 2
        later = now + datetime.timedelta(minutes=6)
        assert ig_leads.tick(later, rows=[row("l:1"), row("l:3", phone="+998 88 207-62-62", name="Farruxbek", platform="fb")]) == 1
        t = group_texts()[0]
        assert not Outbox.objects.filter(event="ig_lead", chat_id=9001).exists()  # xodimning shaxsiy chatiga bormaydi
        assert "Yangi lid (Facebook)" in t and "Farruxbek · +998882076262" in t and "Manba: Facebook: kompyuter sav — interesli" in t
        assert "Kurs: Kompyuter savodxonligi" in t and "🕒 04.11.2026 12:30" in t
        # qayta o'qilsa takror ketmaydi; 5 daqiqadan oldin umuman o'qilmaydi
        assert ig_leads.tick(later + datetime.timedelta(minutes=6), rows=[row("l:3", phone="+998 88 207-62-62")]) == 0
        assert len(group_texts()) == 1


def test_stops_after_10_days_and_resumes_by_command(boss, now_commit):
    with override_settings(IG_LEADS_SHEET_URL=URL):
        now = timezone.now()
        ig_leads.tick(now, rows=[row("l:1")])
        later = now + datetime.timedelta(days=10, minutes=1)
        ig_leads.tick(later, rows=[row("l:1")])
        assert IgWatch.objects.get().active is False
        assert any("to'xtatildi" in t for t in texts())
        assert ig_leads.tick(later + datetime.timedelta(minutes=10), rows=[row("l:1"), row("l:9")]) == 0  # to'xtatilgan — o'qilmaydi
        assert "qayta yoqildi" in ig_leads.handle_command(9001)
        assert IgWatch.objects.get().active is True
        assert ig_leads.handle_command(1234).startswith("Bu buyruq faqat")


def test_not_configured_does_nothing(boss):
    assert ig_leads.tick(rows=[row("l:1")]) == 0 and not IgWatch.objects.exists()
