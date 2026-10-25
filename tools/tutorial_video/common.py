"""Darslar ro'yxati va umumiy bo'laklar.

Ssenariy qoidalari: matn qisqa va oddiy; har bir harakatdan oldin «nima uchun», keyin «qanday»;
yangi tushuncha birinchi marta chiqqanda izohlanadi.
"""
from datetime import date, timedelta

LESSONS = {}


def lesson(num, slug, title, **opts):
    def deco(fn):
        fn.opts = opts
        LESSONS[num] = (slug, title, fn)
        return fn
    return deco


async def outro(L, nxt):
    await L.card("Codial ERP · yoʻriqnoma", "Dars tugadi", f"Keyingi dars: {nxt}" if nxt else "Barcha darslar tugadi",
                 text=f"Dars shu yerda tugadi. Keyingi darsda: {nxt}." if nxt else "Barcha darslar shu yerda tugadi. Ishingizga omad!", hold=1.2)


def tomorrow_10():
    return (date.today() + timedelta(days=1)).isoformat() + "T10:00"


SAVE = ".overlay:last-child [data-submit]"
MODAL = ".overlay:last-child .modal"


def f(name, tag="input"):
    """Forma maydoni selektori."""
    return f'.overlay:last-child [data-f="{name}"] {tag}'


async def option(L, sel, n=0, match=None):
    """Ro'yxatdagi n-chi bo'sh bo'lmagan variant qiymati (match — matnda bo'lishi kerak bo'lgan bo'lak)."""
    return await L.js("""([sel, n, m]) => { const s = document.querySelector(sel); if (!s) return null;
        const o = [...s.options].filter(o => o.value && !o.disabled && (!m || o.textContent.includes(m))); return o[n] ? o[n].value : null; }""",
                      [sel, n, match])
