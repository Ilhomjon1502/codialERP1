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
    BOSHQA = "BOSHQA", "Boshqa"


TOP_ROLES = {RoleCode.ADMIN, RoleCode.BOSH_MENEJER}
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
    ("ai", "AI yordamchi"), ("audit", "Audit tarixi"),
]
SECTION_KEYS = [k for k, _ in SECTIONS]

_S = {"AD": "ADMIN", "BM": "BOSH_MENEJER", "FM": "FILIAL_MENEJERI", "A": "ADMINISTRATOR",
      "AH": "ADMINISTRATOR_HISOBCHI", "H": "HISOBCHI", "U": "USTOZ", "Y": "YORDAMCHI", "UY": "USTOZ_YORDAMCHI"}
_MATRIX = {
    "dashboard": {"AD": "v", "BM": "v", "FM": "v", "A": "v", "AH": "v", "H": "v", "U": "v", "Y": "v", "UY": "v"},
    "leads": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vaed", "AH": "vaed", "H": "v", "U": "v", "Y": "v", "UY": "v"},
    "contracts": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vaed", "AH": "vaed", "H": "v", "U": "v", "UY": "v"},
    "payments": {"AD": "vaedp", "BM": "vaedp", "FM": "vp", "AH": "vaed", "H": "vaed"},
    "debtors": {"AD": "v", "BM": "v", "FM": "v", "AH": "v", "H": "v"},
    "attendance": {"AD": "vaedp", "BM": "vaedp", "FM": "vaedp", "A": "vaedp", "AH": "vaedp", "U": "vae", "UY": "vae", "Y": "v"},
    "profit": {"AD": "v", "BM": "v"},
    "expenses": {"AD": "vaed", "BM": "vaed", "FM": "v", "AH": "vaed", "H": "vaed"},
    "export": {"AD": "v", "BM": "v", "FM": "v", "A": "v", "AH": "v", "H": "v"},
    "groupAnalysis": {"AD": "v", "BM": "v", "FM": "v", "A": "v", "AH": "v", "H": "v", "U": "v"},
    "groups": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vae", "AH": "vae", "H": "v", "U": "v", "Y": "v", "UY": "v"},
    "approvals": {"AD": "v", "BM": "v", "FM": "v", "A": "v", "AH": "v", "H": "v", "U": "v", "UY": "v"},
    "salaries": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "AH": "va", "H": "va", "A": "v", "U": "v", "Y": "v", "UY": "v"},
    "transfers": {"AD": "vaed", "BM": "vaed", "FM": "v", "AH": "vaed", "H": "vaed"},
    "creditors": {"AD": "vaed", "BM": "vaed"},
    "exchange": {"AD": "vae", "BM": "vae"},
    "accounts": {"AD": "vaed", "BM": "vaed", "FM": "v", "AH": "v", "H": "v"},
    "evaluations": {"AD": "vaed", "BM": "vaed", "FM": "vaed", "A": "vae", "AH": "vae"},
    "parentCalls": {"AD": "vaed", "BM": "vaed", "FM": "vae", "A": "vae", "AH": "vae", "H": "v", "U": "vae", "UY": "vae", "Y": "v"},
    "settings": {"AD": "vaed", "BM": "vaed", "FM": "vae", "A": "v", "AH": "v", "H": "v"},
    "ai": {"BM": "v"},
    "audit": {"AD": "v", "BM": "v"},
}
DEFAULT_PERMISSIONS = {
    code: {sec: next((ops for short, ops in _MATRIX.get(sec, {}).items() if _S[short] == code), "") for sec in SECTION_KEYS}
    for code in RoleCode.values
}

# RolePower: kim qaysi rollarni tayinlay oladi (prototipdagi assignable())
_ALL = list(RoleCode.values)
DEFAULT_ROLE_POWER = {
    RoleCode.ADMIN: _ALL,
    RoleCode.BOSH_MENEJER: [r for r in _ALL if r != RoleCode.ADMIN],
    RoleCode.FILIAL_MENEJERI: [
        RoleCode.ADMINISTRATOR, RoleCode.ADMINISTRATOR_HISOBCHI, RoleCode.HISOBCHI, RoleCode.USTOZ,
        RoleCode.YORDAMCHI, RoleCode.USTOZ_YORDAMCHI, RoleCode.BOSHQA,
    ],
}

# Tahrirlash/o'chirish muddati (kun): None — cheklovsiz, 0 — faqat bugun, -1 — mumkin emas (CLAUDE.md 6.4)
_TODAY_ONLY_FOR_ADMINISTRATORS = {"payments", "expenses", "transfers", "salaries"}


def edit_days(role_code, section):
    if role_code in TOP_ROLES:
        return None
    if role_code == RoleCode.FILIAL_MENEJERI:
        return 15
    if role_code in (RoleCode.ADMINISTRATOR, RoleCode.ADMINISTRATOR_HISOBCHI):
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
