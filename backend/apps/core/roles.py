"""Rollar, bo'limlar, boshlang'ich ruxsatlar matritsasi va tahrirlash muddatlari (CLAUDE.md 6).

Bo'limlar va matritsa buyurtmachi ma'qullagan prototipdan olingan (prototype/assets/js/core.js).
Ruxsat harflari: v ko'rish, a qo'shish, e tahrirlash, d o'chirish, p tasdiqlash.
"""

from django.db import models


class RoleCode(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    BOSH_MENEJER = "BOSH_MENEJER", "Bosh menejer"
    FILIAL_MENEJERI = "FILIAL_MENEJERI", "Filial menejeri"
    ADMINISTRATOR = "ADMINISTRATOR", "Administrator"
    ADMINISTRATOR_HISOBCHI = "ADMINISTRATOR_HISOBCHI", "Administrator+Hisobchi"
    HISOBCHI = "HISOBCHI", "Hisobchi"
    USTOZ = "USTOZ", "Ustoz"
    YORDAMCHI = "YORDAMCHI", "Yordamchi ustoz"
    USTOZ_YORDAMCHI = "USTOZ_YORDAMCHI", "Ustoz+Yordamchi"
    MARKETOLOG = "MARKETOLOG", "Marketolog"
    ASOSCHI = "ASOSCHI", "Asoschi"
    BOSHQA = "BOSHQA", "Boshqa"


TOP_ROLES = {RoleCode.ADMIN, RoleCode.BOSH_MENEJER}
VIEW_ALL_ROLES = TOP_ROLES | {RoleCode.ASOSCHI}  # hamma filial va hamma ma'lumotni KO'RADI (asoschi faqat ko'radi — tahrirlash huquqlari TOP_ROLES'da)
MANAGER_ROLES = TOP_ROLES | {RoleCode.FILIAL_MENEJERI}
TEACHER_ROLES = {RoleCode.USTOZ, RoleCode.YORDAMCHI, RoleCode.USTOZ_YORDAMCHI}

OPS = "vaedp"
OP_LABELS = {"v": "ko'rish", "a": "qo'shish", "e": "tahrirlash", "d": "o'chirish", "p": "tasdiqlash"}

SECTIONS = [
    ("dashboard", "Bosh sahifa"), ("leads", "Lidlar"), ("contracts", "Shartnomalar"), ("payments", "To'lovlar"),
    ("debtors", "Qarzdorlar"), ("attendance", "Davomatlar"), ("profit", "Foyda"),
    ("expenses", "Xarajatlar"), ("export", "Shartnoma yuklash"), ("groupAnalysis", "Guruhlar tahlili"),
    ("groups", "Guruhlar"), ("approvals", "Tasdiqlashlar"),
    ("salaries", "Oyliklar"), ("transfers", "Ichki pul oqimi"), ("creditors", "Tashqi pul oqimi"),
    ("exchange", "Pul ayirboshlash"), ("accounts", "G'aznalar"), ("evaluations", "Baholash"),
    ("parentCalls", "Ota-onalar bilan aloqa"), ("settings", "Sozlamalar"),
    ("ai", "AI yordamchi"), ("audit", "Audit tarixi"), ("staffTasks", "Topshiriqlar"),
    ("calls", "Qo'ng'iroqlar"), ("sms", "SMS"), ("clientbot", "Telegram bot (mijozlar)"),
    ("founderReport", "Kunlik hisobot (asoschi)"),
]
SECTION_KEYS = [k for k, _ in SECTIONS]

_S = {"AD": "ADMIN", "BM": "BOSH_MENEJER", "FM": "FILIAL_MENEJERI", "A": "ADMINISTRATOR",
      "AH": "ADMINISTRATOR_HISOBCHI", "H": "HISOBCHI", "U": "USTOZ", "Y": "YORDAMCHI", "UY": "USTOZ_YORDAMCHI", "M": "MARKETOLOG", "AS": "ASOSCHI"}
_MATRIX = {
    "dashboard": {"AD": "v", "BM": "v", "FM": "v", "A": "v", "AH": "v", "H": "v", "U": "v", "Y": "v", "UY": "v", "M": "v", "AS": "v"},
    "leads": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vaed", "AH": "vaed", "H": "v", "U": "v", "Y": "v", "UY": "v", "M": "vaed", "AS": "v"},
    "contracts": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vaed", "AH": "vaed", "H": "v", "U": "v", "UY": "v", "M": "v", "AS": "v"},
    "payments": {"AD": "vaedp", "BM": "vaedp", "FM": "vp", "AH": "vaed", "H": "vaed", "AS": "v"},
    "debtors": {"AD": "v", "BM": "v", "FM": "v", "AH": "v", "H": "v", "AS": "v"},
    "attendance": {"AD": "vaedp", "BM": "vaedp", "FM": "vaedp", "A": "vaedp", "AH": "vaedp", "U": "vae", "UY": "vae", "Y": "v", "AS": "v"},
    "profit": {"AD": "v", "BM": "v", "AS": "v"},
    "expenses": {"AD": "vaed", "BM": "vaed", "FM": "v", "AH": "vaed", "H": "vaed", "AS": "v"},
    "export": {"AD": "v", "BM": "v", "FM": "v", "A": "v", "AH": "v", "H": "v", "AS": "v"},
    "groupAnalysis": {"AD": "v", "BM": "v", "FM": "v", "A": "v", "AH": "v", "H": "v", "U": "v", "M": "v", "AS": "v"},
    "groups": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vae", "AH": "vae", "H": "v", "U": "v", "Y": "v", "UY": "v", "M": "v", "AS": "v"},
    "approvals": {"AD": "v", "BM": "v", "FM": "v", "A": "v", "AH": "v", "H": "v", "U": "v", "UY": "v", "AS": "v"},
    "salaries": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "AH": "va", "H": "va", "A": "v", "U": "v", "Y": "v", "UY": "v", "AS": "v"},
    "transfers": {"AD": "vaed", "BM": "vaed", "FM": "v", "AH": "vaed", "H": "vaed", "AS": "v"},
    "creditors": {"AD": "vaed", "BM": "vaed", "AS": "v"},
    "exchange": {"AD": "vae", "BM": "vae", "AS": "v"},
    "accounts": {"AD": "vaed", "BM": "vaed", "FM": "v", "AH": "v", "H": "v", "AS": "v"},
    "evaluations": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vae", "AH": "vae", "AS": "v"},
    "parentCalls": {"AD": "vaed", "BM": "vaed", "FM": "vae", "A": "vae", "AH": "vae", "H": "v", "U": "vae", "UY": "vae", "Y": "v", "AS": "v"},
    "settings": {"AD": "vaed", "BM": "vaed", "FM": "vae", "A": "v", "AH": "v", "H": "v", "AS": "v"},
    "ai": {"BM": "v", "AS": "v"},
    "audit": {"AD": "v", "BM": "v", "AS": "v"},
    "staffTasks": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vae", "AH": "vae", "H": "vae", "U": "vae", "Y": "vae", "UY": "vae", "M": "vae", "AS": "v"},
    "calls": {"AD": "vaed", "BM": "vaed", "FM": "ve", "A": "ve", "AH": "ve", "M": "v", "AS": "v"},
    "sms": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vae", "AH": "vae", "H": "v", "AS": "v"},
    "clientbot": {"AD": "vaed", "BM": "vaed", "FM": "ve", "A": "ve", "AH": "ve", "M": "v", "AS": "v"},
    "founderReport": {"AS": "v"},  # asoschi: tizimda hamma narsani ko'radi (faqat ko'rish), botga esa faqat kunlik hisobot keladi (2026-10-25)
}
DEFAULT_PERMISSIONS = {
    code: {sec: next((ops for short, ops in _MATRIX.get(sec, {}).items() if _S[short] == code), "") for sec in SECTION_KEYS}
    for code in RoleCode.values
}

