"""Gemini: ovozli (yoki yozma) xabarni matnga aylantiradi va bandlarga ajratadi — savol, amal, topshiriq.
Gemini'ga ovoz va ma'lumotnomalar nomlari boradi (buyurtmachi qarori 2026-10-25: ovozda talaba ismi aytilishi mumkin).
Nomlarni bazadagi yozuvga server moslaydi (`actions`), Gemini faqat aytilgan so'zni qaytaradi."""

import json
import time

from django.utils import timezone

from apps.accounts.models import User
from apps.ai_assistant import providers
from apps.core.models import Status
from apps.core.permissions import role_code
from apps.core.roles import RoleCode
from apps.finance.models import Account, Creditor
from apps.references.models import Branch, DiscountType, ExpenseCategory

TIMEOUT_S = 15  # bitta model uchun; javob bermasa — zaxira modelga o'tadi (2026-10-25: gemini-3.7-flash 60 s javobsiz qolgan, flash-lite ~2 s)

WEEKDAYS = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]

SCHEMA = """Javob — faqat JSON:
{
  "transcript": "ovozli xabarning so'zma-so'z matni (yozma xabar bo'lsa — o'zi)",
  "items": [ ...bandlar... ],
  "reply": "hech narsa tushunilmasa yoki salom-alik bo'lsa — qisqa javob, aks holda bo'sh"
}

Band turlari (har biri {"type": ...}; aytilmagan maydonni yozmang yoki null qiling, o'ylab topmang):
- {"type":"question","text":"..."} — ma'lumot so'ralsa (qancha, kim, nechta, ro'yxat, hisobot, balans, qarzdorlar…). Savolni to'liq, mustaqil gap qilib yozing.
- {"type":"expense","category":"...","name":"nima uchun","quantity":1,"price":0,"cash_type":"CASH|CARD|BANK","account":"g'azna nomi","date":"YYYY-MM-DD","period":"YYYY-MM","comment":"..."}
  Xarajat. Faqat umumiy summa aytilsa quantity=1, price=summa. period — faqat boshqa oy uchun deyilsa («sentyabr uchun internet»).
- {"type":"creditor","creditor":"...","direction":"out|in","amount":0,"cash_type":"CASH|CARD|BANK","account":"...","date":"YYYY-MM-DD","comment":"..."}
  Tashqi pul oqimi (kreditorlar). direction: "out" — pul g'aznadan chiqdi (kreditor olib ketdi, qarz qaytarildi);
  "in" — pul g'aznaga kirdi (kreditordan qarz olindi, u pul berdi/kiritdi). amount doim musbat.
- {"type":"confirm_transfer","from_account":"...","to_account":"...","amount":null,"date":null} — ichki o'tkazmalarni tasdiqlash.
  «Hammasini tasdiqla» bo'lsa filtrlarni bo'sh qoldiring.
- {"type":"approve_payment","what":"noncash|discount|both","student":"...","amount":null,"date":null} — naqdsiz to'lov va/yoki chegirmani tasdiqlash.
- {"type":"payment_edit","student":"o'quvchi ismi familiyasi","date":"to'lov sanasi yoki null","amount":"hozirgi summa yoki null",
   "set":{"amount":null,"date":null,"cash_type":null,"discount":null,"discount_type":null,"comment":null}} — mavjud to'lovni o'zgartirish; set ichida faqat o'zgaradiganlari.
- {"type":"salary_payout","employee":"...","amount":0,"kind":"O'zgarmas|Bonus|KPI","period":"YYYY-MM","cash_type":"CASH|CARD|BANK","account":"...","date":"YYYY-MM-DD","comment":"..."}
  Xodimga oylik berildi (g'aznadan pul chiqdi). period — qaysi oy oyligi (aytilmasa null).
- {"type":"salary_adjust","employee":"...","period":"YYYY-MM","bonus":null,"fine":null,"fixed":null,"kpi":null,"mode":"add|set","comment":"..."}
  Oylik belgilashga bonus, jarima, belgilangan oylik yoki qo'lda KPI. mode: "add" — qo'shish («yana 100 ming bonus», «50 ming jarima yoz»), "set" — aniq qiymat («bonusi 300 ming bo'lsin»).
- {"type":"task","assignee":"xodim","title":"qisqa mavzu","description":"batafsil","due":"YYYY-MM-DDTHH:MM"} — xodimga topshiriq. Muddat aytilmasa due=null.
- {"type":"unknown","text":"..."} — tushunilmagan qism.

Qoidalar:
- Summalar butun so'mda: «300 ming» = 300000, «1,5 million» = 1500000, «yarim million» = 500000.
- Nisbiy sanalar («bugun», «kecha», «dushanba kuni») — «Xabar yozilgan vaqt»ga nisbatan. Sana aytilmasa null (server xabar sanasini oladi).
- cash_type: naqd → CASH, karta/plastik/click/payme → CARD, bank/perechisleniye/hisob raqam → BANK. Aytilmasa null.
- Nomlarni (kategoriya, g'azna, kreditor, xodim, chegirma turi) iloji bo'lsa quyidagi ro'yxatlardagi yozilishida qaytaring.
- Bitta xabarda bir nechta band bo'lishi mumkin — hammasini alohida yozing."""


