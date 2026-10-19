# Qarzdorlar → «Shu oy to'lovi»

Markazda to'lov oyning 10-sanasigacha oldindan olinadi, davomat esa kech olinishi mumkin. Shuning uchun «Qarzdorlar»da ikki tab bor:

- **Shu oy to'lovi** (standart) — shu oy uchun to'lamagan o'quvchilar, **kurs narxi** bo'yicha. Davomatga bog'liq emas.
- **Qarz (davomat bo'yicha)** — avvalgi ro'yxat: o'tilgan darslar bo'yicha yozilgan qarz.

## Hisob

```
oy boshidagi balans = boshlang'ich qoldiq + oy boshigacha yozilgan qarz − oy boshigacha to'lov va chegirma
shu oy narxi        = kurs narxi × (shartnoma amal qilgan dars kunlari ÷ oydagi dars kunlari)   (pro-rata)
to'lashi kerak      = oy boshidagi balans + shu oy narxi − shu oydagi to'lov va chegirma     (0 dan kam bo'lsa ro'yxatda yo'q)
```

- Oldindan to'lagan (balansi minusda) o'quvchi shu oy uchun kredit bilan yopiladi.
- Eski qarz «to'lashi kerak»ga qo'shiladi.
- Oy o'rtasida boshlagan o'quvchi uchun narx dars kunlari nisbatida (masalan 16-sanadan: 7/13).
- Grant, tugagan va hali boshlanmagan shartnomalar kirmaydi (tugaganlarning qarzi «Qarz» tabida).
- Kurs narxi kiritilmagan bo'lsa «narx yo'q» belgisi chiqadi (faqat eski qarz hisoblanadi).

## Muddat

Muddat kuni — Sozlamalar → Filiallar → «Oylik to'lov muddati» (standart 10). Shu kundan keyin qator «Muddati o'tgan · N kun» (qizil) bo'ladi.

## Telegram

08:30 ish rejasi va dars boshlanishidan 10 daqiqa oldingi eslatma endi shu hisob bo'yicha chiqadi (muddati o'tganlar 🔴). Rejaga filial bo'yicha «Muddati o'tgan» jami ham qo'shiladi.

API: `GET /api/v1/debtors/month/?month=YYYY-MM&course=&search=&state=wait|overdue`. Kod: `backend/apps/education/dues.py`.
