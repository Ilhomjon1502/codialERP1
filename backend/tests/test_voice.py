"""Telegram ovozli buyruqlar (apps/voice): Gemini javobi soxta — bandlarni moslash, tasdiq kartasi, tugmalar, bajarish va audit."""

import datetime
import itertools
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Role
from apps.ai_assistant import providers
from apps.core.models import AuditLog
from apps.crm.models import Student
from apps.education.models import Contract, Group
from apps.finance import services as fin
from apps.finance.models import Account, Confirm, Creditor, CreditorTransaction, Expense
from apps.notifications import services as bot
from apps.notifications.models import TelegramLink
from apps.payroll.models import SalaryAssignment, SalaryPayout
from apps.references.models import Course, DayPattern, ExpenseCategory, LessonTime, Room
from apps.tasks.models import StaffTask
from apps.voice import match
from apps.voice import services as voice
from apps.voice.models import VoiceCommand

pytestmark = pytest.mark.django_db
TODAY = timezone.localdate()
CHAT = 555001
_msg = itertools.count(100)


@pytest.fixture
def tg(monkeypatch):
    """Telegram API chaqiruvlari yoziladi; sendMessage — yangi message_id."""
    calls = []

    def api(method, **params):
        calls.append((method, params))
        return {"message_id": next(_msg)} if method == "sendMessage" else True

    monkeypatch.setattr(bot, "api", api)
    monkeypatch.setattr(bot, "download_file", lambda file_id, **kw: b"OGG")
    return calls


@pytest.fixture
def llm(monkeypatch):
    """Gemini javobi: llm.reply = {...}; llm.calls — yuborilgan so'rovlar."""
    class Fake:
        reply = {"transcript": "", "items": []}
        calls = []

    def complete_json(system, user, strong=False, audio=None, timeout=None):
        Fake.calls.append({"system": system, "user": user, "audio": audio})
        return Fake.reply

    monkeypatch.setattr(providers, "complete_json", complete_json)
    return Fake


@pytest.fixture
def env(branch, make_user):
    boss = make_user("BOSH_MENEJER", full_name="Ilhomjon Bosh")
    TelegramLink.objects.create(user=boss, chat_id=CHAT)
    cashier = make_user("ADMINISTRATOR_HISOBCHI", full_name="Akbarxo'ja Karimov")
    cash = Account.objects.create(name="Emirat g'azna", cash_type="ALL", initial_balance=1_000_000)
    cash.responsible.set([cashier])
    card = Account.objects.create(name="Bosh g'azna", cash_type="CARD", initial_balance=0)
    card.responsible.set([boss])
    branch.default_cashbox, branch.noncash_cashbox = cash, card
    branch.save()
    cat = ExpenseCategory.objects.create(name="Internet")
    cat.allowed_roles.set(Role.objects.filter(code__in=["ADMIN", "BOSH_MENEJER"]))
    ExpenseCategory.objects.create(name="Kommunal").allowed_roles.set(Role.objects.filter(code="BOSH_MENEJER"))
    mnsh = Creditor.objects.create(name="MNSH Ilhomjon")
    return {"boss": boss, "cashier": cashier, "cash": cash, "card": card, "cat": cat, "mnsh": mnsh, "branch": branch}


def text_msg(text, **kw):
    return {"chat": {"id": CHAT, "type": "private"}, "text": text, "date": int(timezone.now().timestamp()), **kw}


def press(data):
    return voice.on_callback({"id": "cb1", "from": {"id": CHAT}, "data": data})


def last_cmd():
    return VoiceCommand.objects.order_by("-created_at").first()


def card_text(tg_calls):
    return [p["text"] for m, p in tg_calls if m in ("editMessageText", "sendMessage")][-1]


# ------------------------------------------------------------------ moslash

def test_match_find():
    items = [("a", "Emirat g'azna"), ("b", "Bosh g'azna"), ("c", "Internet"), ("d", "Ijara")]
    assert match.find("emirat", items)[0] == "a"
    assert match.find("bosh gʻaznasi", items)[0] == "b"
    assert match.find("internt", items)[0] == "c"
    obj, options = match.find("", items)
    assert obj is None and len(options) == 4
    people = [(1, "Ali Valiyev"), (2, "Ali Karimov")]
    obj, options = match.find("Ali", people)
    assert obj is None and {o[0] for o in options} == {1, 2}
    assert match.find("Karimov Ali", people)[0] == 2


# ------------------------------------------------------------------ xarajat

