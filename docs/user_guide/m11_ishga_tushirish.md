# Haqiqiy ishga tushirish (M11)

Qaror (2026-10-14): alohida sinov muhiti yo'q. **https://erp.codialinfo.uz** — haqiqiy tizim. Bot (`@bildirishnomaERP1bot`) va AI kaliti o'sha-o'sha qoladi. 1-noyabrdan xodimlar AppSheet o'rniga shu tizimda ishlaydi. Ekranlar AppSheet'dagidek, shuning uchun alohida o'qitish shart emas.

## 1. Tayyorlash (hozir — 31-oktabrgacha)

Dasturchi bajaradi, buyurtmachi tasdiqlagandan keyin:
1. Zaxira: `bash deploy/backup.sh test`.
2. Demo ma'lumotlarni tozalash:
   ```bash
   python manage.py prepare_production --keep ilhomjon.office@gmail.com            # sinov: nima o'chadi
   python manage.py prepare_production --keep ilhomjon.office@gmail.com --commit   # o'chirish
   ```
   - **Saqlanadi:** rollar va ruxsatlar, davomat statuslari, Emirat filiali, Bosh menejer akkaunti (paroli va Telegram bog'lanishi bilan).
   - **O'chadi:** demo xodimlar va qolgan hamma ma'lumot.
3. Joriy Excel bilan import (`import_appsheet --commit`): faol shartnomalar, talabalar, guruhlar, ustozlar.

Bosh menejer qo'lda kiritadi (Sozlamalar):
- **G'aznalar** (boshlang'ich qoldig'i bilan), filialning asosiy va naqdsiz g'aznasi;
- **Kurs narxlari** (noyabrdan);
- **Oydagi dars soni**, noyabr uchun. 1-noyabr soat 06:00 da taklif avtomatik tayyorlanadi, siz tekshirib tasdiqlaysiz;
- **KPI stavkalari** (ustoz va yordamchilar);
- **Chegirma turlari, xarajat kategoriyalari, lid manbalari**;
- **Qolgan xodimlar:** administratorlar, hisobchilar. Ularga parol xati qo'shilganda o'zi ketadi;
- «Ishdan ketgan» holatida ko'chgan ikki yordamchi (agar ishlayotgan bo'lsa) → «Faol».

Narx va dars soni kiritilmasa, qarz va KPI hisoblanmaydi va bosh sahifada ogohlantirish chiqadi.

## 2. O'tish kuni (31-oktabr kechqurun yoki 1-noyabr ertalab)

1. AppSheet'dan oxirgi .xlsx faylni oling (Fayl → Yuklab olish → Excel).
2. Qayta import. Dublikat yaratilmaydi; oraliqda AppSheet'da tugagan shartnomalar yopiladi, yangilari qo'shiladi.
3. Xodimlarga parol o'rnatish xatlari: `python manage.py send_invites` (ro'yxat) → `--send`.
4. AppSheet'da yozishni to'xtating. U faqat eski ma'lumotlarni ko'rish uchun qoladi.

## 3. Monitoring

- Har 5 daqiqada sayt tekshiriladi (`deploy/healthcheck.sh`). Javob bo'lmasa, sayt o'zi qayta ishga tushadi. Tiklanmasa yoki server diski 90% to'lsa, Bosh menejerga Telegram xabari keladi.
- Har kuni 03:15 da baza zaxirasi olinadi (30 kun saqlanadi). Tavsiya: serverdan tashqariga ham nusxa olib turing (Hetzner Backups yoki haftada bir kompyuteringizga).

## Serverda import buyrug'i (dasturchi uchun)

```bash
install -d -m 700 /srv/import                      # Excel shu yerga (scp), checkout'ga emas
cd /srv/codial-test/deploy
docker compose --env-file .env cp /srv/import/Codial.xlsx web:/tmp/appsheet.xlsx
docker compose --env-file .env exec -T -u root web chmod 644 /tmp/appsheet.xlsx
docker compose --env-file .env exec -T web python manage.py import_appsheet --file /tmp/appsheet.xlsx --on 2026-11-01            # sinov
docker compose --env-file .env exec -T web python manage.py import_appsheet --file /tmp/appsheet.xlsx --on 2026-11-01 --commit
docker compose --env-file .env exec -T -u root web rm -f /tmp/appsheet.xlsx && shred -u /srv/import/Codial.xlsx
```

Server SSH'ni qisqa vaqtda ko'p ulanishda vaqtincha bloklaydi — buyruqlarni bitta ulanishda bajaring.

## 2026-10-14 da bajarildi

- Zaxira `codial-test-20261014-1119` → demo tozalandi. Faqat Bosh menejer akkaunti, rollar (10), ruxsatlar (220), davomat statuslari va Emirat qoldi.
- `Codial1.1.xlsx` dan import: 73 shartnoma, 73 talaba, 21 guruh, 4 kurs, 7 ustoz va yordamchi. Xatolar yo'q.
- Excel serverdan o'chirildi. Monitoring yoqildi.

