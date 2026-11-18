"""Instagram/Facebook lidlarining kunlik hisobot holatlari (2026-11-18, buyurtmachi qolipi «Lid_hisoboti_shablon»).

Qolipda 22 ta status, tartibi shu yerdagi `OUTCOMES` bilan bir xil (varaqdagi F3:F24 qatorlari). Uch guruh:
  neytral  — F3:F5   (Yangi lid, Ajidaniya, Bog'lanib bo'lmadi)
  sifatli  — F6:F11  (Maslahat … Markaz o'quvchisi)
  sifatsiz — F12:F24 (qizil qatorlar)
Administrator «Gaplashdim» bosganda shulardan birini tanlaydi: qayta aloqa belgilasa — `CALLBACK_OUTCOMES`, yopsa — `CLOSE_OUTCOMES`.
Hisobotda «haqiqiy» holat `effective()` bilan aniqlanadi (tanlanmagan eski yozuvlar uchun ham)."""

NEUTRAL, QUALITY, BAD = "neytral", "sifatli", "sifatsiz"
GROUP_LABELS = {NEUTRAL: "Neytral", QUALITY: "Sifatli", BAD: "Sifatsiz"}

# (kod, nomi, guruh) — varaq qatorlari tartibida
OUTCOMES = [
    ("new", "Yangi lid", NEUTRAL),
    ("hesitate", "Ajidaniya", NEUTRAL),
    ("unreachable", "Bog'lanib bo'lmadi", NEUTRAL),
    ("consult", "Maslahat", QUALITY),
    ("quality", "Kachestvni lead", QUALITY),
    ("incoming", "Kiruvchi qo'ng'iroq", QUALITY),
    ("demo", "Demoga yozildi", QUALITY),
    ("schedule", "Grafik to'g'ri kelmadi", QUALITY),
    ("center_student", "Markaz o'quvchisi", QUALITY),
    ("elsewhere", "Boshqa joyda o'qiyabdi", BAD),
    ("age", "Yosh to'g'ri kelmadi", BAD),
    ("online", "Online kerak", BAD),
    ("other_dept", "Savdo boshqa bo'limni so'radi", BAD),
    ("duplicate", "Qo'shimcha raqam dublikat", BAD),
    ("spam", "Spam", BAD),
    ("unreachable_bad", "Bog'lanib bo'lmadi (sifatsiz)", BAD),
    ("staff_talk", "Xodimlar o'rtasidagi suhbat", BAD),
    ("no_course", "Bizda yo'q kurs", BAD),
    ("location", "Location to'g'ri kelmadi", BAD),
    ("no_payment", "To'lov qobiliyati yo'q", BAD),
    ("region", "Boshqa viloyat", BAD),
    ("bad", "Sifatsiz lead", BAD),
]
CODES = [c for c, _, _ in OUTCOMES]
LABEL = {c: n for c, n, _ in OUTCOMES}
GROUP = {c: g for c, _, g in OUTCOMES}

CALLBACK_OUTCOMES = ["hesitate", "unreachable", "consult"]  # qayta aloqa belgilanganda
CLOSE_OUTCOMES = CODES[CODES.index("schedule"):]  # «Yopilgan Leadlar» blokidagi 15 ta sabab (varaqdagi 10–24-qatorlar)
LEGACY_CLOSED = "bad"  # sabab saqlanmagan eski yopilgan yozuvlar
LEGACY_CALLBACK = "hesitate"  # holat tanlanmagan eski «qayta aloqa» yozuvlari

REPORT_KINDS = ("Instagram", "Facebook")  # hisobotga faqat reklama lidlari; sayt kirmaydi
CALLED_US = ("Kiruvchi", "Javobsiz", "Rad etilgan")  # lid o'zi qo'ng'iroq qilgan (CallRecord.direction)
DEMO_LEAD_STATUSES = ("3", "4", "5")  # bog'langan haqiqiy lid sinov darsiga yozilgan/qatnashgan/o'qishni boshlagan


def options(codes):
    return [[c, LABEL[c]] for c in codes]


def effective(item, called=False):
    """Kiruvchi lidning hisobotdagi holat kodi.
    Tanlangan holat (`outcome`) birinchi; bo'lmasa — yozuv holatidan: bog'langan lid sinov darsiga yozilgan bo'lsa «demo», aks holda «quality»;
    yangi, lekin lid o'zi qo'ng'iroq qilgan bo'lsa «incoming»."""
    st = item.status
    if st == "linked":
        return "demo" if item.lead_id and item.lead.status in DEMO_LEAD_STATUSES else "quality"
    if item.outcome in LABEL:
        return item.outcome
    if st == "rejected":
        return LEGACY_CLOSED
    if st == "callback":
        return LEGACY_CALLBACK
    return "incoming" if called else "new"
