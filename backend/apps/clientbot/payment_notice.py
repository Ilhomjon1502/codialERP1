"""To'lov kiritilganda botga ulangan o'quvchi va vasiylarga xabar (faqat bot orqali; ulanmagan talabaga hech narsa ketmaydi).

Xabar: summa, to'lov shakli, chegirma, sana, chek raqami, naqdsiz to'lov tasdiq kutayotgani va shartnomaning joriy balansi (qarz yoki oldindan to'langan).
Faqat yangi to'lov kiritilganda (`finance.services.save_payment`); chegirma-only yozuvlarga (masalan tavsiya bonusi) ketmaydi.
Filial sozlamasida o'chirib qo'yish mumkin (`BotConfig.finance_in_bot`: hozircha o'chiq — to'lov va balans botda ko'rsatilmaydi). Xato to'lovni saqlashga xalaqit bermaydi.
"""

import logging
from decimal import Decimal
from html import escape

from apps.calls.sms import money
from apps.education.models import Contract
from apps.education.services import with_balance
from apps.finance.models import Confirm

from . import services as bot
from .cabinet import CASH
from .models import BotAccount, ClientOutbox

log = logging.getLogger(__name__)


def text_for(p):
    c = p.contract
    bal = with_balance(Contract.objects.filter(pk=c.pk)).first().balance or Decimal(0)
    lines = [f"💳 <b>To'lov qabul qilindi</b>\n{escape(c.student.first_name)} {escape(c.student.last_name)} · {escape(c.course.name)}",
             f"Summa: <b>{money(p.amount)}</b> so'm ({CASH.get(p.cash_type, p.cash_type or '—')})"]
    if p.discount:
        lines.append(f"Chegirma: {money(p.discount)} so'm")
    lines.append(f"Sana: {p.date:%d.%m.%Y} · chek №{p.number}")
    if p.noncash_status == Confirm.PENDING:
        lines.append("⏳ Naqdsiz to'lov tasdiqlanishi kutilmoqda")
    lines.append(f"Balans: {'qarz <b>' + money(bal) + '</b> so\'m' if bal > 0 else 'oldindan to\'langan <b>' + money(-bal) + '</b> so\'m' if bal < 0 else 'qarz yo\'q'}")
    lines.append("Rahmat! 🙏")
    return "\n".join(lines)


def notify(p):
    """Yangi to'lov: talabaga ulangan hamma faol akkauntga (o'quvchi va vasiylar). Qaytaradi: yuborilgan xabarlar soni."""
    try:
        if not bot.configured() or not p.amount:
            return 0
        student = p.contract.student
        if not bot.get_config(p.contract.branch).finance_in_bot:
            return 0
        accounts = list(BotAccount.objects.filter(links__student=student, links__is_active=True, blocked=False).distinct())
        if not accounts:
            return 0
        text = text_for(p)
        n = 0
        for acc in accounts:
            if not ClientOutbox.objects.filter(account=acc, key=f"payment:{p.pk}").exists():
                ClientOutbox.objects.create(account=acc, kind="To'lov", key=f"payment:{p.pk}", text=text, student=student, contract=p.contract)
                n += 1
        return n
    except Exception:  # noqa: BLE001 — xabar to'lovni buzmasin
        log.exception("To'lov haqida xabar tayyorlanmadi")
        return 0