def test_expense_card_confirm_and_audit(env, tg, llm):
    llm.reply = {"transcript": "Internetga 300 ming to'ladim naqd", "items": [
        {"type": "expense", "category": "internet", "name": "Internet oktyabr", "quantity": 1, "price": 300000, "cash_type": "CASH"}]}
    assert voice.handle_update(text_msg("Internetga 300 ming to'ladim naqd")) is True
    cmd = last_cmd()
    assert cmd.status == VoiceCommand.Status.DRAFT and cmd.items[0]["type"] == "expense"
    body = card_text(tg)
    assert "Internet" in body and "300 000" in body and "Emirat g'azna" in body
    assert not Expense.objects.exists()  # tasdiqsiz yozilmaydi
    assert press(f"vc:ok:{cmd.pk}").startswith("✅")
    e = Expense.objects.get()
    assert e.total == 300000 and e.account == env["cash"] and e.created_by == env["boss"] and e.date == TODAY
    assert fin.balance(env["cash"]) == 700_000
    log = AuditLog.objects.get(model="Xarajat")
    assert "Telegram buyruq" in log.detail and "Internetga" in log.detail
    cmd.refresh_from_db()
    assert cmd.status == VoiceCommand.Status.DONE and cmd.items[0]["result"].startswith("✅")
    # ikkinchi bosish — dublikat yo'q
    assert "allaqachon" in press(f"vc:ok:{cmd.pk}")
    assert Expense.objects.count() == 1


def test_voice_message_sent_as_audio_and_forward_date(env, tg, llm):
    llm.reply = {"transcript": "Kecha internet 100 ming", "items": [{"type": "expense", "category": "Internet", "price": 100000, "date": None}]}
    old = timezone.now() - datetime.timedelta(days=3)
    msg = {"chat": {"id": CHAT, "type": "private"}, "voice": {"file_id": "F1", "duration": 4, "mime_type": "audio/ogg"},
           "date": int(timezone.now().timestamp()), "forward_origin": {"date": int(old.timestamp())}}
    assert voice.handle_update(msg)
    assert llm.calls[-1]["audio"] == (b"OGG", "audio/ogg")
    cmd = last_cmd()
    assert cmd.is_voice and cmd.duration == 4
    press(f"vc:ok:{cmd.pk}")
    assert Expense.objects.get().date == timezone.localtime(old).date()  # sana aytilmasa — ovoz yozilgan kun


def test_ambiguous_account_pick_then_confirm(env, tg, llm):
    k1 = Account.objects.create(name="Kassa 1", cash_type="CASH")
    Account.objects.create(name="Kassa 2", cash_type="CASH")
    llm.reply = {"transcript": "x", "items": [{"type": "expense", "category": "Kommunal", "price": 50000, "cash_type": "CASH", "account": "kassa"}]}
    voice.handle_update(text_msg("Kommunal 50 ming emiratdan"))
    cmd = last_cmd()
    markup = [p for m, p in tg if m == "editMessageText"][-1]["reply_markup"]
    assert "vc:pk:" in markup and "vc:ok:" not in markup  # avval tanlash
    cmd.refresh_from_db()
    ids = cmd.items[0]["need"]["ids"]
    assert len(ids) == 2
    press(f"vc:pk:{cmd.pk}:0:{ids.index(str(k1.pk))}")
    cmd.refresh_from_db()
    assert cmd.items[0]["picked"]["account"] == str(k1.pk)
    press(f"vc:ok:{cmd.pk}")
    assert Expense.objects.get().account == k1


def test_service_error_shown_not_saved(env, tg, llm):
    llm.reply = {"transcript": "x", "items": [{"type": "expense", "category": "Internet", "price": 100000, "date": (TODAY + datetime.timedelta(days=2)).isoformat()}]}
    voice.handle_update(text_msg("x"))
    press(f"vc:ok:{last_cmd().pk}")
    assert not Expense.objects.exists()
    assert "Kelajak sana" in last_cmd().items[0]["result"]


# ------------------------------------------------------------------ kreditor

def test_creditor_out_and_in(env, tg, llm):
    llm.reply = {"transcript": "x", "items": [
        {"type": "creditor", "creditor": "MNSH", "direction": "out", "amount": 200000, "cash_type": "CASH"},
        {"type": "creditor", "creditor": "mnsh ilhomjon", "direction": "in", "amount": 500000, "cash_type": "CASH"}]}
    voice.handle_update(text_msg("Ilhomjon 200 ming olib ketdi, keyin 500 ming qo'ydi"))
    assert "G'aznadan chiqdi" in card_text(tg)
    press(f"vc:ok:{last_cmd().pk}")
    amounts = sorted(CreditorTransaction.objects.values_list("amount", flat=True))
    assert amounts == [Decimal(-500000), Decimal(200000)]
    assert fin.balance(env["cash"]) == 1_300_000


def test_creditor_direction_asked(env, tg, llm):
    llm.reply = {"transcript": "x", "items": [{"type": "creditor", "creditor": "MNSH", "amount": 100000}]}
    voice.handle_update(text_msg("MNSH 100 ming"))
    cmd = last_cmd()
    assert cmd.items[0]["need"]["field"] == "direction"
    press(f"vc:pk:{cmd.pk}:0:0")  # out
    press(f"vc:ok:{cmd.pk}")
    assert CreditorTransaction.objects.get().amount == 100000