# RolePower: kim qaysi rollarni tayinlay oladi (prototipdagi assignable())
_ALL = list(RoleCode.values)
DEFAULT_ROLE_POWER = {
    RoleCode.ADMIN: _ALL,
    RoleCode.BOSH_MENEJER: [r for r in _ALL if r not in (RoleCode.ADMIN, RoleCode.ASOSCHI)],  # asoschini faqat Admin tayinlaydi
    RoleCode.FILIAL_MENEJERI: [
        RoleCode.ADMINISTRATOR, RoleCode.ADMINISTRATOR_HISOBCHI, RoleCode.HISOBCHI, RoleCode.USTOZ,
        RoleCode.YORDAMCHI, RoleCode.USTOZ_YORDAMCHI, RoleCode.MARKETOLOG, RoleCode.BOSHQA,
    ],
}

# Tahrirlash/o'chirish muddati (kun): None — cheklovsiz, 0 — faqat bugun, -1 — mumkin emas (CLAUDE.md 6.4)
_TODAY_ONLY_FOR_ADMINISTRATORS = {"payments", "expenses", "transfers", "salaries"}


def edit_days(role_code, section):
    if role_code in TOP_ROLES:
        return None
    if role_code == RoleCode.FILIAL_MENEJERI:
        return 15
    if role_code == RoleCode.ADMINISTRATOR_HISOBCHI and section in ("attendance", "leads"):
        return None  # buyurtmachi qarori: Administrator+Hisobchi davomatni (2026-10-19) va lidlarni (2026-10-21) sanadan qat'i nazar to'liq tahrirlaydi
    if role_code in (RoleCode.ADMINISTRATOR, RoleCode.ADMINISTRATOR_HISOBCHI, RoleCode.MARKETOLOG):
        return 0 if section in _TODAY_ONLY_FOR_ADMINISTRATORS else 7
    if role_code == RoleCode.HISOBCHI or role_code in TEACHER_ROLES:
        return 0
    return -1


def edit_rule_text(days):
    if days is None:
        return "cheklovsiz"
    if days == 0:
        return "faqat bugun"
    if days < 0:
        return "yo'q"
    return f"oxirgi {days} kun"


def edit_days_table():
    """Front-end uchun: {rol: {bo'lim: kun|None}}"""
    return {code: {sec: edit_days(code, sec) for sec in SECTION_KEYS} for code in RoleCode.values}
