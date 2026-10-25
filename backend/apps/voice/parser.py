"""Gemini: ovozli (yoki yozma) xabarni matnga aylantiradi va bandlarga ajratadi — savol, amal, topshiriq.
Gemini'ga ovoz va ma'lumotnomalar nomlari boradi (buyurtmachi qarori 2026-10-25: ovozda talaba ismi aytilishi mumkin).
Nomlarni bazadagi yozuvga server moslaydi (`actions`), Gemini faqat aytilgan so'zni qaytaradi."""

import datetime
import json
import re
import time

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.ai_assistant import providers
from apps.core.models import Status
from apps.core.permissions import role_code
from apps.core.roles import RoleCode
from apps.crm.models import Lead
from apps.education.models import Contract, Group
from apps.finance.models import Account, Creditor
from apps.references.models import Branch, Course, DiscountType, ExpenseCategory, LeadSource

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
- {"type":"task_update","assignee":"...","title":"topshiriq mavzusidan so'zlar","action":"done|cancel|edit","due":"YYYY-MM-DDTHH:MM","new_title":null,"comment":"..."}
  Mavjud ochiq topshiriqni bajarildi deb yopish, bekor qilish yoki muddatini/mavzusini o'zgartirish.
- {"type":"payment","student":"o'quvchi ismi familiyasi","amount":0,"cash_type":"CASH|CARD|BANK","account":"...","discount":null,"discount_type":null,"date":"YYYY-MM-DD","comment":"..."}
  YANGI to'lov qabul qilish (o'quvchi pul to'ladi).
- {"type":"transfer","from_account":"...","to_account":"...","amount":0,"date":"YYYY-MM-DD","comment":"..."} — YANGI ichki o'tkazma (bir g'aznadan boshqasiga naqd pul).
- {"type":"exchange","account":"...","from_type":"CASH|CARD|BANK","amount":0,"to_type":"CASH|CARD|BANK","amount_to":null,"comment":"..."}
  Pul ayirboshlash (masalan kartadagi pulni naqdga yechish); amount_to — olingan summa (komissiya bo'lsa kam), aytilmasa null.
- {"type":"delete","entity":"expense|creditor|payment|salary_payout|transfer|exchange","find":{...}} — MAVJUD yozuvni o'chirish.
- {"type":"edit","entity":"expense|creditor|payment|salary_payout|transfer","find":{...},"set":{...}} — MAVJUD yozuvni o'zgartirish.
  find — yozuvni topish uchun aytilgan belgilar (faqat aytilganlari): {"date","amount","cash_type","category","name","account","creditor","employee",
  "student","from_account","to_account","latest":true — «oxirgi kiritilgan» deyilsa}. amount — yozuvning HOZIRGI summasi.
  set — yangi qiymatlar (faqat o'zgaradiganlari): xarajat {"category","name","quantity","price","cash_type","account","date","period","comment"},
  kreditor {"amount","direction","cash_type","account","date","comment"}, to'lov {"amount","date","cash_type","discount","discount_type","comment"},
  oylik berish {"amount","kind","period","cash_type","account","date","comment"}, o'tkazma {"amount","to_account","date","comment"}.
- {"type":"lead_create","first_name":"...","last_name":"...","phone1":"9 raqam","phone2":"9 raqam","source":"...","course":"...","status":"1–8","callback_at":"YYYY-MM-DDTHH:MM",
   "group":null,"demo_date":null,"age_group":null,"social":null,"laptop":null,"gender":"Erkak|Ayol|null","comment":"..."} — yangi lid (yangi talaba).
- {"type":"lead_update","student":"ism familiya yoki telefon","set":{"status":"1–8","callback_at":"YYYY-MM-DDTHH:MM","course":null,"source":null,"group":null,
   "demo_date":null,"demo_attended":true|false|null},"comment":"lidga izoh","delete":false}
  Mavjud lidni o'zgartirish (holat, qayta bog'lanish vaqti, guruh, sinov darsi), izoh qo'shish yoki o'chirish (delete:true).
- {"type":"contract_create","student":"...","course":null,"group":"kurs va guruh raqami, masalan «Frontend 3»","start_date":null,"type":"Pullik|Grant"} — shartnoma tuzish.
- {"type":"contract_update","student":"...","set":{"stop":true,"end_date":null,"stop_reason":"...","group":null,"start_date":null,"type":null,"resume":false,"comment":null}}
  Shartnomani to'xtatish (stop:true, sabab ro'yxatdan), boshqa guruhga o'tkazish, boshlanish sanasi, turi, qayta faollashtirish (resume:true).
- {"type":"attendance","group":"«Frontend 3»","date":"YYYY-MM-DD","all_present":true,"marks":[{"student":"...","status":"Keldi|Sababli|Besabab","comment":"sababi"}]}
  Davomat: marks — aytilganlar; all_present=true — qolganlari «Keldi» («hammasi keldi, faqat Ali kelmadi»). Faqat aytilganlar bo'lsa all_present=false.