# ------------------------------------------------------------------ tasdiqlar

@pytest.fixture
def contract(env):
    b = env["branch"]
    course = Course.objects.create(name="Frontend")
    course.branches.set([b])
    g = Group.objects.create(branch=b, course=course, day_pattern=DayPattern.objects.create(name="", weekdays=[1, 3, 5]),
                             time=LessonTime.objects.create(branch=b, start_time="14:00", end_time="16:00"),
                             teacher=env["cashier"], room=Room.objects.create(branch=b, name="1", capacity=10), start_date=TODAY, number=1)
    st = Student.objects.create(branch=b, first_name="Ali", last_name="Valiyev", phone1="901112233")
    return Contract.objects.create(branch=b, student=st, course=course, group=g, number=1, start_date=TODAY)


def test_confirm_transfers(env, tg, llm):
    t = fin.save_transfer(env["cashier"], {"sender_account": env["cash"], "receiver_account": env["card"], "amount": Decimal(400000)})
    llm.reply = {"transcript": "x", "items": [{"type": "confirm_transfer"}]}
    voice.handle_update(text_msg("o'tkazmalarni tasdiqla"))
    assert "400 000" in card_text(tg)
    press(f"vc:ok:{last_cmd().pk}")
    t.refresh_from_db()
    assert t.status == Confirm.CONFIRMED and t.confirmed_by == env["boss"]


def test_approve_noncash_and_edit_payment(env, tg, llm, contract):
    p = fin.save_payment(env["cashier"], {"contract": contract, "amount": Decimal(300000), "cash_type": "CARD", "date": TODAY})
    llm.reply = {"transcript": "x", "items": [{"type": "approve_payment", "what": "noncash", "student": "Ali Valiyev"}]}
    voice.handle_update(text_msg("Ali Valiyevning karta to'lovini tasdiqla"))
    press(f"vc:ok:{last_cmd().pk}")
    p.refresh_from_db()
    assert p.noncash_status == Confirm.CONFIRMED
    llm.reply = {"transcript": "x", "items": [{"type": "payment_edit", "student": "Valiyev", "set": {"amount": 350000}}]}
    voice.handle_update(text_msg("Valiyevning to'lovini 350 ming qil"))
    assert "300 000 → <b>350 000</b>" in card_text(tg)
    press(f"vc:ok:{last_cmd().pk}")
    p.refresh_from_db()
    assert p.amount == 350000 and p.noncash_status == Confirm.PENDING  # summa o'zgardi — qayta tasdiq


def test_payment_not_found(env, tg, llm, contract):
    llm.reply = {"transcript": "x", "items": [{"type": "payment_edit", "student": "Botir", "set": {"amount": 1}}]}
    voice.handle_update(text_msg("x"))
    assert "To'lov topilmadi" in card_text(tg) and "vc:ok" not in str(tg[-1])


# ------------------------------------------------------------------ oylik va topshiriq

def test_salary_payout_and_adjust(env, tg, llm):
    llm.reply = {"transcript": "x", "items": [
        {"type": "salary_payout", "employee": "Akbarxoja", "amount": 1000000, "cash_type": "CASH", "period": "2026-09"},
        {"type": "salary_adjust", "employee": "Akbarxo'ja", "bonus": 100000, "fine": 20000}]}
    voice.handle_update(text_msg("Akbarxo'jaga sentyabr oyligidan 1 million berdim, 100 ming bonus, 20 ming jarima"))
    press(f"vc:ok:{last_cmd().pk}")
    p = SalaryPayout.objects.get()
    assert p.user == env["cashier"] and (p.year, p.month) == (2026, 9) and p.amount == 1000000
    a = SalaryAssignment.objects.get()
    assert a.bonus == 100000 and a.fine == 20000 and (a.year, a.month) == (TODAY.year, TODAY.month)
    llm.reply = {"transcript": "x", "items": [{"type": "salary_adjust", "employee": "Akbarxo'ja", "bonus": 50000}]}
    voice.handle_update(text_msg("yana 50 ming bonus"))
    assert "100 000 → <b>150 000</b>" in card_text(tg)
    press(f"vc:ok:{last_cmd().pk}")
    a.refresh_from_db()
    assert a.bonus == 150000


def test_task(env, tg, llm):
    due = (timezone.localtime() + datetime.timedelta(days=1)).replace(hour=12, minute=0)
    llm.reply = {"transcript": "x", "items": [{"type": "task", "assignee": "Akbarxo'ja", "title": "Xonani tozalash", "due": due.strftime("%Y-%m-%dT%H:%M")}]}
    voice.handle_update(text_msg("Akbarxo'jaga ertaga 12 gacha xonani tozalashni topshir"))
    assert "botga ulanmagan" in card_text(tg)
    press(f"vc:ok:{last_cmd().pk}")
    t = StaffTask.objects.get()
    assert t.assignee == env["cashier"] and t.created_by == env["boss"] and timezone.localtime(t.due_at).hour == 12


