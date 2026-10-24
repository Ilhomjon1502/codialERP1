"""Mijozlar boti: shartnoma raqami orqali ulanish (SMS kodi o'rniga) — telefon oxirgi 4 raqami bilan tasdiqlanadi, urinishlar cheklangan."""

import pytest

from apps.clientbot import services as bot
from apps.clientbot.models import BotAccount, BotLink, LinkAttempt
from apps.crm.models import Student
from tests.test_clientbot import on  # noqa: F401 — fixtures
from tests.test_sms_auto import env  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db


def prepare(env):  # noqa: F811
    """Talaba (1-tel ...2231, 2-tel ...9999, vasiy ...6671) va uning shartnomasi."""
    st = env["student"](1)
    Student.objects.filter(pk=st.pk).update(phone2="911119999")
    st.refresh_from_db()
    c = env["contract"](st)
    return st, c


def say(chat, text):
    return bot.handle_message(chat, text)


def test_contract_number_then_last4_links_guardian_without_leaking_name(env, on):  # noqa: F811
    st, c = prepare(env)
    r = say(1, str(c.number))
    assert len(r) == 1 and "oxirgi 4 raqamini" in r[0].text and st.first_name not in r[0].text  # tekshiruvdan oldin ism aytilmaydi
    assert not BotLink.objects.exists() and BotAccount.objects.get(chat_id=1).state["step"] == "verify"
    r = say(1, "6671")  # vasiy raqami oxiri
    assert "vasiysi" in r[0].text and r[0].markup["keyboard"]  # menyu bilan
    ln = BotLink.objects.get()
    assert ln.student == st and ln.role == "Vasiy" and ln.phone == st.parent.phone and ln.is_active
    assert BotAccount.objects.get(chat_id=1).state == {} and not LinkAttempt.objects.exists()


@pytest.mark.parametrize("fmt", ["№{n}", "#{n}", "Shartnoma {n}", " {n} "])
def test_number_formats_and_student_phone(env, on, fmt):  # noqa: F811
    st, c = prepare(env)
    assert "oxirgi 4 raqamini" in say(2, fmt.format(n=c.number))[0].text
    r = say(2, "+998 90 111 22 31")  # to'liq raqam yozilsa ham oxirgi 4 raqami olinadi
    assert "Salom" in r[0].text and BotLink.objects.get().role == "Talaba"


def test_second_phone_asks_who(env, on):  # noqa: F811
    st, c = prepare(env)
    say(3, str(c.number))
    r = say(3, "9999")
    assert "kimsiz" in r[0].text and BotLink.objects.get().role == ""


def test_wrong_digits_and_unknown_number(env, on):  # noqa: F811
    st, c = prepare(env)
    assert "topilmadi" in say(4, "99999")[0].text
    assert BotAccount.objects.get(chat_id=4).fails == 1
    say(4, str(c.number))
    assert "4 ta raqamni" in say(4, "12")[0].text  # 4 tadan kam — urinish hisoblanmaydi
    assert "mos kelmadi" in say(4, "0000")[0].text
    assert not BotLink.objects.exists() and BotAccount.objects.get(chat_id=4).state["step"] == "verify"
    assert LinkAttempt.objects.get(student=st).fails == 1


def test_student_locked_after_five_wrong_tries_across_accounts(env, on):  # noqa: F811
    st, c = prepare(env)
    for chat in (5, 6):  # har akkaunt 8 tadan kam, lekin talaba bo'yicha jami 5 dan oshadi
        say(chat, str(c.number))
        for _ in range(3 if chat == 5 else 2):
            say(chat, "0000")
    say(7, str(c.number))
    r = say(7, "6671")  # to'g'ri raqam ham o'tmaydi — talaba bloklangan
    assert "limiti tugadi" in r[0].text and not BotLink.objects.exists()
    LinkAttempt.objects.filter(student=st).update(since=bot.timezone.now() - bot.datetime.timedelta(hours=25))  # sutka o'tgach — ochiladi
    assert "vasiysi" in say(7, "6671")[0].text


def test_account_rate_limit_applies(env, on):  # noqa: F811
    prepare(env)
    for _ in range(bot.MAX_FAILS):
        say(8, "9999999")  # mavjud bo'lmagan shartnoma
    assert "Juda ko'p" in say(8, "1")[0].text


def test_start_cancels_pending_verification(env, on):  # noqa: F811
    st, c = prepare(env)
    say(9, str(c.number))
    say(9, "/start")
    assert BotAccount.objects.get(chat_id=9).state == {}
    assert "topilmadi" in say(9, "6671")[0].text  # raqam endi tekshiruv javobi emas — shartnoma raqami sifatida qidiriladi


def test_deleted_contract_and_account_cap(env, on):  # noqa: F811
    st, c = prepare(env)
    inv = bot.invite_for(st, st.parent.phone)
    for chat in (11, 12, 13):
        say(chat, str(c.number))
        assert "vasiysi" in say(chat, "6671")[0].text
    say(14, str(c.number))
    assert "cheklovga" in say(14, "6671")[0].text  # bir raqamga ko'pi bilan 3 akkaunt
    assert inv.links.count() == 3
    c.is_deleted = True
    c.save()
    assert "topilmadi" in say(15, str(c.number))[0].text
