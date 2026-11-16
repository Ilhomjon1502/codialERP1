"""Kiruvchi (Instagram/Facebook/sayt) lidga darhol SMS — «Kompyuter savodxonligi» (2026-11-16)."""

import datetime

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.calls import auto_sms
from apps.calls.models import CallDevice, SmsMessage, SmsRule
from apps.crm import inbox
from apps.crm.models import InboxLead, Parent, Student

pytestmark = pytest.mark.django_db
KS = "Kompyuter savodxonligi"
TEXT = "Javlon, siz Kompyuter savodxonligida https://ilhomjon1502.github.io/Ks-darsi/ darslarini o'rganasiz."


@pytest.fixture
def env(branch):
    CallDevice.objects.create(name="Qabul", branch=branch, token_hash="x")
    return auto_sms.ensure_rules([branch])


def sent():
    return list(SmsMessage.objects.filter(kind=SmsMessage.Kind.INBOX).order_by("created_at"))


def test_clean_name():
    f = auto_sms.clean_name
    assert (f("Javlon"), f("javlon aliyev"), f("азимжон"), f("Мурод ил"), f("ШАХЗОД"), f("ўктам"), f("Ғайрат")) == ("Javlon", "Javlon", "Azimjon", "Murod", "Shaxzod", "O'ktam", "G'ayrat")
    assert (f(""), f("—"), f("😀"), f("123"), f("a"), f("  ")) == ("",) * 6
    assert f("👑Sitora👑") == "Sitora"


def test_rule_is_enabled_by_default(env):
    r = {x.key: x for x in env}["inbox_lead"]
    assert r.enabled and r.enabled_at and r.text.startswith("{ism}, siz Kompyuter savodxonligida https://ilhomjon1502.github.io/Ks-darsi/")
    assert not {x.key: x for x in env}["lead"].enabled  # boshqa qoidalar o'chiq qoladi


def test_instagram_lead_gets_sms_once_per_phone(env, branch):
    item, _ = inbox.add("Instagram", phone="901112233", name="javlon", course_name=KS, external_id="l:1")
    m = sent()
    assert len(m) == 1 and m[0].text == TEXT and m[0].phone == "901112233" and m[0].status == "Navbatda" and m[0].recipient == "Lid (Instagram)"
    inbox.add("Facebook", phone="901112233", name="javlon", course_name=KS, external_id="l:2")  # shu raqam — qayta ketmaydi
    assert len(sent()) == 1


def test_no_name_greeting_and_site_source(env, branch):
    inbox.add("Sayt", phone="902223344", name="", course_name=KS)
    inbox.add("Instagram", phone="903334455", name="—", course_name=KS, external_id="l:3")
    assert [m.text.split(",")[0] for m in sent()] == ["Assalomu alaykum"] * 2


def test_skips_other_course_known_phone_old_and_disabled(env, branch):
    inbox.add("Instagram", phone="901000001", name="Ali", course_name="Frontend", external_id="a")
    inbox.add("Instagram", phone="901000002", name="Ali", course_name="", external_id="b")
    Student.objects.create(branch=branch, first_name="Vali", last_name="Aliyev", phone1="901000003")
    inbox.add("Instagram", phone="901000003", name="Vali", course_name=KS, external_id="c")
    Parent.objects.create(branch=branch, first_name="Karim", last_name="Aliyev", phone="901000004")
    inbox.add("Instagram", phone="901000004", name="Karim", course_name=KS, external_id="d")
    inbox.add("Instagram", phone="901000005", name="Eski", course_name=KS, external_id="e", received_at=timezone.now() - datetime.timedelta(days=2))
    assert sent() == []
    SmsRule.objects.filter(key="inbox_lead").update(enabled=False)
    inbox.add("Instagram", phone="901000006", name="Ali", course_name=KS, external_id="f")
    assert sent() == []


def test_backfill_sends_once_to_open_ks_leads(env, branch):
    SmsRule.objects.filter(key="inbox_lead").update(enabled=False)  # lidlar «avval» tushgan
    inbox.add("Instagram", phone="901000011", name="Ali", course_name=KS, external_id="1", received_at=timezone.now() - datetime.timedelta(days=3))
    inbox.add("Facebook", phone="901000012", name="Vali", course_name=KS, external_id="2", received_at=timezone.now() - datetime.timedelta(days=3))
    inbox.add("Instagram", phone="901000013", name="Sali", course_name="Frontend", external_id="3")
    closed, _ = inbox.add("Instagram", phone="901000014", name="Yopiq", course_name=KS, external_id="4", received_at=timezone.now() - datetime.timedelta(days=3))
    InboxLead.objects.filter(pk=closed.pk).update(status="rejected")
    SmsRule.objects.filter(key="inbox_lead").update(enabled=True)
    call_command("sms_inbox_backfill")  # sinov
    assert sent() == []
    call_command("sms_inbox_backfill", "--commit")
    assert sorted(m.phone for m in sent()) == ["901000011", "901000012"]
    call_command("sms_inbox_backfill", "--commit")  # qayta — takror yo'q
    assert len(sent()) == 2