- {"type":"attendance_contact","student":"...","date":null,"contact":"Gaplashildi|Tushib bo'lmadi|Noto'g'ri raqam|Bog'lanishga","comment":"..."}
  Kelmagan o'quvchi bilan bog'lanish natijasi.
- {"type":"unknown","text":"..."} — tushunilmagan yoki tizimda bunday amal yo'q.

Qoidalar:
- Summalar butun so'mda: «300 ming» = 300000, «1,5 million» = 1500000, «yarim million» = 500000.
- Nisbiy sanalar («bugun», «kecha», «dushanba kuni») — «Xabar yozilgan vaqt»ga nisbatan. Sana aytilmasa null (server xabar sanasini oladi).
- cash_type: naqd → CASH, karta/plastik/click/payme → CARD, bank/perechisleniye/hisob raqam → BANK. Aytilmasa null.
- Nomlarni (kategoriya, g'azna, kreditor, xodim, chegirma turi) iloji bo'lsa quyidagi ro'yxatlardagi yozilishida qaytaring.
- «O'chir», «o'chirib tashla», «noto'g'ri kiritibman, olib tashla» — delete; hech qachon manfiy summali yangi yozuv yaratmang.
- «… ni … qil», «o'zgartir», «tuzat», «… emas … bo'lsin» mavjud yozuv haqida bo'lsa — edit; payment_edit o'rniga ham edit (entity "payment") ishlating.
- Avvalgi xabarda yaratilgan yoki hozir aytilgan yozuvni tuzatish/o'chirish so'ralsa — delete/edit (find'da aytilgan belgilar bilan).
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
    lines.append("Lid manbalari: " + ", ".join(LeadSource.objects.filter(status=Status.ACTIVE).order_by("name").values_list("name", flat=True)))
    lines.append("Kurslar: " + ", ".join(Course.objects.filter(status=Status.ACTIVE).order_by("name").values_list("name", flat=True)))
    groups = Group.objects.filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate())).select_related("course", "teacher", "time", "day_pattern")
    lines.append("Guruhlar (kurs raqam — ustoz, kunlar, vaqt): " + "; ".join(
        f"{g.course.name} {g.number} — {g.teacher.full_name if g.teacher_id else ''}, {g.day_pattern.name}, {g.time.start_time:%H:%M}" for g in groups.order_by("course__name", "number")))
    lines.append("Lid holatlari: " + ", ".join(f"{s.value}. {s.label}" for s in Lead.LeadStatus))
    lines.append("Shartnoma to'xtatish sabablari: " + ", ".join(Contract.StopReason.values))
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


def _recent(user):
    """So'nggi 2 soatda bajarilgan buyruqlar — «hozir kiritganimni o'chir» kabi gaplar uchun kontekst."""
    from .models import VoiceCommand

    since = timezone.now() - datetime.timedelta(hours=2)
    rows = VoiceCommand.objects.filter(user=user, status=VoiceCommand.Status.DONE, created_at__gte=since).order_by("-created_at")[:3]
    lines = [f"- «{c.transcript[:200]}» → " + "; ".join(re.sub(r"<[^>]+>", "", i.get("result") or "")[:150] for i in c.items) for c in reversed(rows)]
    return ("So'nggi bajarilgan buyruqlar (kontekst uchun):\n" + "\n".join(lines) + "\n\n") if lines else ""


def parse(user, *, text="", audio=None, said_at=None, previous=None):
    """audio=(bytes, mime). previous — tuzatilayotgan buyruq (VoiceCommand). Qaytaradi: (dict, model, ms)."""
    if previous is not None:
        old = [{"type": i["type"], **i.get("raw", {})} for i in previous.items]
        prompt = (f"Oldingi xabar matni: «{previous.transcript}»\nOldingi bandlar: {json.dumps(old, ensure_ascii=False, default=str)}\n\n"
                  "Menejer tuzatish yubordi (quyida). Tuzatishni qo'llab, BARCHA bandlarni (o'zgarmaganlarini ham) to'liq qaytaring. "
                  "transcript — faqat tuzatish matni.\n\nTuzatish: ")
    else:
        prompt = _recent(user) + "Xabar: "
    prompt += text if text else "(ovozli xabar ilova qilingan)"
    t0 = time.monotonic()
    out = providers.complete_json(system_prompt(user, said_at), prompt, audio=audio, timeout=TIMEOUT_S)  # asosiy (tez) model, kuchli emas
    items = [i for i in (out.get("items") or []) if isinstance(i, dict) and i.get("type")]
    return ({"transcript": str(out.get("transcript") or text or "").strip(), "items": items, "reply": str(out.get("reply") or "").strip()},
            providers.used_model(), int((time.monotonic() - t0) * 1000))