def _ctx_lists(user):
    lines = []
    branches = list(Branch.objects.filter(status=Status.ACTIVE).values_list("name", flat=True))
    if len(branches) > 1:
        lines.append("Filiallar: " + ", ".join(branches))
    accs = Account.objects.filter(status=Status.ACTIVE).order_by("name")
    lines.append("G'aznalar: " + ", ".join(f"{a.name} ({a.get_cash_type_display()})" for a in accs))
    cats = ExpenseCategory.objects.filter(allowed_roles__code=role_code(user)).distinct().order_by("name")
    lines.append("Xarajat kategoriyalari: " + ", ".join(f"{c.name}" for c in cats))
    lines.append("Kreditorlar: " + ", ".join(Creditor.objects.order_by("name").values_list("name", flat=True)))
    lines.append("Chegirma turlari: " + ", ".join(DiscountType.objects.order_by("name").values_list("name", flat=True)))
    staff = User.objects.filter(employment_status=User.Employment.ACTIVE).exclude(role__code=RoleCode.BOSHQA).select_related("role").order_by("full_name")
    lines.append("Xodimlar: " + ", ".join(f"{u.full_name} ({u.role.name if u.role else '—'})" for u in staff))
    return "\n".join(lines)


def system_prompt(user, said_at):
    now = timezone.localtime()
    said = timezone.localtime(said_at) if said_at else now
    return (
        "Siz Codial o'quv markazi (Farg'ona) ERP tizimining Telegram yordamchisisiz. Bosh menejer o'zbek tilida (ba'zan ruscha so'zlar bilan) "
        "ovozli yoki yozma xabar yuboradi: ma'lumot so'raydi, moliyaviy amal yoki xodimga topshiriq aytadi. Xabarni bandlarga ajrating.\n\n"
        f"Hozir: {now:%Y-%m-%d %H:%M}, {WEEKDAYS[now.weekday()]}.\n"
        f"Xabar yozilgan vaqt: {said:%Y-%m-%d %H:%M}, {WEEKDAYS[said.weekday()]}.\n\n"
        f"{_ctx_lists(user)}\n\n{SCHEMA}"
    )


def parse(user, *, text="", audio=None, said_at=None, previous=None):
    """audio=(bytes, mime). previous — tuzatilayotgan buyruq (VoiceCommand). Qaytaradi: (dict, model, ms)."""
    if previous is not None:
        old = [{"type": i["type"], **i.get("raw", {})} for i in previous.items]
        prompt = (f"Oldingi xabar matni: «{previous.transcript}»\nOldingi bandlar: {json.dumps(old, ensure_ascii=False, default=str)}\n\n"
                  "Menejer tuzatish yubordi (quyida). Tuzatishni qo'llab, BARCHA bandlarni (o'zgarmaganlarini ham) to'liq qaytaring. "
                  "transcript — faqat tuzatish matni.\n\nTuzatish: ")
    else:
        prompt = "Xabar: "
    prompt += text if text else "(ovozli xabar ilova qilingan)"
    t0 = time.monotonic()
    out = providers.complete_json(system_prompt(user, said_at), prompt, audio=audio, timeout=TIMEOUT_S)  # asosiy (tez) model, kuchli emas
    items = [i for i in (out.get("items") or []) if isinstance(i, dict) and i.get("type")]
    return ({"transcript": str(out.get("transcript") or text or "").strip(), "items": items, "reply": str(out.get("reply") or "").strip()},
            providers.used_model(), int((time.monotonic() - t0) * 1000))
