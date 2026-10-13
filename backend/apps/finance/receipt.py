"""To'lov cheki (PDF, 80 mm kenglik). Har so'rovda joriy ma'lumotdan yaratiladi — to'lov o'zgarsa chek ham yangi (CLAUDE.md 7.5)."""

import io

from django.utils import timezone
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .services import fmt

W = 80 * mm
# Standart PDF shriftlarida yo'q belgilar o'rniga
REPLACE = str.maketrans({"ʻ": "'", "ʼ": "'", "‘": "'", "’": "'", "№": "N", "—": "-", "–": "-", "«": '"', "»": '"'})


def _t(s):
    return str(s or "").translate(REPLACE)


def build(p, balance):
    """p — Payment (contract, student, group, discount_type yuklangan). balance — to'lovdan keyingi shartnoma balansi."""
    c = p.contract
    rows = [
        ("Sana", f"{p.date:%d.%m.%Y} {timezone.localtime(p.created_at):%H:%M}"),
        ("Talaba", c.student.full_name),
        ("Shartnoma", f"N{c.number} - {c.group}"),
        ("To'lov shakli", p.get_cash_type_display() if p.amount else "-"),
    ]
    if p.discount:
        rows.append(("Chegirma", f"{fmt(p.discount)} so'm ({p.discount_type})"))
    rows += [("Summa", f"{fmt(p.amount)} so'm"), ("Balans (to'lovdan keyin)", f"{fmt(balance)} so'm"), ("Qabul qildi", p.created_by or "-")]
    pending = "Tasdiqlashga" in (p.discount_status, p.noncash_status)
    h = (52 + 9 * len(rows) + (8 if pending else 0)) * mm
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=(W, h))
    pdf.setTitle(_t(f"Chek N{p.number}"))
    y = h - 12 * mm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(6 * mm, y, "codial")
    pdf.setFillColor(HexColor("#F26A1B"))
    pdf.drawString(6 * mm + pdf.stringWidth("codial", "Helvetica-Bold", 16), y, ".")
    pdf.setFillColor(HexColor("#000000"))
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(W - 6 * mm, y + 2 * mm, _t(f"IT o'quv markazi - {p.branch}"))
    pdf.drawRightString(W - 6 * mm, y - 2 * mm, "Farg'ona sh.")
    y -= 12 * mm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(W / 2, y, _t(f"TO'LOV CHEKI N {p.number}"))
    y -= 4 * mm
    pdf.line(6 * mm, y, W - 6 * mm, y)
    y -= 7 * mm
    for label, value in rows:
        big = label == "Summa"
        pdf.setFont("Helvetica", 8)
        pdf.drawString(6 * mm, y, _t(label))
        pdf.setFont("Helvetica-Bold", 11 if big else 8)
        text = _t(value)
        while pdf.stringWidth(text, "Helvetica-Bold", 11 if big else 8) > W - 40 * mm and len(text) > 4:
            text = text[:-2]
        pdf.drawRightString(W - 6 * mm, y, text)
        y -= 9 * mm
    if pending:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawCentredString(W / 2, y, "TASDIQLANMAGAN")
        y -= 8 * mm
    pdf.line(6 * mm, y + 4 * mm, W - 6 * mm, y + 4 * mm)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(W / 2, y - 2 * mm, "Rahmat!")
    pdf.showPage()
    pdf.save()
    return buf.getvalue()