# ------------------------------------------------------------------ tuzatish, bekor, ruxsat, savol

def test_edit_flow(env, tg, llm):
    llm.reply = {"transcript": "internet 300", "items": [{"type": "expense", "category": "Internet", "price": 300000}]}
    voice.handle_update(text_msg("internet 300 ming"))
    first = last_cmd()
    press(f"vc:ed:{first.pk}")
    llm.reply = {"transcript": "350 ming", "items": [{"type": "expense", "category": "Internet", "price": 350000}]}
    voice.handle_update(text_msg("summasi 350 ming"))
    assert "Oldingi xabar matni" in llm.calls[-1]["user"]
    first.refresh_from_db()
    second = last_cmd()
    assert first.status == VoiceCommand.Status.REPLACED and second.parent == first
    assert "allaqachon" in press(f"vc:ok:{first.pk}")
    press(f"vc:ok:{second.pk}")
    assert Expense.objects.get().total == 350000


def test_cancel(env, tg, llm):
    llm.reply = {"transcript": "x", "items": [{"type": "expense", "category": "Internet", "price": 1000}]}
    voice.handle_update(text_msg("x"))
    cmd = last_cmd()
    press(f"vc:no:{cmd.pk}")
    assert "allaqachon" in press(f"vc:ok:{cmd.pk}")
    assert not Expense.objects.exists()


def test_expired(env, tg, llm):
    llm.reply = {"transcript": "x", "items": [{"type": "expense", "category": "Internet", "price": 1000}]}
    voice.handle_update(text_msg("x"))
    cmd = last_cmd()
    VoiceCommand.objects.filter(pk=cmd.pk).update(created_at=timezone.now() - datetime.timedelta(hours=1))
    assert "Muddati" in press(f"vc:ok:{cmd.pk}")
    assert not Expense.objects.exists()


def test_only_boss(env, tg, llm, make_user):
    other = make_user("ADMINISTRATOR_HISOBCHI")
    TelegramLink.objects.create(user=other, chat_id=777)
    msg = {"chat": {"id": 777, "type": "private"}, "voice": {"file_id": "F", "duration": 2}, "date": 1}
    assert voice.handle_update(msg) is True and "faqat Bosh menejer" in tg[-1][1]["text"]
    assert voice.handle_update({"chat": {"id": 777, "type": "private"}, "text": "salom"}) is False  # oddiy matn — eski ishlov (kod)
    assert voice.handle_update(text_msg("/start")) is False
    assert not llm.calls
    # boshqa xodim boshliqning tugmasini bosa olmaydi
    llm.reply = {"transcript": "x", "items": [{"type": "expense", "category": "Internet", "price": 1000}]}
    voice.handle_update(text_msg("x"))
    assert voice.on_callback({"id": "c", "from": {"id": 777}, "data": f"vc:ok:{last_cmd().pk}"}) == "Ruxsat yo'q"


def test_question_answered_via_ai(env, tg, llm, monkeypatch):
    from apps.ai_assistant import services as ai

    monkeypatch.setattr(ai, "ask", lambda user, q: {"status": "ok", "title": "Bu oy xarajatlar", "note": "", "error": "", "columns": ["jami"],
                                                     "rows": [[1250000]], "truncated": False, "row_count": 1, "explain": []})
    llm.reply = {"transcript": "Bu oy qancha xarajat bo'ldi", "items": [{"type": "question", "text": "Bu oy qancha xarajat bo'ldi?"}]}
    voice.handle_update(text_msg("Bu oy qancha xarajat bo'ldi"))
    assert last_cmd().status == VoiceCommand.Status.ANSWERED
    assert "1 250 000" in tg[-1][1]["text"]


def test_gemini_audio_payload(settings, monkeypatch):
    settings.AI_API_KEY, settings.AI_PROVIDER = "k", "gemini"
    seen = {}

    def post(url, headers, body, timeout, retries=0):
        seen["body"] = body
        return {"candidates": [{"content": {"parts": [{"text": '{"items": []}'}]}}]}

    monkeypatch.setattr(providers, "_post", post)
    assert providers.complete_json("s", "u", audio=(b"abc", "audio/ogg")) == {"items": []}
    part = seen["body"]["contents"][0]["parts"][1]["inline_data"]
    assert part == {"mime_type": "audio/ogg", "data": "YWJj"}
    settings.AI_PROVIDER = "openai"
    with pytest.raises(providers.ProviderError):
        providers.complete_json("s", "u", audio=(b"abc", "audio/ogg"))
