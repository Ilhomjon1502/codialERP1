# Codial ERP — AppSheet tizimini Django'da qayta qurish

> Claude Code uchun asosiy topshiriq hujjati. Har bir sessiya shu fayldan boshlanadi.
> Hujjat tili o'zbekcha (lotin). Kod, model va o'zgaruvchi nomlari inglizcha.

---

## 0. Joriy holat (2026-10-19) — yangi kelgan dasturchi shu yerdan boshlasin

> **Yangi sessiya: avval pastdagi «Keyingi sessiya uchun (2026-10-18)» blokini o'qing** — u eng so'nggi holat, ochiq ishlar va ish usullari. Eng yangi qo'shimcha — «2026-10-19 da qo'shilganlar: Qo'ng'iroqlar» (Android ilova).

**Qisqasi:** prototip ma'qullandi va muzlatildi. **M1–M11 tayyor: 2026-10-18 dan haqiqiy tizim ishga tushdi, AppSheet to'xtatildi**: haqiqiy tizim (`backend/` — Django + DRF API, `frontend/` — prototip ekranlari API'ga ulangan) **Hetzner serverida ishlayapti**. Keyingi ish — buyurtmachining yangi so'rovlari. Telegram bot tokeni (`deploy/set-telegram.sh`) va Gemini kaliti (`deploy/set-ai.sh`) kiritilgan — buni faqat buyurtmachi o'zi qiladi. Buyurtmachi «boshla» deganda boshlanadi. **«50% chegirmalar», «Talaba vazifalari» va «Baholash bo'limi» (ustoz → talaba) olib tashlangan** (buyurtmachi qarori 2026-10-13).

| Bosqich | Holat |
|---|---|
| AppSheet tahlili, shu CLAUDE.md | ✅ |
| Prototip (`prototype/`) va buyurtmachi so'ragan 11 ta o'zgarish (20.6) | ✅ ma'qullangan, **endi o'zgartirilmaydi** |
| Arxitektura (`docs/architecture.md`): API + prototip interfeysi, Hetzner | ✅ tasdiqlangan 2026-10-12 |
| **M1** — backend, kirish/parol, rollar va ruxsatlar, filial doirasi, audit, Sozlamalar, Audit tarixi, front-end ulandi | ✅ 2026-10-12, 37 test, https://erp.codialinfo.uz da |
| **M2** — CRM: talabalar, ota-onalar, lidlar (voronka, ro'yxat, statistika, kartochka, izohlar, talaba ma'lumotlarini to'ldirish) | ✅ 2026-10-13, 52 test |
| **M3** — guruhlar, shartnomalar, qarzdorlar, davomat (olish, kelmaganlar, statistika, qoldirilgan darslar), qarz va KPI hisobi va qayta hisoblash, lid → shartnoma | ✅ 2026-10-13, 70 test |
| **M4** — moliya: to'lovlar (chegirma limiti, tasdiqlar, PDF chek), CashMovement ledger va g'azna balansi, o'tkazmalar, ayirboshlash, xarajatlar, kreditorlar, Tasdiqlashlar, «To'lov qilganlar» | ✅ 2026-10-13, 84 test |
| **M5** — oyliklar: KPI stavkalari (qayta hisoblash bilan), oylik belgilash (nusxa), hisoblangan KPI daraxti, oylik berish (g'azna jurnaliga), xodim balansi | ✅ 2026-10-13, 100 test (9 tasi JS sintaksis) |
| **M6** — ustozni baholash (talaba → ustoz), ota-onalar bilan aloqa (daraxt), Excel (.xlsx) eksport; vazifalar, baholash bo'limi va 50% chegirma — olib tashlangan | ✅ 2026-10-13, 104 test |
| **M7** — bosh sahifa (guruhlar to'lishi), foyda oyma-oy, statistika (oylik, voronka, birinchi to'lovchilar) | ✅ 2026-10-13, 106 test |
| **M8** — Telegram bot: bog'lash, xabarlar navbati, 6 xil xabar, davomat eslatmasi va kunlik hisobot (cron) | ✅ 2026-10-13, 111 test |
| **M9** — AI yordamchi (Bosh menejer): Gemini → SQL → server tekshiruvi → jadval/diagramma, ma'lumot LLM'ga bormaydi | ✅ 2026-10-14, 134 test |
| **M10** — AppSheet importi: faqat faol shartnomalar + kerakli talaba/guruh/ustoz, qarzsiz (`import_appsheet`, sinov rejimi standart) | ✅ 2026-10-14, 140 test; sinov: 73 shartnoma, 21 guruh, xatosiz |
| **M11** — haqiqiy ishga tushirish: alohida sinov muhiti yo'q, hozirgi erp.codialinfo.uz haqiqiy tizim bo'ladi; `prepare_production` (demo tozalash), takroriy importda tugagan shartnomalarni yopish, `send_invites`, `/api/v1/health/` + `deploy/healthcheck.sh` | ✅ 2026-10-18: o'tish bajarildi — 83 shartnoma boshlang'ich qarz bilan, 61 ochiq lid, narx/dars soni, KPI, g'azna qoldiqlari (`importer/extra.py`) |
| **Topshiriqlar** (2026-10-16) — xodimlar bir-biriga topshiriq beradi, bot eslatadi (`apps/tasks`, `docs/user_guide/topshiriqlar.md`) | ✅ |
| **Qo'ng'iroqlar** (2026-10-19) — qabul telefonidagi (Android) qo'ng'iroqlar ERP'ga (19:00 BM hisobotida ham — `daily_report.calls_section`): `apps/calls` (CallDevice, CallRecord; ulash kodi → token, `/calls/ingest/`, CRM bilan solishtirish, javobsizga qayta qo'ng'iroq, statistika), `frontend/assets/js/pages-calls.js`, Android ilova `android/` (Java, `build.ps1`), `docs/user_guide/qongiroqlar.md`. Suhbat yozuvi — **kerak emas** (buyurtmachi qarori 2026-10-21: telefonda faqat Google Telefon, murakkab) | ✅ kod; telefonda sinov kutilmoqda |
| **To'lovga tavsiya** (2026-10-19; 10-20 da nomi o'zgardi: qarz emas, eslatma; «✓ To'lov qilgan» tugmasi shu oy uchun ro'yxat va Telegram'dan olib tashlaydi — `DueDismissal`) — Qarzdorlar → «To'lovga tavsiya»: oy kurs narxi bo'yicha (pro-rata, kredit va eski qarz hisobga olinadi), davomatga bog'liq emas; muddat `Branch.payment_due_day` (10); Telegram 08:30 reja va 10 daqiqa oldingi eslatma shu hisobda (`education/dues.py`, `docs/user_guide/shu_oy_tolovi.md`) | ✅ kod, 195 test; serverga joylanmagan |
| **Foyda → «Hisobot olish»** (2026-10-20) — Google Sheets oylik moliyaviy hisobot: bitta doimiy fayl, har oy yangi varaq (namuna «Codial moliyaviy hisobot.xlsx»: tushum, ustozlar/xodimlar oyligi, xarajatlar izoh-note bilan, foyda, 75/25 taqsimot, kreditorlardan olingan pullar; «avvalgi oydan» qoldiq qo'lda). Faqat Admin/BM. `apps/reports/sheet_report.py`, `gsheets.py` (service account, urllib + cryptography), `deploy/set-google.sh`, `gsheets_check`, `docs/user_guide/foyda_google_sheets.md`. Eski 20 varaq ko'chirilmagan (oktabr 2026 dan) | ✅ serverda ishlayapti (2026-10-20, kalit kiritilgan, birinchi hisobot olindi) |
| **Lid: qayta bog'lanish vaqti** (2026-10-21) — 1- va 8-statuslarda sana+vaqt majburiy (`Lead.callback_at`), vaqti kelganda bot hamma Administrator+Hisobchiga tugmalar bilan eslatadi (✅ Qo'ng'iroq qilindi · +1 soat · Ertaga; `lc:` callback), 8:30 rejada muddati o'tganlar. `crm.services.validate_callback/callback_action`, `reminders.lead_callbacks`, `docs/user_guide/qayta_boglanish.md` | ✅ kod, testlar; serverga joylanmagan |
| **Qo'ng'iroqlar ↔ baza** (2026-10-21) — lid/shartnoma kartochkasida qo'ng'iroqlar tarixi va oxirgi aloqa; gaplashilgan qo'ng'iroqdan keyin «izoh yozing» (eslatma to'xtamaydi; `Lead.callback_talked_at`, `POST /leads/{id}/call-note/`, bot xabari); kelmagan talaba bilan bog'lanish (`POST /calls/{id}/absence-contact/`); voronka (manba → qo'ng'iroq → lid → shartnoma) va AI `analytics_calls`; `docs/user_guide/qongiroqlar.md` | ✅ kod, testlar; serverga joylanmagan |
| **SMS — to'lov eslatmasi** (2026-10-22) — qabul telefonining o'z SIM'idan (Android ilova 1.1), faqat administrator «Yuborish»ni bosganda: Qarzdorlar → «To'lovga tavsiya» → «SMS yuborish» (ko'rinib turgan ro'yxat) yoki qatordagi ✉ → qolip → server hisobi → tasdiq → navbat; talabaning hamma raqamiga (1-, 2-telefon, vasiy), shu oy olganlarga qayta ketmaydi. Qoliplar va jurnal — Qo'ng'iroqlar → «SMS». `apps/calls/sms.py` (SmsTemplate, SmsMessage; `queue_dues`, `outbox`, `report`), API `/sms/` (`dues/`, `retry/`, `cancel/`, `cancel-all/`, `summary/`), `/sms-templates/`, telefon uchun `/calls/sms/outbox/` va `/calls/sms/report/`; bo'lim `sms` (accounts/0011); Android `SmsSender`, `SmsSentReceiver` (navbat 8–21 da 30 s, tunda 10 daqiqa; SMS orasida 4 s; yuborishda WakeLock); `docs/user_guide/sms.md`. Menyu «Qo'ng'iroqlar va SMS», tab «SMS statistikasi» (`sms.stats`: holatlar, bo'laklar, kunlar, kimga, kim yubordi, SMS'dan keyin to'lov qilganlar); lid/shartnoma kartochkasida qo'ng'iroqlar yonida SMS tarixi (`crm.views.contact_history`, `sms.history`). APK 1.1 optimallashtirish: HTTP keep-alive (`disconnect()` yo'q), CallLog `_ID` bo'yicha faqat yangi qatorlar (+10 daqiqa zaxira; 1.0 dan bir marta 3 soat) | ✅ 2026-10-22 serverda (commit 2b57d91); APK 1.1 telefonga o'rnatilmagan |
| **Mijozlardan kelgan SMS** (2026-10-22, ilova 1.2) — telefon «Kirish qutisi»dan faqat oddiy raqamlardan (+998 XX…) kelgan SMS'larni `POST /calls/sms/inbox/` ga yuboradi (bank, Click/Payme, operator — telefondan chiqmaydi), SMS `_ID` bo'yicha + ContentObserver + `SmsReceivedReceiver`; `SmsMessage.direction` = Kiruvchi (status «Qabul qilindi», vaqti `sent_at`, `external_id`, talaba/vasiy/lid FK, faol shartnoma), `sms.ingest_inbox`, `sms.rematch`; noma'lum raqamlar ham saqlanadi («＋ Lid yaratish»), Telegram xabar yo'q (buyurtmachi qarori). Kartochkada yozishma (↙/↗), jurnalda «Kelgan/Yuborilgan» va «Noma'lum raqamlardan» filtrlari, statistikada kelgan SMS, noma'lumlar, «Eslatmaga javob yozdi». Ilova 1.2: qo'ng'iroqlar va kelgan SMS sutkada bir marta oxirgi 24 soat qayta yuboriladi (`CallSync.FULL_SCAN_MS`) | ✅ 2026-10-22 serverda, 244 test; APK 1.2 telefonga o'rnatilgan |
| **SMS yetkazilishi, ilova 1.3** (2026-10-22) — sinov SMS ERP'da «Yuborildi» bo'lib, qabul qiluvchiga **yetmadi** (qo'lda yozilgani yetdi): sabab noma'lum edi, chunki «Yuborildi» faqat operator SMS markaziga topshirilganini bildiradi. 1.3: delivery report (`SmsDeliveredReceiver`, 3GPP holat kodi: 0 yetdi, 0x20–0x3F kutiladi, 0x40+ yetmadi), yuborish xatosida tizim `errorCode`, ERP'ga SIM/operator ma'lumoti (`SmsMessage.detail`), `delivery`/`delivered_at` (calls/0004), `report` ga `stage` (sent/delivered) va `info`; jurnalda «✓✓ Yetkazildi / ✕ Yetkazilmadi / yetkazilishi noma'lum» va filtr, statistikada «Yetkazildi/Yetkazilmadi»; ilovada «ruxsat berilmagan» eski yozuvi o'zi o'chadi. Eslatma: SMS'ni telefonning «Xabarlar» ilovasida saqlab bo'lmaydi — Android buni faqat asosiy SMS ilovasiga ruxsat beradi | ✅ 2026-10-22 serverda (346152a); APK 1.3 telefonda, operator hisoboti ishlayapti. Sinov: matni «Test…» SMS qabul qiluvchi telefonining spam filtrida yashirilgan, «Assalomu alaykum» yetgan — SMS matni muhim |
| **Avtomatik SMS** (2026-10-23, buyurtmachi so'rovi) — 5 qoida (`SmsRule`, har filialda; boshida **o'chiq**, administrator Qo'ng'iroqlar va SMS → SMS → «Avtomatik SMS»da ko'rib, yoqadi): 1) **lid** — yangi lid yaratilganda hamma raqamiga, har yangi lidga («Codialga xush kelibsiz, AyTi ta'limini biz bilan o'rganing!»); 2) **shartnoma** — tuzilganda (faol yoki rejadagi): «{ism} {guruh} guruhiga qo'shildingiz.» (guruh «Kompyuter savodxonligi 192»); 3) **oy boshi** — 1-sana 10:00: shu oy narxini to'lamagan faol, Grant bo'lmagan shartnomalarga (`month_dues`), «To'lovga tavsiya»dan SMS olgan raqamga takror yo'q; 4) **oldindan to'lov bonusi** — 25-sana 10:00: kelasi oy uchun to'lamaganlarga, bonus «Avvaldan to'lov» chegirmasidan, `{kun}` oy tugashiga qolgan kun; 5) **kelmagan** — har kuni 08:00: oxirgi 3 kunda «Besabab», «Gaplashildi» emas, bir talabaga 3 kunda bittadan, `{kecha}` = «Kecha» yoki «21.10 kuni». `apps/calls/auto_sms.py` (`lead_created`/`contract_created` hook'lari `crm.services.create_lead` va `education.services.save_contract` da, `tick()` va `check_problems()` — `run_bot` har daqiqada), `SmsMessage.key` (takrorlanmaslik), `/sms-rules/` (+ `preview/`), Telegram `sms_problem` (Bosh menejerga: navbatda 15 daqiqadan ko'p, xato, yetkazilmadi, telefon ulanmagan; har SMS haqida bir marta) | ✅ kod, 263 test; serverga joylanmagan |
| **Kichik o'zgarishlar** (2026-10-21 … 10-22; hammasi `main` da) — 1) **Kunlik hisobot 19:00** aniqlashtirildi: «bugun +N yangi» = bugun qo'shilgan **yoki** bugun boshlangan (`start_date`) shartnomalar; «−N to'xtatildi» = bugun tugash sanasi kiritilganlar (AuditLog `Shartnoma` bo'yicha, sanasi qaysi kun bo'lishidan qat'i nazar); lidlarda «Bugun holati o'zgardi: N ta (4. … — 2 · 5. … — 1)» (AuditLog `Lid`, kun ichidagi birinchi eski va oxirgi yangi holat) — `daily_report.day_updates/stopped_contracts/lead_moves`, `tests/test_daily_counts.py`. 2) **Talaba formasi:** sharif **ixtiyoriy** (`validate_father_name` bo'sh qiymatni qabul qiladi; kiritilsa — nuqtasiz, kamida 3 harf); yangi vasiy qo'shilganda **kim bo'lishi majburiy** (`Parent.relation`: Ota, Ona, Aka, Uka, Opa, Singil, Amaki, Tog'a, Xola, Amma, Buvi, Bobo, Boshqa; `crm/0003`); ismi bo'sh bo'lsa kimligi ism o'rniga yoziladi, «Boshqa» bo'lsa ism shart. 3) **Ruxsat:** Administrator+Hisobchi **lidlarni** sanadan qat'i nazar muddatsiz tahrirlaydi (`roles.edit_days`, davomat kabi); 7 kunlik muddat faqat Administrator va Marketolog uchun (`docs/decisions.md`). 4) **Bot «🔄 Lid o'zgardi»** xabarida status raqami emas, nomi: «3. Sinov darsga yozildi ➡️ 5. O'qishni boshladi» (`notifications.services._lead_status`). 5) **Dublikat talabani birlashtirish** (AppSheet'dan ikki marta ko'chgan): `crm.services.merge_students(user, keep, drop)` — `drop` dagi shartnoma, qo'ng'iroq va SMS `keep` ga o'tadi, lidlar bittaga birlashadi (izohlar asosiy lidga), bo'sh maydonlar to'ldiriladi, `drop` soft delete, audit; buyruq `python manage.py merge_students --keep <id> --drop <id> [--by EMAIL] [--commit]` (`--commit`siz — sinov, hech narsa saqlanmaydi; ID ning boshi ham bo'ladi; faqat bir filial). | ✅ kod, 246 test; serverga joylanmagan (m12-52 va keyingilar) |
| **Mijozlar boti** (2026-10-24, B1) — o'quvchi va vasiylar uchun **alohida Telegram bot** (`apps/clientbot`, Docker `clientbot`, `run_clientbot`, token `deploy/set-clientbot.sh` — buyurtmachi o'zi kiritadi). Lid/shartnoma SMS'iga har raqam uchun kod va `t.me/<bot>?start=KOD` havolasi qo'shiladi (`calls/auto_sms._bot_suffix`); bot ulaydi (`BotInvite`/`BotLink`; vasiy yoki o'quvchi), lidga «Codialni qayerdan topdingiz?» so'raydi (`LeadSurvey`, admin manbasi o'zgarmaydi), «tanish» bo'lsa tavsiya qiluvchi ismi (`Referral`). Bosh menejer uchun Qo'ng'iroqlar va SMS → **Telegram bot** tabi (`pages-clientbot.js`; ulanganlar, ulanmaganlar, manba javoblari, tavsiyalar, sozlamalar: bonus 75 000 so'm), ruxsat bo'limi `clientbot` (accounts/0012). **Keyingi bosqichlar (rejalashtirilgan, buyurtmachi tasdiqlagan, `docs/decisions.md` 2026-10-24):** B2 — ✅ serverda; B3 — ✅ kod (`clientbot/cabinet.py`: to'lovlar, davomat, dars jadvali, to'lov muddati; menyu tugmalari, ko'p farzand tanlovi); B4 — ✅ kod (`clientbot/survey.py`: `SurveyQuestion`, `ExitSurvey`, `tick()` har daqiqada `run_clientbot` da, savollarni Bosh menejer boshqaradi, javoblar «Ketish so'rovnomasi» tabida); hozirgi talabalarni ulash — «Talabalar» tabida ommaviy taklif (`clientbot/invites.py`); B5 — ✅ kod (`clientbot/referrals.py`: lid to'lovlari yig'indisi ≥ oy narxining 50% bo'lganda tavsiya qiluvchining shartnomasiga 75 000 so'mlik «Tavsiya bonusi» chegirma yozuvi; `finance.services._referral_check` hook'i). `docs/user_guide/mijozlar_boti.md` | ✅ B1 serverda (2026-10-24, @codialstudentbot ishlayapti); **B2 kodi tayyor** — ulangan raqamga SMS o'rniga bot (`auto_sms.enqueue`, `clientbot.services.accounts_for/deliver`, `ClientOutbox` ga student/contract/lead/month/phone), qoidalar `demo` (sinov darsi) va `bot_reminder` (ulanish eslatmasi, `reminder_days`/`reminder_max`), «Telegram bot → Xabarlar» tabi; serverga joylanmagan |
| **AI yordamchi sifati** (2026-10-16) — ma'lumotlar holati, bo'sh natija sababi, `analytics_lessons` (`ai_assistant/context.py`) | ✅ 164 test |
| **Ovozli buyruqlar** (2026-10-25, buyurtmachi so'rovi) — faqat **Bosh menejer** xodimlar botiga ovozli yoki yozma xabar yuboradi (forward qilingan eski ovoz ham; sana — ovoz yozilgan kun): Gemini ovozni matnga aylantiradi va bandlarga ajratadi (`providers.complete_json(audio=…)`, `inline_data`). **Savol** — darhol javob (`ai_assistant.ask`, jadval 20 qatorgacha). **Amal va topshiriq** — yozma tasdiq kartasi: ✅ Tasdiqlash / ✏️ Tuzatish (yoki kartaga reply) / ❌ Bekor; noaniq nomda tanlash tugmalari; 30 daqiqada eskiradi. Amallar: xarajat, kreditor (out → +, in → −), o'tkazmalarni tasdiqlash, naqdsiz/chegirmani tasdiqlash, to'lovni o'zgartirish, oylik berish, oylik belgilash (bonus/jarima: add yoki set), topshiriq. Bajarish faqat mavjud servislar orqali; audit belgisi `audit.tagged()` («🎙 Telegram ovozli buyruq: «…»»). `apps/voice` (`VoiceCommand`, `parser`, `actions.HANDLERS`, `match`, `services`), `run_bot` → `voice.handle_update` / `vc:` callback, `notifications.download_file`, `docs/user_guide/ovozli_buyruq.md`. Shu kuni qo'shildi: mavjud yozuvni topib **o'chirish/o'zgartirish** (`voice/records.py`: xarajat, kreditor amali — o'chirib qayta kiritish, to'lov, oylik berish, o'tkazma, ayirboshlash; `find` + `set`, o'xshashlik bo'yicha qidiruv, «oxirgi kiritilgan»), yangi to'lov, o'tkazma, ayirboshlash, topshiriqni yopish/bekor/muddat; so'nggi 2 soatdagi bajarilgan buyruqlar Gemini'ga kontekst; **lid, shartnoma, davomat** (`voice/edu.py`: `lead_create` — 2 telefon majburiy, `lead_update` — holat/qayta bog'lanish/guruh/izoh/o'chirish (`crm.services.update_lead` — yangi, sayt qoidalari bilan), `contract_create` (lid → 5-holat), `contract_update` (to'xtatish+sabab, guruh, qayta faollashtirish), `attendance` (`edu.mark`, «hammasi keldi, faqat …»), `attendance_contact`); ismni moslashda aniq mos ustun (`records.score/best`); tushunilmasa — qila oladiganlar ro'yxati. AI: `analytics_accounts` da `cash_balance/card_balance/bank_balance`; `providers` javob bermagan modelni 5 daqiqa chetlab o'tadi, kuchli modelga 12 s | ✅ 2026-10-25 serverda |
| **Yo'riqnoma videolari** (2026-10-22 … 10-23) — Administrator+Hisobchi uchun 14 ta video (o'zbekcha ovoz `uz-UZ-MadinaNeural`, yoritish, yozuv, `.srt`): `tools/tutorial_video/` (Playwright + CDP screencast + ffmpeg, ssenariylar `l01.py`…`l14.py`, README). Haqiqiy bazaning **lokal nusxasida** yoziladi (`launch.json` → `video-copy`, 8010-port, soxta Telegram tokeni), telefonlar yashiriladi. Tizim o'zgarsa: `bash run.sh check NN` (tezkor sinov), `bash run.sh rec NN`. Natija `docs/video/` (git'ga kirmaydi) | ✅ 2026-10-23: 14 ta video, jami ~55 daqiqa |
| 18-bo'limdagi ochiq savollar | ⏳ takliflar `docs/architecture.md` 7-bo'limda; buyurtmachi javob bermasa takliflar qo'llanadi. 3-savol yopildi: 50% chegirma bo'limi olib tashlandi |
| Domen `codialinfo.uz` | ✅ buyurtmachiniki (ahost.uz). DNS: A `erp` → `77.42.9.23` (2026-10-13), Let's Encrypt SSL. Asosiy sayt (`@`, `www` — Vercel) va pochta yozuvlariga tegilmaydi |
| Pochta (SMTP) | ✅ 2026-10-13: Gmail (`ilhomjonibragimov1502@gmail.com`, App password `deploy/.env` da). Qayta sozlash: serverda `bash /srv/codial-test/deploy/set-smtp.sh` (parolni o'zi so'raydi) |

**Manzillar:**

| Nima | Qayerda |
|---|---|
| Haqiqiy tizim | **https://erp.codialinfo.uz** — **haqiqiy ma'lumot** (2026-10-14 dan; demo o'chirilgan). Serverdagi papka nomi tarixiy: `/srv/codial-test` — bu haqiqiy tizim, alohida prod yo'q. Zaxira manzil: https://test.77-42-9-23.sslip.io |
| Prototip (dizayn namunasi) | https://ilhomjon1502.github.io/codialERP1/ |
| Server | Hetzner CAX11 «codial-1», `77.42.9.23`, `ssh -i ~/.ssh/codial_hetzner root@77.42.9.23` |
| Kod | https://github.com/Ilhomjon1502/codialERP1 (`main`) |

**Ish qoidalari (o'zgarmagan):** keyingi bosqich buyurtmachi «boshla» deganda boshlanadi; commit/push faqat u so'raganda; noaniq biznes qoidani so'ra yoki `docs/decisions.md` ga yoz.

### Keyingi sessiya uchun (2026-10-18) — eng so'nggi holat

**Serverda (https://erp.codialinfo.uz, `/srv/codial-test`):**
- **2026-10-18 kechqurun haqiqiy ishga tushirildi** (AppSheet o'rniga). Import (`import_appsheet --on 2026-10-19 --commit`, `apps/importer/extra.py`):
  - 83 faol/rejadagi shartnoma, `opening_balance` = AppSheet `ContractDebt` (28 qarzdor 3 910 727; 55 oldindan to'lagan −22 579 758). Nofaol shartnomalar qarzi ko'chmadi (AppSheet'dagi 3 964 763 dan ~54 ming farq — buyurtmachi qabul qildi);
  - 61 ochiq lid (1–4, 8) + 109 izoh, 19 lid manbasi; okt–noy kurs narxlari va dars soni (Tasdiqlangan); okt KPI stavkalari;
  - g'azna qoldiqlari — `CashMovement` manba `opening` (pul turlari bo'yicha): Emirat 750 000, Bosh g'azna 8 222 507;
  - yangi tizimdagi 14–17.10 davomati (22 qator) o'chirildi (AppSheet qarziga kirgan).
  - Qayta import qilish **kerak emas** (AppSheet to'xtatildi); qilinsa — `opening_balance` va g'azna qoldig'i Excel holatiga qaytadi.
- Bosh menejer akkaunti `ilhomjon.office@gmail.com` (buyurtmachi, botga bog'langan). Botga hozir faqat 3 xodim bog'langan.
- Zaxiralar: `/srv/backups/codial-test/` (har kuni 03:15).
- Monitoring: `deploy/healthcheck.sh`, cron */5; xato bo'lsa Telegram'ga (`ALERT_TELEGRAM_CHAT`).
- Cron:
  - `daily_report` — 19:00 (BM; 2026-10-19 dan qo'ng'iroqlar bo'limi bilan);
  - `morning_plan` — 08:30 (Adm+Hisobchi; tunda javobsiz qo'ng'iroqlar bilan);
  - `notify_attendance` — */10;
  - `propose_lesson_frequencies` — har oy 1-kuni.

**2026-10-19 da qo'shilganlar: Qo'ng'iroqlar** (buyurtmachi so'rovi; `main` da va serverda, telefon ulangan va ishlayapti):
- **Maqsad:** administratorlar ishlatadigan qabul telefonidagi (**998204432**, Redmi Note 8, Android 11, MIUI 12.5.2) barcha qo'ng'iroqlar tugashi bilan ERP «Qo'ng'iroqlar» menyusiga tushadi. Raqam, ism (bazada bo'lsa), vaqt, suhbat davomiyligi va marketing ma'lumoti (lid statusi, manba, kurs, yangi raqam) ko'rsatiladi. **Suhbat yozib olinmaydi** — buyurtmachi «keyingi versiyada» dedi. Telefon — ish telefoni, barcha qo'ng'iroqlar tushadi (buyurtmachi tasdiqlagan).
- **Backend `apps/calls`:**
  - `models.py`:
    - `CallDevice` — nomi, filial, SIM raqami, holat; `token_hash` (SHA-256), `pair_code` + `pair_expires_at`, `last_seen_at`, `app_version`;
    - `CallRecord` — device, branch, `external_id` (`<CallLog._ID>-<date ms>`, (device, external_id) unique), `direction` (Kiruvchi / Chiquvchi / Javobsiz / Rad etilgan / Bloklangan), `number` (asl), `phone` (9 xona), `started_at`, `duration` (s), `contact_name` (telefon kontaktidagi nom), `sim`, `is_first`, `student` / `parent` / `lead` (FK), `comment`, `callback_at`, `callback_by`.
  - `services.py`:
    - `normalize` — 9 xonaga keltiradi;
    - `new_pair_code` / `pair` / `device_by_token` — qurilmani ulash;
    - `match` — shu filialda talabaning 1/2-telefoni, keyin vasiy (→ birinchi farzandi va uning lidi);
    - `rematch` — ro'yxat ochilganda topilmaganlarni qayta solishtiradi, keyin ochilgan lid ham bog'lanadi;
    - `ingest` — idempotent, ko'pi 500 ta;
    - `_mark_callbacks` — chiquvchi yoki gaplashilgan kiruvchi qo'ng'iroq shu raqamdagi oldingi javobsizni avtomatik yopadi;
    - `set_callback`, `stats`.
  - `views.py` va API:
    - telefon uchun (sessiyasiz, CSRF'siz; sarlavha `Authorization: Device <token>`): `POST /api/v1/calls/pair/` (`login` throttle), `POST /calls/ingest/`, `GET /calls/ping/`;
    - sayt uchun: `/calls/` (filtrlar `from`, `to`, `dir` = Kiruvchi | Chiquvchi | missed | missed_open, `known`, `first`, `q`, `device`; PATCH faqat `comment`; `POST {id}/callback/`; `GET stats/`) va `/call-devices/` (yaratilganda kod; `POST {id}/pair-code/` yangi kod beradi va eski tokenni bekor qiladi).
  - Rollar jadvali (Sozlamalar → Rollar va ruxsatlar) bo'limlar ro'yxatini endi serverdan oladi (`bootstrap.sections` → `A.SECTIONS`, `api.js`) — yangi bo'lim `roles.py` `SECTIONS` ga qo'shilsa jadvalda o'zi chiqadi (`core.js` dagi ro'yxat faqat zaxira). Bosh menejer/Admin istalgan rolga `calls` ni bera oladi.
  - Ruxsat bo'limi `calls` (`accounts/0010`): Admin/BM `vaed` (qurilmalar ham), FM, Administrator, Adm+Hisobchi — `ve`, Marketolog — `v`.
  - Testlar: `tests/test_calls.py`.
- **Front-end** `frontend/assets/js/pages-calls.js` (`#/calls`; menyuda «Ota-onalar bilan aloqa» oldida, `?v=m12-27`). Uchta tab:
  - Ro'yxat: javobsiz qatorlar qizil; «✓ Qo'ng'iroq qilindi»; ✎ izoh; noma'lum raqamdan «＋ Lid yaratish» — `A.leadForm(null, free, preset)` ga 3-parametr `preset` qo'shildi; telefon 6 soat jim bo'lsa ogohlantirish.
  - Statistika: kartochkalar (jami, kiruvchi, chiquvchi, javobsiz, umumiy/o'rtacha suhbat, eng uzun va eng qisqa suhbat (kim bilan, qachon — `stats.longest_call`/`shortest_call`; bosilsa shu raqam qo'ng'iroqlari), yangi raqamlar — bosilganda mos filtrlangan ro'yxat); soatlar, kunlar va suhbat davomiyligi (oraliqlar `DURATION_BUCKETS`) diagrammasi; lid manbasi va statusi bo'yicha.
  - Qurilmalar (faqat `calls:a`): qo'shish, 8 belgili kod, yoqish va o'chirish.
- **Android ilova `android/`** (Java, tashqi kutubxonasiz; `uz.codial.calls`, minSdk 26, target/compile 36, AGP 9.0.1, Gradle 9.1):
  - `MainActivity` — ekran: ruxsatlar, batareya, MIUI Avtozapusk, server + kod, «Hozir yuborish»;
  - `CallService` — foreground (`specialUse`) xizmat, `ContentObserver(CallLog)`, 2,5 s debounce, har 10 daqiqada sinxronlaydi;
  - `CallSync` — 1.1 dan CallLog `_ID` bo'yicha faqat yangi qatorlar (+ oxirgi 10 daqiqa sana bo'yicha zaxira; 1.0 da 3 soatlik oyna edi), 200 tadan yuboradi; server 401 qaytarsa ulanishni bekor qiladi;
  - `CallReceiver` — `PHONE_STATE` = IDLE bo'lsa, 3 s kutib yuboradi;
  - `BootReceiver`, `SyncJob` — 15 daqiqalik job;
  - `Prefs`, `Api`.
  - Ulanganda shu kunning 00:00 dan boshlab yuboriladi.
- **APK yig'ish:** `android/build.ps1`. Natija `android/app/build/outputs/apk/debug/app-debug.apk` (~840 KB, debug kalit bilan imzolangan).
  - Claude'ning Bash/PowerShell sandbox'ida Gradle **ishlamaydi**: «Unable to establish loopback connection», daemon'ga ulanib bo'lmaydi. Yig'ishni **foydalanuvchining Terminal panelida** (`run_in_terminal`) yoki Android Studio'da qiling: `powershell -ExecutionPolicy Bypass -File D:\wibecoding\codialERP1\android\build.ps1`. Birinchi build ~2–3 daqiqa.
  - `build.ps1` faqat ASCII bo'lsin: Windows PowerShell 5.1 BOM'siz UTF-8 ni buzadi.
  - `android/local.properties` git'ga kirmaydi. Undagi yo'l `sdk.dir=C\:/Users/Surface PC/AppData/Local/Android/Sdk` ko'rinishida — teskari chiziq bilan yozilsa, Gradle «filename syntax is incorrect» deydi.
  - **Imzo:** APK shu kompyuterdagi debug kaliti (`~/.android/debug.keystore`) bilan imzolangan. Yangilashni shu kompyuterda yig'ing, aks holda eski ilovani o'chirib qayta o'rnatish va qayta ulash kerak. Doimiy release kalit hali yo'q.
  - Yangi versiyada `app/build.gradle.kts` dagi `versionCode` va `versionName` ni oshiring.
- **Ulash tartibi** (buyurtmachi bajardi, 2026-10-19): ERP → Qo'ng'iroqlar → Qurilmalar → «Qurilma qo'shish» → kod. APK telefonga Telegram orqali o'rnatiladi. Ilovada ruxsatlar, batareya va Avtozapusk sozlanadi, kod kiritiladi va «Ulash» bosiladi. Qo'llanma: `docs/user_guide/qongiroqlar.md`. Birinchi kuni 80 qo'ng'iroq tushdi, ularning ~35 foizi bazadagi talaba yoki lidga bog'landi.
- **19:00 hisobot:** `daily_report.calls_section(day)` — jami, yo'nalishlar va suhbat vaqti, javobsizlarga qayta bog'lanish va o'rtacha vaqti, **javobsiz qolganlar ro'yxati** (vaqt, raqam, ism; 10 tagacha), yangi raqamlar, lid manbalari, telefon 6 soatdan ko'p jim bo'lsa ⚠️. Faol qurilma bo'lmasa, bo'lim chiqmaydi. Tekshirish: `daily_report --print`.
- **08:30 ertalabki reja:** `reminders._night_missed` — kecha 18:30 dan bugun 8:30 gacha javobsiz/rad etilgan va **qayta terilmagan** (`callback_at` bo'sh) qo'ng'iroqlar, raqam bo'yicha jamlangan (×N), reja boshida «📵 Tunda javobsiz qo'ng'iroqlar» (15 tagacha). Oyna `NIGHT_FROM`/`NIGHT_TO`.
- **Keyingi g'oyalar** (so'ralmagan, buyurtmachi aytsa):
  - ~~suhbatni yozib olish~~ — bekor qilindi (2026-10-21, `docs/decisions.md`);
  - javobsiz qo'ng'iroq bo'lsa administratorlarga darhol Telegram xabar;
  - AI uchun `analytics_calls` view'i;
  - release kalit bilan imzolash.

**2026-10-18 da qo'shilganlar** (ishga tushirish kuni; hammasi `main` da va serverda):
- **Menyu:** chap menyu ☰ bilan ikonkalarga yig'iladi (`body.side-collapsed`, holati `localStorage`); telefonda yon panel (`A.act.drawer`). «Baholash (ustozni)» menyudan olib tashlandi (`A.NAV`; API va ma'lumot qoldi).
- **Dars jadvali** (`pages-admin.js`): bo'sh joyni bosish → «Yangi guruh» formasi (kun, vaqt, xona/ustoz oldindan to'ldirilgan, `A.act['sched-add']`, `A.groupForm(null, preset)`).
- **Guruh formasi** (`pages-edu.js`): dars vaqti — Sozlamalardagi vaqtlar yoki «＋ Boshqa vaqt» (yangi `LessonTime` yaratiladi); xona/ustoz band bo'lsa sariq ogohlantirish, baribir saqlash mumkin (server to'sib qo'ymaydi).
- **Marketolog roli** (`RoleCode.MARKETOLOG`, migratsiya `accounts/0008`): lidlar to'liq, qolgan bo'limlar ko'rish, topshiriqlar; qo'shimcha ruxsatni BM/FM «Rollar va ruxsatlar»da beradi. Bot (standart): `new_lead`, yangi hodisalar `lead_change` (status o'zgarishi) va `contract_change` (yangi/o'zgargan shartnoma); o'z amali haqida xabar kelmaydi (`notify(exclude=)`). Tahrirlash muddati — 7 kun.
- **Topshiriqlar:** berilganda/o'zgarganda/bajarilganda/bekor qilinganda xabar xodim sozlamasidan qat'i nazar boradi (`notify(force=True)`), takroriy eslatmalar — sozlamaga ko'ra. Eslatma oynasi ichida berilgan topshiriqda darhol takror yo'q; bir martalik eslatma muddat vaqtida (`tasks.services.due_reminders`). Bot navbatni 5 s da yuboradi (long poll `timeout` 5).
- **Davomatlar → Statistika** AppSheet kabi: chapda sanalar (sonlari), o'ngda qatorlar (o'quvchi, sana, status, kurs, ustoz, guruh, dars kunlari, KPI, qarz); filtrlar oy/kurs/guruh/o'quvchi; davomat olinmagan sanalar qizil (`/attendance/dates/`, `/attendance/gaps/`, `?date=&course=&search=`). Eski guruh/ustoz jamlamasi — «Jamlama».
- **Telegram:** `debt_lesson` — dars boshlanishiga 10 daqiqa qolganda Administrator+Hisobchi'ga shu guruhdagi qarzdorlar (`reminders.debt_before_lessons`, bot tick). `run_bot` guruh `chat_id` ni jurnalga yozadi (`GURUH chat_id=…`); Codial ichki guruhi: `-1001530659909` (e'lonlar qo'lda `services.api("sendMessage")` bilan; avtomatik guruh xabarlari hali yo'q — «Ochiq ishlar» 1).
- **Import** (`apps/importer/extra.py`): yuqorida (M11). `CashMovement.Source.OPENING`.
- 2026-10-18 kechqurun barcha botga ulangan xodimlarga va ichki guruhga ishga tushish e'loni yuborildi. Botga ulanmaganlar: Akbarxo'ja, Ilhomjon Developer.

**2026-10-14 … 10-16 da qo'shilganlar** (buyurtmachi so'rovlari, hammasi `main` da va serverda):
- **Dars jadvali** bosh sahifada (xona × vaqt). Blokni bosib guruh vaqtini o'zgartirish mumkin — `pages-admin.js` (`schedHTML`, `sched-edit`), API `/schedule/` (`education/views.py`).
- **Telegram:**
  - 19:00 BM hisoboti (`daily_report.py`);
  - dars boshlanganda ustozga xabar va 08:30 ertalabki reja (`notifications/reminders.py`, bot har 60 s `tick`);
  - **Mini App** — botdan parolsiz davomat va topshiriq (`notifications/webapp.py`, `POST /api/v1/auth/telegram/`, `?tg=attendance|tasks`);
  - Outbox'da `markup` (inline tugmalar), `callback_query` (`td:<id>` — «✅ Bajarildi»).
- **Davomat** (`pages-edu.js`):
  - ustoz faqat bugungi guruhlarini ko'radi, joriy dars avtomatik tanlanadi;
  - ustoz faqat **Keldi/Besabab** qo'yadi (Sababli — menejerlar);
  - menejerlar: sana → kurs → shu kungi guruh.
- **Topshiriqlar** (`apps/tasks`, `pages-tasks.js`): berilganda bajaruvchiga «📌 Yangi topshiriq» (+ Bajarildi tugmasi), beruvchiga «📤 Topshiriq berildi». Bajaruvchi botga ulanmagan bo'lsa — ogohlantirish (botda ham, saytda ham).
- **Dizayn:** navy menyu, Codial logotipi, telefonda ixcham kartochkalar (`style.css`).
- **AI yordamchi:**
  - Gemini'ga sxema va «ma'lumotlar holati» boradi: yozuvlar soni; kurs, guruh, xodim, manba, g'azna nomlari — talaba ma'lumotisiz;
  - bo'sh natija sababi ekranda (`context.diagnose`);
  - nom topilmasa, mavjud qiymatlar bilan 1 marta qayta so'raladi;
  - yangi view `analytics_lessons` (davomat olinmagan darslar);
  - model: `gemini-3.5-flash-lite` → zaxiralar → qayta so'rashda `gemini-3.7-flash` (`providers.py`).

**Ochiq ishlar (navbat bilan):**
0. **Oktyabr oyi ko'chirildi (2026-10-19, bajarildi)** — oyni yangi tizimda yopamiz (oylik, foyda). `importer/october.py` + `extra.py`; Excel snapshot 18.10 20:26 (davomat/to'lov oxirgi sanasi 17.10). Natija:
   - qoldiqlar **01.10.2026 holatida**: shartnoma `opening_balance` (16 qarzdor 2 532 136; 56 oldindan to'lagan −15 296 727), g'azna (`CashMovement` manba `opening`, sana 30.09: Emirat 3 260 000, Bosh 11 603 507), kreditor (`initial_balance` − 01.10 gacha amallar), xodim oyligi (sentyabr `SalaryAssignment.opening_balance` + sentyabr KPI «qo'lda KPI»da);
   - oktyabr qatorlari: 398 davomat, 45 to'lov (27,195 mln, chegirma 525 ming), 14 xarajat (7,209 mln), 7 o'tkazma, 4 ayirboshlash, 2 kreditor amali, 38 oylik berish (25,322 mln: 19 ta sentyabr oyi uchun), 24 sentyabr belgilash; 15–16 ta tugagan shartnoma (oktyabrda dars olgan) + xodimlar, guruhlar, xarajat kategoriyalari, chegirma turi;
   - KPI stavkalari: oktyabrda dars olgan (xodim, rol, kurs) uchun oktyabrgacha amalda bo'lgan oxirgi stavka (6/6);
   - **tekshiruvlar nolga teng**: shartnoma balansi tizim ↔ AppSheet 0/99 farq (>10 so'm), xodim balansi 0/24, to'lov/xarajat/oylik summalari Excel bilan teng. **G'azna farqi ataylab**: Bosh g'azna hozir −4 771 493 = AppSheet 8 222 507 − 20 ta tasdiqlanmagan naqdsiz (karta) to'lov 12 994 000 (yangi qoida: tasdiqlangunga qadar g'aznaga kirmaydi; BM «Tasdiqlashlar»da tasdiqlaydi);
   - **Oktyabr uchun oylik belgilash yo'q** (AppSheet'da ham 0): BM tizimda belgilaydi — KPI oktyabr davomatidan avtomatik (ustoz 6 171 848, yordamchi 150 760); foyda `reports/profit`.
   - **Qayta import xavfsiz** (idempotent; yangi tizimda qo'lda kiritilgan bir xil davomat/to'lov/xarajat/o'tkazma topilsa dublikat yaratmaydi — AppSheet kalitini bog'laydi): AppSheet'ga ikkala tizimda ishlash davrida kiritilganlarni oy oxirida yangi Excel bilan qo'shish mumkin (`--on` sanasi bilan; 01.10 dan keyingi qatorlar yangilanadi). Faqat 17.10 gacha bo'lgan yangi tizimdagi legacy_id'siz davomat qatorlari AppSheet foydasiga o'chiriladi.
   - Keyingi qarorlar (2026-10-19): kreditor boshlang'ich haqqi **0** (faqat oktyabr amallari; MNSH eski −284,9 mln ko'chmadi); ishdan ketgan xodimlar bilan hisob yopilgan — 7 xodimning oylik belgilash/qoldig'i o'chirildi va importer ularni o'tkazmaydi (oktyabrda dars o'tgan/yordam bergan xodim AppSheet'da «Qo'shilmagan» bo'lsa ham ishlayapti deb hisoblanadi: FlutterShogirt, Muhammadmuso, Beckendshogirt — Sozlamalarda «Faol» qilish kerak, aks holda oylik belgilab bo'lmaydi); Xodim balansida ishdan ketganlar yashirin (`bal-left`); Tasdiqlashlar'da «Hammasini tasdiqlash» (`ok-nc-all`, `ok-disc-all`); sentyabr internet xarajati (to'langan 03.10, hisob davri sentyabr) — AppSheet davri saqlangan.
   - **Xodim oyligi qoldig'i (2026-10-19, buyurtmachi qarori):** sentyabr `SalaryAssignment.opening_balance` AppSheet qoidasi bo'yicha — qoldiq **faqat 2026 yil ichidagi** oylardan (2025 dan o'tgan qoldiq, masalan Farg'ona administrator +1 500 000, hisobga olinmadi) — sentyabr yakuni AppSheet bilan teng (10/10 xodim). **Bundan keyin algoritm o'zimizniki: 2026 yil oxiridagi qoldiq 2027 ga o'tadi** (`payroll.services.compute` yillar oralig'ida ham o'tkazadi; 19-bo'lim 6-xato tuzatilgan).
   - Hali ko'chmagan: oktyabrdan oldingi tarix (davomat, to'lov, xarajat), nofaol shartnomalarning oktyabrdan oldingi tarixi, kreditorlarning qolgani, chegirma turlarining qolgani.
1. **Telegram guruhga topshiriqlar** — buyurtmachi 2026-10-16 da so'radi, javob kutilmoqda. **Javobsiz boshlamang.**
   - Taklif: botni guruhga qo'shib BM `/ulash` yozadi, guruh chat_id saqlanadi.
   - Guruhga chiqadi: yangi topshiriq, bajarildi/bekor qilindi, har kuni ertalab ro'yxat (bugun tugaydigan + muddati o'tgan). Takroriy eslatmalar guruhga chiqmaydi (shovqin bo'lmasin).
   - Guruhda `web_app` tugmasi ishlamaydi → oddiy `url` havola.
   - Guruhdagi «✅ Bajarildi»: `callback_query.from.id` bo'yicha (bu xodimning shaxsiy chat_id si); faqat bajaruvchi yoki Admin/BM bosa oladi.
   - Formada «Guruhga ham yuborilsin» belgisi (standart yoqilgan).
   - Buyurtmachidan so'ralgan: 1) guruhga nimalar chiqsin; 2) kunlik ro'yxat soati; 3) belgi kerakmi.
2. Noyabr narxi AppSheet'da yo'q bo'lsa oktyabrniki amal qiladi; noyabr dars soni 1-noyabr cron taklifi + BM tasdig'i.
3. Ixtiyoriy: AI'da prognoz (buyurtmachi tilga olgan, boshlanmagan).

**Ish usullari** (tokenni tejash va xatosiz ishlash uchun):
- **Testlar:** `cd backend && .venv/Scripts/python -m pytest -q` (388 test) va `.venv/Scripts/ruff check .`. Front-end o'zgarsa — `frontend/index.html` dagi `?v=` ni oshiring (hozir `m12-69`). Android ilova o'zgarsa — yuqoridagi «APK yig'ish» bandi.
- **Serverdagi holatni tekshirish** (masalan, qo'ng'iroqlar tushyaptimi): skript ichida `docker compose --env-file .env exec -T web python manage.py shell <<'PY' … PY` (heredoc), ssh esa `dangerouslyDisableSandbox` bilan ishga tushiriladi. Telefon raqamlarini chatga chiqarmang — kerak bo'lsa yashiring.
- **Serverga joylash — bitta SSH ulanishda**, skript bilan (server tez-tez ulanishni cheklaydi):
  1. Skriptni scratchpad'ga yozing va `ssh -i ~/.ssh/codial_hetzner root@77.42.9.23 'bash -s' < skript.sh` bilan ishga tushiring.
  2. Skript ichida: `cd /srv/codial-test && git pull && cd deploy && docker compose --env-file .env up -d --build web bot`.
  3. Keyin tekshiruv: `curl -H "Host: erp.codialinfo.uz" -H "X-Forwarded-Proto: https" http://127.0.0.1:8001/api/v1/health/`.
  4. Skript ichidagi `docker compose exec -T …` ga `< /dev/null` qo'shing, aks holda u skriptning qolgan qatorlarini yutib yuboradi. Django shell uchun heredoc (`<<'PY'`) ishlating.
- **Windows:**
  - katta tahrirlarni Python skript faylida qiling (fayl Write vositasi bilan yozilsin — Git Bash heredoc'i ba'zan buziladi);
  - Windows Python'ga `/c/...` yo'l bermang — `cygpath -w` yoki `D:\...` ishlating;
  - `python -` (stdin) ishlatmang — osilib qoladi.
- **Buyurtmachi bilan:** u o'zbek tilida yozadi; javob qisqa va o'zbekcha bo'lsin. U «push qil», «serverga joyla» deb so'raydi; har yangi funksiyadan keyin odatda GitHub va serverga joylanishini kutadi. Ikkilansangiz — so'rang.
- **Xavfsizlik:**
  - sirlarni (Gemini, Telegram token, parollar) hech qachon chatga yozdirmang va o'zingiz kiritmang — faqat `deploy/set-*.sh`;
  - repo ochiq: `.env`, `*.local.md`, `import_data/` git'ga kirmasin; xlsx'dagi shaxsiy ma'lumotlarni chiqarmang;
  - buzadigan amaldan oldin zaxira oling;
  - jonli AppSheet/Google Sheets'ga ulanmang;
  - AI: talaba ma'lumoti Gemini'ga bormaydi.


### Ishni topshirish (2026-10-13) — keyingi dasturchi shundan davom etadi

**M5 da nima qilindi:**
- `apps/payroll/`: `models.py` (KPIRate, SalaryAssignment + `opening_balance` importi uchun, SalaryPayout); **`services.py`** — `compute()` (8.4: KPI davomatdan, jarima ayiriladi, qoldiq yillar oralig'ida), `latest_per_user`, `save_rate` (+ qayta hisoblash), `save_assignment`, `copy_previous_month`, `save_payout` (g'azna: `CashMovement.Source.SALARY`, `check_funds`), `kpi_entries`, `scope()` (6.3); `views.py` — `/kpi-rates/`, `/salary-assignments/` (+ `balances`, `{id}/breakdown`, `copy`), `/salary-payouts/`, `/kpi/`, `/kpi/rows/`; `demo.py`.
- Front-end: `pages-fin.js` oxiridagi Oyliklar bo'limi (5 tab) API'ga ulangan; `A.CONNECTED` ga `salaries`.
- `tests/test_frontend_syntax.py` — barcha `frontend/assets/js/*.js` node bilan tekshiriladi (node yo'q joyda o'tkazib yuboriladi). **Front-end'ni o'zgartirgach testlarni albatta ishga tushiring.**
- Qarorlar: `docs/decisions.md` (M5). Qo'llanma: `docs/user_guide/m5_oyliklar.md`.

**M6 da nima qilindi:** `apps/education/models.py` — TeacherEvaluation (s1–s5), ParentCall; `services.py` oxirida `save_evaluation`, `save_parent_call`; `export.py` — `contracts_xlsx()` (openpyxl); `views.py` — `/evaluations/`, `/parent-calls/`, `GET /export/contracts/`; `demo_m6.py`. Front-end `pages-edu.js` oxiri (Baholash (ustozni), Ota-onalar bilan aloqa, Shartnoma yuklash), `A.activeContracts()`, `A.downloadXlsx()`. «Talaba vazifalari», «Baholash bo'limi» (GradingSession/StudentGrade) va «50% chegirmalar» — **olib tashlangan**, qaytarmang. Qo'llanma: `docs/user_guide/m6_baholash_aloqa_eksport.md`.

**M7 da nima qilindi:** `apps/reports/` (modelsiz): `services.py` — `profit()` (8.6), `monthly_stats()`, `funnel()`, `first_payers()`; `views.py` — `/reports/profit/`, `/reports/stats/`, `/reports/funnel/`, `/reports/first-payers/`. Front-end: `pages-fin.js` — «Foyda» (API) va yangi `A.page('stats')` (`#/stats`, 3 tab, Chart.js); bosh sahifada faol guruhlar to'lishi. Qo'llanma: `docs/user_guide/m7_hisobotlar.md`.

**M8 da nima qilindi:** `apps/notifications/`: `models.py` (TelegramLink — kod, chat_id, prefs; Outbox — navbat); `services.py` — `notify()` (on_commit, takrorlanmaslik kaliti), hodisalar (`lead_created`, `payment_pending`, `transfer_created`, `makeup_requested`), `api()` (Bot API), `send_pending()`, `handle_message()`; buyruqlar `run_bot` (Docker `bot` xizmati), `notify_attendance` (cron */10), `daily_report` (cron 20:00); `/notifications/me/`. Hodisalar crm/finance/education servislariga ulangan. Front-end: profil → «✈️ Telegram» (`A.telegramPanel`). Token: `deploy/set-telegram.sh`. Qo'llanma: `docs/user_guide/m8_telegram.md`.

**M9 da nima qilindi (AI yordamchi, buyurtmachi tasdiqlagan variant 2026-10-13).** Provayder — **Gemini** (bepul tarif). **Tasdiqlangan variant:** Gemini'ga faqat savol + `analytics_*` view'lar sxemasi (ustunlarning o'zbekcha tavsifi va namunaviy savollar bilan — sifat uchun) boradi; u SQL qaytaradi; server tekshiradi (faqat SELECT, faqat ruxsat etilgan view'lar, LIMIT, 5 s timeout, faqat o'qish huquqli DB foydalanuvchisi) va bajaradi; natija — talaba ismi, telefon va h.k. bilan — **faqat Bosh menejer ekranida** (jadval yoki Chart.js). «Tahlil» qadamida LLM'ga faqat yig'ma raqamlar (ism/telefonsiz). Natija qatorlari LLM'ga yuborilmaydi. Buyurtmachi sharti: analitika sifati yomonlashmasin. API kaliti — `deploy/set-telegram.sh` kabi skript (`set-ai.sh`) bilan serverda, chatga emas. `AI_PROVIDER` almashtiriladigan; kunlik limit; har savol, SQL va natija hajmi log'ga. Bo'lim `ai` — faqat Bosh menejer (matritsada bor), front-end `pages-admin.js` dagi `A.page('ai')` hozir prototip (6 ta tayyor javob) — API'ga ulanadi; bosh sahifa jadvaliga M9 qatori qo'shiladi.
Bajarildi: `apps/ai_assistant/` — `analytics.py` (14 ta view, ustun tavsiflari, `pii` belgisi; `pre_migrate`/`post_migrate` da qayta yaratiladi, PostgreSQL'da `codial_ai` roli), `guard.py` (sqlglot tekshiruvi, LIMIT, timeout, READ ONLY), `providers.py` (gemini/anthropic/openai, urllib), `services.py` (prompt, 1 marta qayta urinish, tahlil — PII bo'lsa faqat yig'ma), `models.AIQuery` (jurnal); API `/ai/`, `/ai/ask/`, `/ai/{id}/run/`, `/ai/{id}/analyze/`. Front-end `pages-admin.js` oxiri. Kalit: `deploy/set-ai.sh`. Qo'llanma: `docs/user_guide/m9_ai_yordamchi.md`. **Yangi jadval/ustun qo'shsangiz va AI uni bilishi kerak bo'lsa — `analytics.py` dagi view va tavsifni yangilang** (`test_views_have_declared_columns...` mosligini tekshiradi).

**M10 doirasi — buyurtmachi qarori 2026-10-14 (16-bo'limdan tor):** faqat faol shartnomalar va ularga kerakli talaba, ota-ona, guruh, kurs, dars kunlari/vaqti, xona, ustoz/yordamchi; boshlang'ich qarz yo'q (0); qolgani qo'lda kiritiladi; yangi tizimda hisob 2026-11-01 dan. Manba: `import_data/Codial1.1.xlsx` (Google Sheets'dan, 51 varaq). Batafsil: `docs/decisions.md`.

**M10 da nima qilindi:** `apps/importer/` — `reader.py` (varaqlar, ID/sana/telefon normallashtirish), `services.py` (`run(path, on, dry_run)` — faol shartnomalar va ularga kerakli ma'lumotlar, `legacy_id` bilan idempotent, bitta yozuv xatosi importni to'xtatmaydi, hisobot), buyruq `import_appsheet --file … [--on YYYY-MM-DD] [--commit]`. Tizimda bor xodim (pochta bo'yicha) faqat bog'lanadi. Qo'llanma: `docs/user_guide/m10_import.md`. **M11 (2026-10-14, buyurtmachi qarori):** alohida sinov/prod muhiti **yo'q** — `/srv/codial-test` (erp.codialinfo.uz, o'sha bot va AI kaliti) haqiqiy tizim. Vositalar: `apps/importer/reset.py` + `prepare_production --keep EMAIL [--commit]` (saqlanadi: rollar/ruxsatlar, davomat statuslari, Emirat, ko'rsatilgan akkaunt; qolgani butunlay o'chadi), `import_appsheet` qayta ishga tushirilsa oraliqda tugagan shartnomalarni yopadi (`_close_ended`), `send_invites [--send]`, `seed_demo` haqiqiy bazada rad etadi, `GET /api/v1/health/` + `deploy/healthcheck.sh` (cron */5, Telegram `ALERT_TELEGRAM_CHAT`). Tartib: `docs/user_guide/m11_ishga_tushirish.md`.

**M10 ning asl rejasi (16-bo'lim, tarix uchun; buyurtmachi doirani toraytirgan — yuqoriga qarang):** 16-bo'lim: `python manage.py import_appsheet --dry-run` → `import_data/*.xlsx` (Emirat), `legacy_id` bilan idempotent, boshlang'ich qoldiqlar (`Contract.opening_balance`, `Account.initial_balance`, `SalaryAssignment.opening_balance`, kreditorlar), tekshiruv hisoboti. Buyurtmachidan AppSheet Excel eksport fayllari kerak. Keyin M11 (sinov ma'lumotlarini tozalash, o'tish kuni, monitoring).

**Oxirgi holat (M4 dan keyin):** M1–M4 `main` da va https://erp.codialinfo.uz da ishlayapti (2026-10-13). Sinov ma'lumotlariga to'lovlar, xarajatlar, o'tkazmalar, kreditor qo'shildi; 84 test yashil.

**M3 dagi holat:** M1, M2 va M3 `main` da, https://erp.codialinfo.uz da ishlayapti (sinov ma'lumotlari: 13 demo xodim + buyurtmachi akkaunti `ilhomjon.office@gmail.com` (Bosh menejer), ~80 lid, 7 guruh, ~58 shartnoma, o'tgan va joriy oy davomati, 8 ta KPI stavkasi). 70 test yashil, ruff toza. Pochta (Gmail SMTP) ishlayapti — parol o'rnatish xatlari haqiqatan yetib boradi. **Parol siyosati: faqat kamida 4 belgi** (buyurtmachi qarori, `docs/decisions.md`).

**M3 rejasi (bajarildi, tarix uchun):**
1. `apps/education/`: `Group`, `Contract`, `Attendance`, `MakeupRequest` (7.4, 9-bo'lim). Pul `DecimalField(14,0)`, bo'lish `ROUND_HALF_UP` (5-bo'lim).
2. Servislar: guruh statusi/to'lishi, shartnoma statusi va raqami, davomat olish (dars kuni, sana qoidalari, o'rindosh), **qarz va KPI (8.2, 8.3) — `Attendance` qatorida saqlanadi**, qayta hisoblash (8.5): `references/services.py` dagi `# M3:` izohli joylar (narx o'zgarishi, dars soni tasdig'i) shu servisni chaqirsin; `recalculate --month` buyrug'i.
3. M2 dan qolganlar (17-bo'lim M3 qatori): `Lead.group` FK + migratsiya, `crm.services.has_contract()`, lid kartochkasidagi «Shartnoma tuzish» (`pages-crm.js` → `A.openLead`), statistikadagi shartnoma konversiyasi.
4. Front-end: `pages-crm.js` (Shartnomalar, Qarzdorlar), `pages-edu.js` (Guruhlar, Davomat, Kelmaganlar, Qoldirilgan darslar) — 21.4 tartibida API'ga ulash, `A.CONNECTED` ga `contracts`, `debtors`, `attendance`, `groups`, `groupAnalysis` qo'shish. Namuna: M2 dagi `A.page('leads')` (`load()` + server hisobi).
5. Testlar (8-bo'lim formulalari, muddatlar, rollar, doira, so'rovlar soni), `seed_demo` ga guruh/shartnoma/davomat, `docs/user_guide/m3_*.md`, shu bo'lim va 17-bo'lim holati.
6. Joylash: 21.5 (`git pull` + `docker compose up -d --build` + `seed_demo`).

**M3 da nima qilindi (keyingi dasturchi bilsin):**
- `apps/education/`: `models.py` (Group, Contract, Attendance, MakeupRequest); **`calc.py`** — qarz va KPI (8.1–8.3), `Calculator` narx/dars soni/stavkani keshlaydi, `recalculate(qs)` — qayta hisoblash (8.5); `services.py` — status (sanadan), doira (`teacher_scope`), guruh/shartnoma qoidalari, davomat olish (`check_take`, `mark`), bog'lanish holati, qoldirilgan darslar; `views.py` — `/groups/` (+ `journal`), `/contracts/` (+ `counts`), `/debtors/`, `/attendance/` (`take`, `stats`, `summary`), `/makeups/` (`approve`, `reject`); `demo.py` — sinov ma'lumotlari; `recalculate --month|--all` buyrug'i.
- `apps/payroll/models.py`: faqat `KPIRate` (KPI hisobi uchun). API va ekran — M5.
- Qayta hisoblash ulangan joylar: kurs narxi (`references.services.set_course_price`), dars soni tasdig'i/o'zgarishi/o'chirilishi (`approve_frequency`, `LessonFrequencyViewSet`), shartnoma turi (`save_contract`), davomat statusi (`mark`, `approve_makeup`). **M5 da KPI stavkasi o'zgarganda `calc.recalc_from(month, branch=…, course=…)` chaqirilsin.**
- Shartnoma balansi: `services.with_balance()` — hozir `paid` va `discount_sum` = 0. **M4 da shu yerga to'lovlar subquery'si qo'shiladi** (qarzdorlar, shartnoma sahifasi, bosh sahifa o'zi yangilanadi).
- Lid: `Lead.group`, `has_contract` (Exists annotatsiya), `POST /leads/{id}/contract/`, voronka va statistikada shartnoma konversiyasi.
- Front-end: `A.CONNECTED` ga contracts, debtors, attendance, groups, groupAnalysis qo'shildi; guruhlar bootstrap'da (`A.reloadGroups()`); umumiy `A.pager(key, data)` va `A.keepContract()`. Bosh sahifa (`pages-admin.js`) — faol talabalar, qarzdorlik, bugun davomati olinmagan guruhlar, ustoz uchun KPI.
- Qarorlar: `docs/decisions.md` (2026-10-13, M3). Qo'llanma: `docs/user_guide/m3_guruhlar_shartnomalar_davomat.md`.

**M4 da nima qilindi (keyingi dasturchi bilsin):**
- `apps/finance/`: `models.py` (Account, **CashMovement**, Payment, Transfer, Exchange, Expense, Creditor, CreditorTransaction, CreditorComment); **`services.py`** — `sync_movements` (manba → jurnal qatorlari), `balances()`/`balance()`, `check_funds` (qoldiqdan oshmasin), `my_accounts`, `scoped_account_ids`, to'lov/o'tkazma/xarajat/ayirboshlash/kreditor qoidalari, tasdiqlar (`can_approve_discount`, `can_approve_noncash`, `can_confirm_transfer`), `pending_counts`; `receipt.py` — PDF chek (reportlab); `views.py` — `/payments/` (+ `approve_discount`, `approve_noncash`, `receipt`, `summary`), `/transfers/` (+ `confirm`), `/exchanges/`, `/expenses/` (+ `names`, `summary`), `/creditors/` (+ `comments`), `/creditor-transactions/`, `/approvals/`; `demo.py` — sinov ma'lumotlari.
- G'azna balansi: `AccountSerializer` da `balance`, `by_type`, `pending` (bootstrap va `/accounts/`), jurnal — `/accounts/{id}/ledger/`.
- Shartnoma balansi endi to'lovlar bilan (`education.services.with_balance`), shartnoma sahifasida «To'lovlar» tabi, Lidlar → «To'lov qilganlar» (`?paid=1`).
- **M5 uchun:** `SalaryPayout` saqlanganda `sync_movements(CashMovement.Source.SALARY, payout, [(account, cash_type, -amount, True, user)])` va `check_funds`; KPI stavkasi o'zgarsa `education.calc.recalc_from`.
- Front-end: `pages-fin.js` boshidagi bo'limlar API'ga ulangan (Foyda va Oyliklar — hali prototip kodi, M5/M7); `A.reloadMoney()` (g'aznalar + tasdiqlar soni), `A.reloadPending()`, `A.accBal()`.
- Ochiq: pulni qaytarish (18-bo'lim 9-savol) — hali yo'q.

**M4 rejasi (bajarildi):** Buyurtmachi «M4 ni boshla» desa: `CashMovement` ledger, g'azna balansi, to'lovlar (chegirma limiti, tasdiqlar, PDF chek), o'tkazmalar, ayirboshlash, xarajatlar, kreditorlar (7.5); `with_balance()` ga to'lovlar; front-end `pages-fin.js` 21.4 tartibida; shartnoma sahifasi va qarzdorlardagi «To'lov» tugmasi `paymentsReady()` orqali o'zi chiqadi (`A.CONNECTED` da `payments` bo'lsa).

**Buyurtmachi qarori (M3):** eski shartnomani to'xtatish (tugash sanasi, sabab, izoh) muddatdan qat'i nazar mumkin, tugash sanasi oxirgi 30 kun ichida (`education.services.check_contract_edit`). Boshqa maydonlar — 6.4 muddati, boshlanish sanasi bo'yicha.

**Ochiq:** 18-bo'lim savollari (3-savol yopildi — 50% chegirma olib tashlandi); lokal `C:\DSKEYS` (E-IMZO kaliti nusxasi) — buyurtmachi so'rasa o'chiriladi.

### Yangi kelgan dasturchi uchun qadamlar

1. Shu bo'limni, **21-bo'limni** (haqiqiy tizim qanday tuzilgan va yangi bo'lim qanday qo'shiladi) va `docs/decisions.md` ni o'qing.
2. Biznes qoidalar: 6-bo'lim (rollar), 7-bo'lim (modellar), 8-bo'lim (hisob-kitob). Ekranlar va matnlar — prototipda (20-bo'lim).
3. Lokalda ishga tushiring (`README.md`): `backend` da `seed_demo` → `runserver` → http://localhost:8000.
4. Testlar: `backend` da `.venv/Scripts/python -m pytest` va `.venv/Scripts/ruff check .` yashil bo'lsin.
5. Keyingi bosqich (M11) rejasi: shu bo'limdagi «M10 da nima qilindi» → «M11 rejasi» va 17-bo'lim.

## 1. Manbalar

| Fayl | Nima |
|---|---|
| `codial_appdoc.json` | AppSheet "Codial 1.0" ilovasining to'liq texnik tavsifi (48 jadval, 651 ustun, 170 view, 202 action, 16 format qoidasi, 10 slice). **Asosiy mashina o'qiydigan manba.** |
| `AppSheetsDoc.pdf` | Xuddi shu "Application Documentation" ning brauzerdan saqlangan PDF nusxasi (851 sahifa). Faqat odam o'qishi uchun; JSON bilan bir xil. **GitHub'ga yuklanmagan** (18 MB, `.gitignore` da) — kerak bo'lsa buyurtmachidan so'rang. |
| `prototype/` | Bosiladigan HTML prototip (20-bo'lim). |

JSON tuzilmasi: `[{t: "H2"|"H3"|"H4"|"table", text|rows}]` ro'yxati. Jadval bloklari kalit-qiymat juftlari: `Table name`, `Schema Name`, `Column name` (+ `Type`, `Type Qualifier` ichida `Valid_If`, `Show_If`, `Editable_If`, `Required_If`, `Reset_If`, `EnumValues`, `ReferencedTableName`), `App formula`, `Initial value`, `View name`, `Action name`, `Rule name`, `Slice Name`.

- Fayl 1,1 MB. Uni to'liq o'qima. Kerakli jadval yoki ustunni nomi bo'yicha qidir (Grep yoki kichik Python skript bilan).
- Biznes qoidaning asl formulasini doim shu fayldan tekshir. Bu hujjat bilan farq bo'lsa, **shu hujjat ustun**: unda AppSheet xatolari ataylab tuzatilgan (19-bo'lim).
- Kod boshlanganda manba fayllar `docs/appsheet/` ga ko'chiriladi.

## 2. Kontekst va maqsad

- **Kompaniya:** Codial — Farg'onadagi IT o'quv markazi. Kurslar: Frontend, Backend, Flutter, Kiber xavfsizlik, Kompyuter savodxonligi va boshqalar.
- **Hozirgi holat:** "Codial 1.0" AppSheet ilovasi, ma'lumotlar Google Sheets'da.
- **Muammo:** ilova sekin ochiladi (sinxronlash 25–30 s), chunki AppSheet barcha jadvallarni klientga yuklaydi va virtual ustunlarni (`SELECT(...)` lar) har safar butun jadvallar bo'ylab qayta hisoblaydi.
- **Maqsad:** barcha funksiyalarni saqlagan holda tez, ishonchli va kengaytiriladigan Django veb-ilova qurish. Topilgan xatolar tuzatiladi va yangi imkoniyatlar qo'shiladi.
- **Faqat Codial uchun.** iTeach boshqa markaz va boshqa tizim, uni hech qanday shaklda aralashtirma.
- **Filiallar:** hozir bitta faol filial bor: **"Emirat"** (Farg'ona). Model filiallarga bo'lingan bo'lsin. Faol filial bitta bo'lsa, u hamma joyda avtomatik tanlanadi va filial maydoni ko'rinmaydi. "Xonaqoh" va "Andijon" yopilgan, ko'chirilmaydi.
- **Foydalanuvchilar** faqat xodimlar (telefon va kompyuterdan). Talabalar va ota-onalar tizimga kirmaydi.

## 3. Ish tartibi

1. Kod yozishdan oldin quyidagilarni taqdim et va tasdiqlashni kut: loyiha tuzilmasi, ER-diagramma (Mermaid), bosqichlar rejasi, 18-bo'limdagi ochiq savollar.
2. Ish **bosqichma-bosqich** (17-bo'lim) olib boriladi. Har bosqich oxirida: testlar yashil, `README` yangilangan, qisqa hisobot (nima qilindi, qanday tekshirish mumkin).
3. Jonli AppSheet ilovasiga yoki Google Sheets'ga **hech qachon ulanma va yozma.** Eski ma'lumotlar faqat Excel eksport fayllaridan import qilinadi (16-bo'lim).
4. Biznes qoidasi noaniq bo'lsa, taxmin qilma, so'ra. Taxmin majburiy bo'lsa, `docs/decisions.md` ga yoz (sana, qaror, sabab).
5. Interfeys matnlari o'zbek tilida (lotin), Django i18n (`gettext`) orqali.
6. Commit faqat buyurtmachi so'raganda qilinadi.

## 4. Texnologiyalar

| Qism | Tanlov |
|---|---|
| Til / framework | Python 3.12, Django 5.x |
| Ma'lumotlar bazasi | PostgreSQL 16 (serverda, Docker). Lokalda SQLite (`config/settings/dev.py`). Kod faqat Django ORM orqali; PostgreSQL'ga xos funksiyalar faqat zarur bo'lsa va zaxira yechim bilan |
| Backend API | **Django REST Framework**, `/api/v1/`, sessiya + CSRF (bir domen, CORS yo'q). Tasdiqlangan 2026-10-12, `docs/architecture.md` |
| Frontend | **Ma'qullangan prototip** (`prototype/` → `frontend/`) API'ga ulanadi: oddiy HTML/CSS/JS, framework va build yo'q. Hisob-kitob front-end'da emas, serverda |
| Diagrammalar | Chart.js |
| Dizayn | Responsive (telefon + kompyuter), PWA. Brend ranglari: qora, oq, to'q sariq (Codial logotipi) |
| PDF / Excel | WeasyPrint yoki xhtml2pdf (chek), openpyxl (Excel) |
| Fon vazifalari | Management buyruqlari + cron. Celery shart emas |
| Telegram | aiogram yoki python-telegram-bot |
| Testlar | pytest + pytest-django, factory_boy |
| Kod sifati | ruff, black, pre-commit |
| Deploy | Hetzner VPS, Docker Compose: `test.` subdomen (M1 dan) va asosiy domen (M11 dan) bitta serverda |
| Sozlamalar | `LANGUAGE_CODE="uz"`, `TIME_ZONE="Asia/Tashkent"`, pul butun so'mda: `DecimalField(max_digits=14, decimal_places=0)` |

## 5. Loyiha tuzilmasi va konventsiyalar

Haqiqiy tuzilma (M1 da tasdiqlangan; ✅ — bor, ⏳ — o'z bosqichida qo'shiladi):

```
backend/
  config/settings/       base, dev (SQLite), prod (PostgreSQL, HTTPS), test (pytest)
  config/api.py          /api/v1/ marshrutlari (router)
  apps/
    core/          ✅    BaseModel, AuditLog, roles.py (rollar, bo'limlar, matritsa, muddatlar), permissions.py,
                         scoping.py, services.py (soft delete), viewsets.py (AuditedModelViewSet), seed_demo
    accounts/      ✅    User (pochta bilan kirish), Role, RolePermission, RolePower; login, parol havolasi
    references/    ✅    Branch, Course, Room, DayPattern, LessonTime, CoursePrice, LessonFrequency,
                         DiscountType, ExpenseCategory, LeadSource, AttendanceStatus; bootstrap
    finance/       ✅ M4  Account, CashMovement (ledger), Payment, Transfer, Exchange, Expense, Creditor…; receipt.py (PDF), demo.py
    crm/           ✅ M2  Parent, Student, Lead, LeadComment; voronka va statistika (services.board/stats)
    education/     ✅ M3  Group, Contract, Attendance, MakeupRequest; calc.py (qarz, KPI, qayta hisoblash), demo.py
                         + M6: TeacherEvaluation, ParentCall; export.py (.xlsx)
    payroll/       ✅ M5  KPIRate, SalaryAssignment, SalaryPayout; compute() (oylik hisobi), demo.py
    reports/       ✅ M7  foyda, oylik statistika, voronka, birinchi to'lovchilar (modelsiz)
    tasks/         ✅    StaffTask — topshiriqlar va bot eslatmalari (2026-10-16)
    calls/         ✅    CallDevice, CallRecord — qabul telefonidagi qo'ng'iroqlar (2026-10-19)
    clientbot/     ✅    mijozlar (o'quvchi/vasiy) Telegram boti: BotInvite, BotLink, LeadSurvey, Referral (2026-10-24)
    voice/         ✅    VoiceCommand — Bosh menejerning botdagi ovozli/yozma buyruqlari va savollari (2026-10-25)
    importer/      ✅ M10 reader.py, services.py (faol shartnomalar importi), import_appsheet buyrug'i
    notifications/ ✅ M8  Telegram: TelegramLink, Outbox; run_bot, notify_attendance, daily_report
    ai_assistant/  ✅ M9  AIQuery (jurnal); analytics.py (view'lar), guard.py (SQL xavfsizligi), providers.py, services.py
  tests/                 pytest (conftest: make_user, api)
frontend/          ✅    prototip ekranlari, API'ga ulangan (21.3)
android/           ✅    «Codial qo'ng'iroqlar» Android ilovasi (Java), build.ps1 — 0-bo'lim, 2026-10-19
deploy/            ✅    docker-compose.yml, .env.example, nginx/, backup.sh, restore.sh
docs/              ✅    architecture.md, decisions.md, deploy_hetzner.md, user_guide/
prototype/         🔒    GitHub Pages'dagi prototip — o'zgartirilmaydi
import_data/             AppSheet .xlsx eksportlari (git'ga kirmaydi)
```

Qoidalar:
- Biznes mantiq **faqat servis qatlamida**, view, shablon yoki `save()` ichida emas. Har bir servis uchun unit-test bo'ladi.
- Har bir model `BaseModel` dan meros oladi: `created_at`, `created_by`, `updated_at`, `updated_by`, `is_deleted` (soft delete), `legacy_id` (AppSheet kaliti, indeksli, nullable).
- Pul hisobida faqat `Decimal`, `float` taqiqlangan. Bo'lish natijalari so'mgacha yaxlitlanadi (`ROUND_HALF_UP`); qoida `docs/decisions.md` da.
- Barcha moliyaviy amallar `transaction.atomic` ichida.
- Enum'lar `TextChoices`. Qiymatlar AppSheet'dagi o'zbekcha matnlar bilan mos keladi, chunki import shunga tayanadi.
- Formadagi bosqichma-bosqich ko'rinish (AppSheet `Show_If`) va bog'liq ro'yxatlar (filial → kurs → guruh → talaba) serverda ham tekshiriladi, faqat JS'ga ishonilmaydi.

## 6. Rollar va ruxsatlar

### 6.1 Rollar (seed)

| Kod | Nomi |
|---|---|
| `ADMIN` | Admin (tizim egasi) |
| `BOSH_MENEJER` | Bosh menejer |
| `FILIAL_MENEJERI` | Filial menejeri |
| `ADMINISTRATOR` | Administrator (qabul bo'limi) |
| `ADMINISTRATOR_HISOBCHI` | Administrator+Hisobchi |
| `HISOBCHI` | Hisobchi |
| `USTOZ` | Ustoz |
| `YORDAMCHI` | Yordamchi ustoz |
| `USTOZ_YORDAMCHI` | Ustoz+Yordamchi |
| `BOSHQA` | Boshqa (tizimga kirmaydi, faqat ro'yxatda) |
| `ASOSCHI` | Asoschi (2026-10-25; saytda hamma bo'lim va filialni faqat KO'RADI — `permissions.sees_all`; botga faqat qisqa kunlik hisobot keladi — `founder_report`) |

- `Role` modeli: har bir rol uchun bo'limlar bo'yicha ruxsatlar (ko'rish / qo'shish / tahrirlash / o'chirish / tasdiqlash) va tahrirlash muddati.
- Bosh menejer va Admin Sozlamalarda rollarni boshqaradi va yangi rol qo'shadi.
- `RolePower`: qaysi rol qaysi rollarni tayinlay oladi (AppSheet: `Roles.RolePower`).
- "Asoschi / Investor" va "Aloqa operatori" rollari ko'chirilmaydi.

### 6.2 Boshlang'ich ruxsatlar matritsasi (AppSheet "update mode" dan)

`A` = hammasi, `QT` = qo'shish+tahrirlash, `T` = faqat tahrirlash, `K` = faqat ko'rish, `—` = bo'lim ko'rinmaydi yoki doiradan tashqari. Bu **seed uchun boshlang'ich holat**. Muddatlar 6.4 bo'yicha qo'llanadi.

| Bo'lim | Admin | BM | FM | Adm | Adm+H | Hisobchi | Ustoz | Yordamchi | U+Y |
|---|---|---|---|---|---|---|---|---|---|
| Foydalanuvchilar | A | A | A | K | QT | K | K | K | K |
| Talabalar, Ota-onalar, Lidlar, Shartnomalar | A | A | A | A | A | K | K | K | K |
| Kurslar | A | A | A | QT | A | K | K | K | K |
| Guruhlar | A | A | A | QT | QT | K | K | K | K |
| Filiallar, Pul turlari, Xarajat kategoriyalari | A | A | K | K | K | K | K | K | K |
| Xonalar, Kurs narxlari | A | A | A | A | A | K | K | K | K |
| Dars kunlari, Dars vaqtlari, Lid manbalari | A | A | A | QT | QT | K | K | K | K |
| Oydagi dars soni | A | A | A | QT | A | K | K | K | K |
| KPI stavkalari, Oylik belgilash, Chegirma turlari | A | A | A | K | K | K | K | K | K |
| G'aznalar | A | A | K | K | T | T | K | K | K |
| To'lovlar, Xarajatlar, Oylik berish, Ichki o'tkazmalar | A | A | K | K | A | A | K | K | K |
| Davomat | A | A | A | A | A | K | A | A | A |
| Davomat statuslari, Rollar | A | T | K | K | K | K | K | K | K |
| Talaba vazifalari | A | A | K | K | K | K | A | K | A |
| Kreditorlar, Kreditor amallari, Pul ayirboshlash | A | A | — | — | — | — | — | — | — |
| Baholash (talaba → ustoz) | A | A | A | A | A | K | K | K | K |
| Qo'ng'iroqlar (2026-10-19; Marketolog — K) | A | A | T | T | T | — | — | — | — |
| Baholash bo'limi (ustoz → talaba) | A | A | A | A | A | K | A | A | A |

Diqqat: AppSheet'da `Exchange`, `CommentToCreditors`, `Parent_Comment`, `Discount50`, `Exel` jadvallarida cheklov ifodasi yo'q edi (hamma hammasini qila olardi). Yangi tizimda ular uchun ruxsat aniq belgilanadi. Taklif: Parent_Comment administratorlar va menejerlarga (Discount50 — bo'lim olib tashlangan); Exchange va Creditor bo'limlari faqat Admin va Bosh menejerga.

### 6.3 Ma'lumotlarga kirish doirasi (scoping)

- **Admin, Bosh menejer:** barcha filiallar.
- **Qolgan rollar:** faqat `user.branches` ichidagi filiallar.
- **Ustoz:** faqat o'zi ustoz bo'lgan guruhlar, ularning shartnomalari, davomati va vazifalari.
- **Yordamchi:** faqat o'zi yordamchi bo'lgan guruhlar.
- **Ustoz+Yordamchi:** ikkalasi.
- Har kim o'zi yaratgan yozuvlarni ko'radi (`created_by`).
- KPI stavkasi, oylik belgilash va oylik berish: Filial menejeri o'z filialini, boshqa xodim faqat o'zinikini ko'radi.
- Ichki o'tkazmalar: foydalanuvchi filialidagi g'azna jo'natuvchi yoki qabul qiluvchi bo'lgan yozuvlar.
- Doira so'rov boshida bir marta aniqlanadi va umumiy `QuerySet` menejeri yoki mixin orqali qo'llanadi. Har sahifada qayta hisoblanmaydi.

### 6.4 Tahrirlash va o'chirish muddatlari (tasdiqlangan)

| Rol | O'tgan sanadagi yozuvni tahrirlash / o'chirish |
|---|---|
| Admin | cheklovsiz |
| Bosh menejer | cheklovsiz (o'tgan sanalarni ham) |
| Filial menejeri | oxirgi 15 kun |
| Administrator, Administrator+Hisobchi | shartnoma, lid, davomat: 7 kun; to'lov: faqat bugun |
| Hisobchi | xarajat, to'lov, oylik berish: faqat bugun |
| Ustoz, Yordamchi | davomat: faqat bugun; boshqa yozuvlarni tahrirlay olmaydi |

- Tasdiqlangan to'lov, chegirma va o'tkazmani faqat Admin va Bosh menejer o'zgartiradi.
- Muddat yozuvning `date` maydoni (bo'lmasa `created_at`) bo'yicha: `today - date <= N kun`.
- AppSheet'dagi `TODAY()+30 >= [CreatedTime]` kabi formulalar xato (doim rost). Ularni ko'chirma, yuqoridagi jadvalni qo'lla.
- **Audit log:** har bir yaratish, o'zgartirish va o'chirishda kim, qachon, model, yozuv, eski va yangi qiymatlar yoziladi (`django-simple-history` yoki o'z yechim). Bosh menejer audit tarixini ko'radi.
- O'chirish **soft delete** (moliyaviy yozuvlar jismonan o'chirilmaydi).
- Ishlatilgan ma'lumotnoma yozuvini (masalan davomatda ishlatilgan statusni) o'chirib bo'lmaydi, faqat nofaol qilinadi.

## 7. Ma'lumotlar modeli

### 7.1 AppSheet → Django moslik jadvali

| AppSheet | Django | Izoh |
|---|---|---|
| Users | `User` (AbstractUser) | |
| Roles | `Role`, `RolePower` | |
| Branches | `Branch` | |
| Courses | `Course` | |
| Rooms | `Room` | |
| LessonDays + Days | `DayPattern` | Days alohida jadval bo'lmaydi |
| LessonTimes | `LessonTime` | |
| CoursePrices | `CoursePrice` | yangi mantiq: `effective_from` |
| LessonFrequency | `LessonFrequency` | yangi: Taklif/Tasdiqlangan |
| TeacherKPI | `KPIRate` | yangi mantiq: `effective_from` |
| DiscountTypes | `DiscountType` | |
| Categories | `ExpenseCategory` | |
| LeadSources | `LeadSource` | |
| CashType | `CashType` (TextChoices) | |
| AttendanceStatus | `AttendanceStatus` | enum + rollar ruxsati |
| Months | — | Python/Django oy nomlari |
| Parents | `Parent` | |
| Students | `Student` | |
| Leads | `Lead` | |
| LeadComments | `LeadComment` | |
| Groups | `Group` | |
| Contracts | `Contract` | |
| Attendance | `Attendance` | |
| TakeAttendance | — | jadval emas, ekran holati |
| — | `MakeupRequest` | yangi |
| StudentTasks | — | **ko'chirilmaydi**: bo'lim olib tashlangan (2026-10-13) |
| Baholash | `TeacherEvaluation` | talaba ustozni baholaydi |
| Baholash_tizimi + B_Students | — | **ko'chirilmaydi**: bo'lim olib tashlangan (2026-10-13) |
| Parent_Comment | `ParentCall` | |
| Discount50 | — | **ko'chirilmaydi**: bo'lim olib tashlangan (2026-10-13) |
| Accounts | `Account` | |
| — | `CashMovement` | yangi ledger |
| Payments | `Payment` | |
| Transactions | `Transfer` | |
| Exchange | `Exchange` | |
| Expenses | `Expense` | |
| Creditors | `Creditor` | |
| CashFlow | `CreditorTransaction` | |
| CommentToCreditors | `CreditorComment` | |
| SalaryAppoinment | `SalaryAssignment` | |
| SalaryGiving | `SalaryPayout` | |
| Balance | — | foyda hisoboti sahifasi |
| Exel + "Process for Exel" + "Yuklash Output" | `ExcelExport` servisi | |
| "Process for Chek" + "Faylni yuklash Output" | chek PDF servisi | |
| _Per User Settings | — | kerak emas |

### 7.2 Sozlamalar (ma'lumotnomalar)

- **Branch:** `name` (unique), `status` (Faol/Nofaol), `default_cashbox` (FK Account), `noncash_cashbox` (FK Account, naqdsiz to'lovlar g'aznasi; AppSheet'dagi qattiq yozilgan `cb4963b4` o'rniga).
- **User:**
  - `full_name` (unique, xato: "Avval kiritilgan ism! Boshqa nom bering"), `phone`, `email` (unique, login uchun; xato: "Avval kiritilgan pochta!");
  - `role` (FK Role; tanlov ro'yxati `RolePower` bo'yicha), `branches` (M2M; Admin va Bosh menejerda bo'sh = hammasi);
  - `teams` (ko'p tanlov: Qabul, Marketing, Moliya, HR, Ta'lim, Boshqa, Qurilish va ta'mirlash, IT, Ta'minot);
  - `employment_status` (Faol / Ishdan ketgan). Ishdan ketgan xodim kira olmaydi, tarixi saqlanadi;
  - `BOSHQA` rolida email va login bo'lmaydi;
  - **parol talabi (2026-10-13, buyurtmachi qarori):** faqat kamida 4 belgi, oson parol ham mumkin; login urinishlari limiti (10/daqiqa) saqlanadi;
  - **parol (tasdiqlangan, 2026-10-12):** admin xodimga parol bermaydi. Xodim qo'shilganda uning pochtasiga bir martalik "parol o'rnatish" havolasi yuboriladi (Django `PasswordResetTokenGenerator`, muddatli). Xodim parolini o'zi qo'yadi. Admin "Havolani qayta yuborish" tugmasi bilan yangisini jo'nata oladi. Buning uchun SMTP pochta sozlanadi (`.env`).
- **Course:** `name` (unique), `branches` (M2M), `status` (Faol/Nofaol, standart Faol).
- **Room:** `branch`, `name`, `capacity`, `status` (standart Faol).
- **DayPattern** (LessonDays): `name` (masalan "Dush,Chor,Jum"), `weekdays` (ISO raqamlar ro'yxati, unique), `status` (Faol/Nofaol, standart Faol). Nofaol jadval yangi guruh va lid formalarida chiqmaydi va oydagi dars soni taklifiga kirmaydi. Guruh, lid, dars soni yoki davomatda ishlatilmagan bo'lsa o'chirish mumkin, aks holda faqat nofaol qilinadi.
  - AppSheet `Days.DayNumber` va `WEEKDAY()-1` ishlatgan: yakshanba=0, dushanba=1 … shanba=6. ISO'da dushanba=1 … yakshanba=7, ya'ni faqat **yakshanba** farq qiladi (0 → 7). Importda shunday o'girilsin.
- **LessonTime:** `branch`, `start_time`, `end_time` (standart start + 2 soat), (branch, start, end) unique (xato: "Avval qo'shilgan vaqt!"), `status` (Faol/Nofaol, standart Faol). Ko'rinishi "08:00 - 10:00". Nofaol vaqt yangi guruh va lid formalarida chiqmaydi. Guruh yoki lidda ishlatilmagan bo'lsa o'chirish mumkin, aks holda faqat nofaol qilinadi.
- **CoursePrice** (yangi mantiq):
  - maydonlar: `branch`, `course`, `effective_from` (oyning 1-kuni), `price` (≥ 0);
  - oy uchun narx = shu oyda amalda bo'lgan oxirgi yozuv;
  - narx faqat o'zgarganda yangi yozuv qo'shiladi, tarix saqlanadi.
- **LessonFrequency** (oydagi darslar soni):
  - maydonlar: `branch`, `day_pattern`, `courses` (M2M), `year`, `month`, `frequency` (4–26; xato: "Oyda eng ozi 4 marta, ko'p 26 marta bo'lishi mumkin, xolos"), `status` (Taklif / Tasdiqlangan), `approved_by`;
  - (branch, day_pattern, course, year, month) takrorlanmasin;
  - **yangi jarayon:** har oy 1-kuni cron har bir faol dars kunlari jadvali uchun shu oydagi dars kunlarini kalendardan hisoblab, "Taklif" holatida yozuv tayyorlaydi (o'tgan oydagi kurs tanlovini nusxalaydi). Menejer kurslarni belgilaydi, sonni tekshiradi, kerak bo'lsa tuzatadi (bayramlar) va tasdiqlaydi;
  - tasdiqlanmagan oy uchun qarz va KPI hisoblanmaydi, dashboard'da ogohlantirish chiqadi. Tasdiqlangach, shu oyning davomat qatorlari qayta hisoblanadi.
- **KPIRate** (TeacherKPI, yangi mantiq):
  - maydonlar: `branch`, `user`, `role_type` (USTOZ / YORDAMCHI), `course`, `effective_from`, `type` (O'zgarmas / Foiz), `fixed_amount` (≥ 0), `percent` (0–100);
  - oy uchun stavka = shu oyda amalda bo'lgan oxirgi yozuv;
  - "O'tgan oy stavkalarini nusxalash" tugmasi bor;
  - yordamchiga menejer alohida (odatda arzonroq) stavka belgilaydi.
- **DiscountType:** `name` (unique, xato: "Avval qo'shilgan nom!"), `max_amount` (≥ 0), `courses` (M2M, ixtiyoriy), `is_system` (masalan "Boshlang'ich balansga", oddiy tanlovda ko'rinmaydi). (`is_discount50` belgisi 50% chegirmalar bo'limi bilan birga olib tashlangan.) Hozirgi turlar: 50% Chegirma (500 000), Rag'batlantiruvchi (350 000), Boshlang'ich balansga (500 000), Ikki va undan ortiq farzand (100 000), Avvaldan to'lov (75 000).
- **ExpenseCategory:** `name`, `kind` (Xarajat / Qayta investitsiya / Dividend / Tashqi qarz), `allowed_roles` (M2M). AppSheet'da `kind` faqat 3 qiymatli edi, "Tashqi qarz" yangi.
- **LeadSource:** `name`, `status` (Faol/Nofaol, standart Faol). Nofaol manba yangi lid formasida chiqmaydi, eski lidlar, filtrlar va statistikada qoladi.
- **CashType:** `CASH` (Naqd), `BANK` (Bank), `CARD` (Karta). `ALL` faqat g'azna turi sifatida ishlatiladi, to'lov yoki xarajatda tanlanmaydi.
- **AttendanceStatus:** `KELDI="1"`, `SABABLI="0"`, `BESABAB="X"`, `NOFAOL="-"`. Har bir status uchun uni qo'ya oladigan rollar sozlanadi.

### 7.3 CRM

- **Parent:** `branch`, `first_name` (≥ 3), `last_name`, `phone` (9 raqam, +998 siz; xato: "9 sondan iborat bo'lsin. Namuna: 998883322").
- **Student:**
  - maydonlar: `branch`, `first_name`, `last_name` (3–20 belgi; xato: "Eng ozi 3 harf, ko'pi 20"), `father_name` (≥ 3, nuqta taqiqlangan: "Nuqta qo'yib bo'lmaydi!"), `gender` (Erkak / Ayol), `phone1` (9 raqam), `phone2` (9 raqam, ≠ phone1: "Ikki bir xil nomer kiritib bo'lmaydi!"), `birth_date`, `parent` (FK);
  - **dublikat tekshiruvi:** (branch, first, last, father_name) unique, bo'sh joylar `trim` qilinib, harf katta-kichikligi hisobga olinmaydi. Xato: "Ushbu o'quvchi avval kiritilgan. Lidlar yoki shartnomalar oynasidan qidiring";
  - `full_name = first + " " + last + " " + father_name`;
  - talaba odatda lid formasidan yaratiladi va filialni lid'dan oladi.
- **Lead:**
  - maydonlar: `branch`, `student`, `source`, `course`, `day_pattern`, `preferred_times` (M2M LessonTime), `status`, `group`, `demo_date` (standart bugun), `demo_attended` (Keldi / Kelmadi), `age_group`, `social_status`, `laptop`, `tags`;
  - `status`: 1. Qayta bog'lanishga · 2. Yangi guruhga kutyapti · 3. Sinov darsga yozildi · 4. Sinov darsga qatnashdi · 5. O'qishni boshladi · 6. Ma'qul kelmadi · 7. Ma'qul kelmadi (Sifatsiz) · 8. Keyinroq o'qiydi;
  - `age_group`: 9-12, 13-15, 16-18, 19-21, 22-24, 25-27, 28-30, 31-33, 34-36, 37-39, 40-42;
  - `social_status`: Maktab o'quvchisi, Oliygoh talabasi, Kompaniya xodimi, Davlat xizmatchisi, Vaqtincha ishsiz;
  - `laptop`: Bor, Yo'q, Sotib oladi;
  - yangi lid formasida yangi talabaning 1- va 2-telefoni majburiy (2-telefon ≠ 1-telefon); standart status — "2. Yangi guruhga kutyapti";
  - formadagi tartib: talaba → yosh guruhi → ijtimoiy holat → noutbuk → teglar;
  - bitta talaba bir filialda faqat bitta lidga ega bo'ladi; shartnomasi bor talabaga yangi lid ochilmaydi;
  - `group` 3, 4, 5-statuslarda ko'rinadi va filial + kurs bo'yicha Faol yoki Rejadagi guruhlardan tanlanadi. `demo_date` guruh tanlangach, `demo_attended` sana kiritilgach chiqadi;
  - hisoblanadigan: "Shartnoma statusi" (Tuzilgan / Tuzilmagan), lid oyi va yili (`created_at` bo'yicha), talabaning to'lovlari ro'yxati;
  - **5-statusda:** tug'ilgan sana bo'sh bo'lsa, talaba ma'lumotlarini to'ldirish formasiga yo'naltiriladi. Shartnomasi yo'q bo'lsa "Shartnoma tuzish" tugmasi chiqadi: filial, talaba, kurs, guruh, `start_date = demo_date`, `type = Pullik` bilan shartnoma yaratib, uning sahifasini ochadi.
- **LeadComment:** `lead`, `comment` (filial lid'dan olinadi).

### 7.4 O'quv jarayoni

- **Group:**
  - maydonlar: `branch`, `course`, `day_pattern`, `time` (shu filialdan), `teacher` (USTOZ yoki USTOZ_YORDAMCHI, shu filialda), `supporter` (YORDAMCHI yoki USTOZ_YORDAMCHI, ixtiyoriy), `room` (shu filialdan), `start_date` (standart bugun), `end_date` (> start; xato: "Boshlanish sanadan kichik bo'lolmaydi!"), `number`, `comment`;
  - `number` avtomatik: (branch, course) bo'yicha max+1. Nomi: `"{course} / #{number}"`;
  - filialni yaratilgandan keyin o'zgartirib bo'lmaydi; kursni yaratilgandan keyin faqat Admin o'zgartiradi;
  - `status` (hisoblanadi): end bo'sh bo'lsa start > bugun → Rejada, aks holda Faol. End bor bo'lsa start ≤ bugun ≤ end → Faol, start > bugun → Rejada, aks holda Nofaol;
  - to'lish foizi = faol shartnomalar ÷ xona sig'imi (sig'im 0 yoki xona yo'q bo'lsa "—");
  - to'lish holati: 0 → Bo'sh, ≤ 50% → Yomon, ≤ 75% → O'rtacha, ≤ 85% → Yaxshi, > 85% → Zo'r (ranglar: qizil, to'q sariq, ko'k, yashil);
  - bo'sh o'rinlar = sig'im − faol shartnomalar; faol va nofaol talabalar ro'yxati.
- **Contract:**
  - maydonlar: `branch`, `student` (shu filialdan), `course` (filialdagi faol kurs), `group` (shu kurs va filialdagi faol guruh; kurs o'zgarsa guruh tozalanadi), `type`, `number`, `start_date` (standart bugun), `end_date` (≥ start), `stop_reason`, `comment`, `file` (PDF), `opening_balance`;
  - `type`: Grant / Pullik (standart Pullik, faqat Admin va Bosh menejer o'zgartiradi);
  - `number` avtomatik: filial bo'yicha max+1. Nomi: `"{student.full_name} №{number}"`;
  - `stop_reason` (`end_date` bo'lsa majburiy): Kursni tamomladi, Moliyaviy qiyinchilik, Dars sifatidan qoniqmadi, Markaz sharoiti yoqmadi, Chetlashtirildi - o'zlashtirish past, Chetlashtirildi - xulqi yomon, Kurs yoqmadi - Boshqa kursga o'tyapti;
  - filial va talaba yaratilgandan keyin o'zgarmaydi; kursni faqat Admin o'zgartiradi;
  - `status`: end bor va end < bugun → Nofaol; start > bugun → Rejada; aks holda Faol (AppSheet formulasi buzilgan, 18-bo'lim 1-savol);
  - **qarz:** `debt = Σ attendance.student_debt − Σ payments.amount − Σ payments.discount + opening_balance`. Shartnoma sahifasida "Shartnoma summasi" (Σ student_debt), "To'lov summasi", "Chegirma summasi" va "Balans" ko'rsatiladi;
  - ko'rsatiladi: talaba telefonlari, guruh, filial va kurs nomlari, yosh guruhi (lid'dan).
- **Davomat olish ekrani** (AppSheet'dagi TakeAttendance o'rniga; alohida jadval yo'q). **Davomatni faqat ustoz oladi:**
  1. Ustoz o'z faol guruhini tanlaydi (bitta bo'lsa avtomatik). Menejerlar istalgan ustoz va guruhni tanlaydi.
  2. Sana: ustoz uchun faqat bugun; Admin, Bosh menejer, Filial menejeri va administratorlar tuzatish uchun ≤ bugun. Sana guruh dars kunlariga mos bo'lishi shart. Xatolar: "Guruhning bu sanaga darsi yo'q", "Kelajak sana bilan davomat olib bo'lmaydi", "Faqat bugunga davomat olish mumkin, xolos".
  3. O'rindosh ustoz yoki yordamchi ko'rsatilishi mumkin. Buni Admin, Bosh menejer va administratorlar belgilaydi. O'rindosh guruhning o'z ustozidan farq qiladi.
  4. Ekranda shu sanada faol talabalar chiqadi (`start ≤ sana` va `end` bo'sh yoki `end ≥ sana`), hali belgilanmaganlari yuqorida.
  5. Har bir talaba uchun katta tugmalar: **Keldi** (yashil), **Sababli** (sariq, izoh bilan), **Besabab** (qizil). "Hammasi keldi" tugmasi ham bor.
  6. (group, contract, date) unique.
- **Attendance:**
  - maydonlar: `branch`, `group`, `course`, `contract`, `date`, `status`, `teacher` (darsni amalda o'tgan, o'rindosh bo'lsa o'rindosh), `supporter` (guruh yordamchisi yoki o'rindosh yordamchi), `day_pattern`, `contact_status`, `comment`;
  - `contact_status`: Bog'lanishga, Gaplashildi, Tushib bo'lmadi, Noto'g'ri raqam. X va 0 uchun standart "Bog'lanishga". "Gaplashildi" bo'lsa izoh majburiy;
  - **saqlanadigan hisoblangan maydonlar:** `student_debt`, `teacher_kpi`, `supporter_kpi` (servisda hisoblanadi, 8-bo'lim).
- **MakeupRequest** (yangi): 9-bo'lim.
- **StudentTask** — **olib tashlangan** (buyurtmachi qarori 2026-10-13), quyidagi tavsif tarix uchun:
  - maydonlar: `branch`, `teacher` (ustoz uchun avtomatik o'zi), `course`, `group`, `contract`, `task`, `deadline` (standart bugun+3), `status`, `completion_rate` (0–100, faqat Tamomladi bo'lsa), `teacher_comment` (Tamomladi, Bajarmadi, Bajarolmadi bo'lsa);
  - `status`: Rejada (standart), Yuklatildi, Tamomladi, Bajarolmadi, Bajarmadi.
- **TeacherEvaluation** (Baholash, talaba ustozni baholaydi; javoblarni administrator kiritadi):
  - maydonlar: `branch`, `date`, `contract`, `group` va `teacher` (shartnomadan avtomatik), `comment`;
  - 5 ta mezon, har biri 0–10: mavzuni sodda tushuntira oladimi; dars qiziqmi, qiziq metodlardan foydalanadimi; adolatlimi, teng e'tibor qiladimi; kerak vaqtda yordam beradimi; kamchiliklar haqida tavsiya berib ruhlantiradimi;
  - jami = mezonlar yig'indisi.
- **GradingSession / StudentGrade** — **olib tashlangan** (buyurtmachi qarori 2026-10-13), quyidagi tavsif tarix uchun (Baholash_tizimi + B_Students, ustoz talabani baholaydi):
  - sessiya: `branch`, `teacher`, `course`, `group`, `date`, `comment`;
  - har bir talaba (guruhdagi faol shartnoma): davomat bali (1–20), vazifa bali (1–40), oy yakuniy bali (1–500), jami, izoh;
  - bir sessiyada bir talaba bir marta baholanadi.
- **ParentCall** (Parent_Comment): `branch`, `course`, `group`, `contract`, `date`, `comment`. Telefonlar (1- va 2-telefon, vasiy) talabadan olinadi, qo'ng'iroq (`tel:`) va SMS (`sms:`) havolalari ko'rsatiladi. Ro'yxat sahifasida chapda AppSheet'dagidek daraxt: **Barchasi → (filial) → kurs → guruh**, har birida yozuvlar soni; bosilgan tugun bo'yicha jadval filtrlanadi (filial bitta bo'lsa filial darajasi ko'rinmaydi). Izohni tahrirlash (sana va izoh; kurs, guruh, talaba o'zgarmaydi) va o'chirish (soft delete) mumkin. Tahrirlangan izoh ostida kichik yozuv: "✎ {kim} · {sana vaqt}", "Kim" ustunida qo'shgan shaxs va vaqti. Muddatlar 6.4 bo'yicha; o'chirish hozircha faqat Admin va Bosh menejerda. Ota-ona sahifasida farzandlari va qo'ng'iroqlar tarixi chiqadi.
- **Discount50** — **50% chegirmalar bo'limi olib tashlangan** (buyurtmachi qarori 2026-10-13): model, menyu va ruxsat bo'limi yo'q. «50% Chegirma» nomli chegirma turi oddiy to'lov chegirmasi sifatida qolgan (Sozlamalarda o'chirish mumkin).

### 7.5 Moliya

- **Account** (G'azna):
  - maydonlar: `name` (unique), `responsible` (M2M User; rollar: Admin, Bosh menejer, Administrator+Hisobchi, Hisobchi), `cash_type` (Cash / Bank / Card / All), `initial_balance`, `status`;
  - mas'ullarni faqat Admin va Bosh menejer o'zgartiradi;
  - hozir ikkita g'azna bor: "Emirat g'azna" (All) va "Bosh g'azna" (Karta).
- **CashMovement** (yangi, yagona pul harakatlari jurnali / ledger):
  - har bir to'lov, xarajat, oylik berish, o'tkazma, almashtirish va kreditor amali servis orqali bir yoki bir nechta `CashMovement` qatorini yaratadi; manba o'zgarsa yoki o'chirilsa, qatorlar ham yangilanadi;
  - maydonlar: `account`, `cash_type`, `amount` (+/−), `date`, `source_type`, `source_id`, `is_confirmed`;
  - **g'azna balansi = initial_balance + Σ tasdiqlangan harakatlar**, `cash_type` bo'yicha alohida ham. Indeksli aggregatsiya bilan olinadi va AppSheet'dagi ulkan `Accounts.Now` formulasini almashtiradi.
- **Payment:**
  - maydonlar: `branch` (shartnomadan), `contract`, `group` (shartnomadan), `date`, `amount`, `cash_type` (standart Cash, All tanlanmaydi), `comment`, `receipt_pdf`;
  - `date`: Admin va Bosh menejer ≤ bugun kiritadi ("Kelasi davr bilan kiritib bo'lmaydi"), boshqalar faqat bugun ("Faqat bugun bilan kiritish mumkin, xolos");
  - chegirma: `discount_type`, `discount`. **Limit majburiy:** `|discount| ≤ discount_type.max_amount`. Xato: "Bu chegirma turiga X so'mdan ortiqcha chegirma kiritib bo'lmaydi";
  - `discount_confirmation` (Tasdiqlashga / Tasdiqlandi), `discount_confirmed_by`, `discount_confirmed_at`: Admin istalgan vaqtda, Bosh menejer yaratilganidan keyin 30 kun ichida tasdiqlaydi;
  - `noncash_confirmation`, `noncash_confirmed_by`, `noncash_confirmed_at`: Cash bo'lmagan to'lovni Admin istalgan vaqtda, Bosh menejer 360 kun, Filial menejeri 7 kun ichida tasdiqlaydi;
  - `cashbox`: Cash bo'lsa foydalanuvchi mas'ul bo'lgan faol g'azna (Admin va Bosh menejer — istalgan faol g'azna, buyurtmachi qarori 2026-10-13), naqdsiz bo'lsa `branch.noncash_cashbox`;
  - `accountant`: g'azna mas'ullaridan biri;
  - naqdsiz to'lov tasdiqlanmaguncha g'azna balansiga qo'shilmaydi;
  - **PDF chek** avtomatik yaratiladi, to'lov o'zgarsa qayta yaratiladi va qayta yuklab olinadi;
  - ko'rsatiladi: shartnoma statusi, guruhdagi o'quvchilar soni.
- **Transfer** (Ichki pul oqimi):
  - maydonlar: `date` (standart bugun, faqat Admin va Bosh menejer o'zgartiradi), `sender_account` (foydalanuvchi mas'ul bo'lgan faol g'azna), `sender_cashier`, `cash_type` (faqat Cash), `amount` (≥ 0), `receiver_account` (faol, ≠ sender), `receiver_cashier`, `status` (Tasdiqlashga → Tasdiqlandi), `confirmed_by`, `comment`;
  - `amount` ≤ jo'natuvchi g'azna qoldig'i (Admin va Bosh menejerdan tashqari). Xato: "G'aznada X so'm pul bor" yoki "G'aznada pul yo'q";
  - yaratilgandan keyin summa va pul turini faqat Admin o'zgartiradi;
  - tasdiqni qabul qiluvchi g'azna mas'uli yoki Admin beradi. Tasdiqlanmaguncha ikkala tomonda ham hisobga olinmaydi;
  - ro'yxatda har bir foydalanuvchiga yo'nalish ko'rsatiladi: Chiquvchi / Kiruvchi / Boshqa.
- **Exchange** (Pul ayirboshlash, faqat Admin va Bosh menejer): `account`, `date` (bugun), `from_type`, `amount`, `to_type` (≠ from), `amount_to` (≤ amount, xato: "X dan katta bo'lolmaydi"), `loss = amount − amount_to`.
- **Expense:**
  - maydonlar: `branch`, `date`, `category`, `name` (shu kategoriyadagi oldingi nomlar taklif qilinadi; kategoriya o'zgarsa tozalanadi), `quantity` (≥ 1), `price` (≥ 0), `total = quantity × price`, `cash_type`, `account`, `cashier`, `period_year`, `period_month` (hisob davri; standart sanadan, faqat Admin va Bosh menejer o'zgartiradi), `comment`;
  - `total` ≤ g'azna qoldig'i (Admin va Bosh menejerdan tashqari). Xato: "G'aznada X so'm pul bor".
- **Creditor** (faqat Admin va Bosh menejer): `name` (unique), `initial_balance` (yaratilgandan keyin faqat Admin o'zgartiradi); joriy haqqi = initial − Σ amallar.
- **CreditorTransaction** (CashFlow): `date`, `creditor`, `amount`, `cash_type`, `account`, `cashier`, `comment`. Belgisi: **"−" qarz olish, "+" qarz qaytarish.** Formada shu ogohlantirish ko'rsatiladi. G'aznaga ta'siri: `CashMovement.amount = −amount`.
- **CreditorComment:** `creditor`, `comment`.
- **SalaryAssignment** (Oylik belgilash):
  - maydonlar: `branch`, `user` (Admin emas, shu filialda), `year`, `month`, `fixed`, `bonus`, `kpi` (qo'lda), `fine` (≥ 0), `comment`;
  - (branch, user, year, month) unique;
  - avtomatik: `teacher_kpi`, `supporter_kpi`, `total` (8.4), `given` (shu oy uchun berilganlar), `carried_from_previous` (barcha oldingi davrlarning `total − given` yig'indisi, **yillar oralig'ida ham**), `final_balance = total + carried − given`.
- **SalaryPayout** (Oylik berish): `branch`, `user`, `year`, `month`, `date` (bugun), `type` (O'zgarmas / Bonus / KPI), `amount` (≥ 0; ≤ g'azna qoldig'i, Admin va Bosh menejerdan tashqari), `cash_type`, `account`, `cashier`, `comment`.

### 7.6 Eksport

- **ExcelExport:** filial → kurs → guruhlar (ko'p tanlov) bo'yicha shartnomalar ro'yxati `.xlsx` ga yuklanadi (AppSheet'dagi "Shartnoma yuklash" boti o'rniga).
- Har bir ro'yxat sahifasida joriy filtr bilan "Excel'ga yuklash" tugmasi bor.

## 8. Hisob-kitob algoritmlari

Hammasi servis modullarida bo'ladi va har biri uchun unit-test yoziladi.

### 8.1 Oydagi dars soni

```
frequency(branch, day_pattern, course, year, month)
  = LessonFrequency(status=Tasdiqlangan): aynan shu filial + dars kunlari + kurs + oy
```
Topilmasa yoki tasdiqlanmagan bo'lsa, qarz va KPI hisoblanmaydi (0 emas, "hisoblanmagan" holat) va ogohlantirish chiqadi.

### 8.2 Talaba qarzi (har bir davomat qatori)

```
agar status == NOFAOL ("-")  yoki  contract.type == Grant:   student_debt = 0
aks holda (KELDI, SABABLI, BESABAB):
    student_debt = price(branch, course, oy) / frequency(branch, day_pattern, course, oy)
```
Qoida: **dars bo'ldimi, qarz yoziladi**, talaba kelmagan bo'lsa ham.

### 8.3 Ustoz va yordamchi KPI (har bir davomat qatori)

```
agar contract.type == Grant  yoki  status in (BESABAB, NOFAOL):  kpi = 0
aks holda (KELDI, SABABLI):
    rate = KPIRate(branch, user, role_type, course, oy)
    O'zgarmas:  kpi = rate.fixed_amount / frequency(...)
    Foiz:       kpi = rate.percent / 100 × price(branch, course, oy) / frequency(...)

teacher_kpi   = formula, user = attendance.teacher,   role_type = USTOZ
supporter_kpi = formula, user = attendance.supporter, role_type = YORDAMCHI
```
- `fixed_amount` = bitta o'quvchi uchun oylik kelishilgan summa.
- Yordamchi KPI'si ustoz olgan davomat qatorlaridan guruh yordamchisiga avtomatik yoziladi.
- O'rindosh bo'lsa, KPI darsni amalda o'tgan kishiga yoziladi.
- Stavka topilmasa KPI = 0 va bu "stavka belgilanmagan" ogohlantirishi sifatida ko'rsatiladi.
- Besabab bo'lsa KPI yozilmaydi. Ustoz darsni yetkazib bersa, status SABABLI ga o'zgaradi va KPI yoziladi (9-bo'lim).

### 8.4 Oylik

```
teacher_kpi(user, oy)   = Σ attendance.teacher_kpi   (teacher = user,   filial, yil, oy)
supporter_kpi(user, oy) = Σ attendance.supporter_kpi (supporter = user, filial, yil, oy)

total = fixed + bonus + kpi + teacher_kpi + supporter_kpi − fine
```
Ustoz+Yordamchi rolidagi xodimda ikkalasi bo'lishi mumkin. **Jarima ayiriladi.**

### 8.5 Qayta hisoblash

Narx, KPI stavkasi, dars soni, shartnoma turi yoki davomat statusi o'zgarganda tegishli oy va shartnomalarning `student_debt`, `teacher_kpi`, `supporter_kpi` qiymatlari `transaction.atomic` ichida qayta hisoblanadi. Qo'lda ishga tushirish uchun `python manage.py recalculate --month 2026-10` buyrug'i bo'ladi.

### 8.6 Foyda (oyma-oy)

```
Foyda = Σ to'lovlar − Σ xarajatlar (kind = "Xarajat") − Σ hisoblangan oyliklar (SalaryAssignment.total)
```
- Filtrlar: filial, yil, bir nechta oy.
- "Qayta investitsiya", "Dividend", "Tashqi qarz" alohida qatorlarda ko'rsatiladi.
- Ranglar: to'lovlar ko'k, xarajatlar pushti, foyda musbat yashil, manfiy qizil.
- AppSheet'dagi Balance "kalkulyator" jadvali kerak emas, bu oddiy filtrli hisobot sahifasi.

## 9. Qoldirilgan darsni yetkazish (yangi jarayon)

**Hozir:** oy oxirida ustoz adminga og'zaki aytadi, admin X ni 0 ga o'zgartiradi.

**Yangi jarayon:**
1. Ustoz "Kelmaganlar" ro'yxatidan BESABAB qatorni tanlaydi va **"Darsni yetkazdim"** so'rovini yuboradi (yetkazilgan sana va izoh bilan).
2. So'rov Bosh menejer, Filial menejeri va administratorlarga tushadi, Telegram'ga ham xabar boradi.
3. Tasdiqlansa, davomat statusi SABABLI ga o'zgaradi va KPI qayta hisoblanadi. Rad etilsa, sabab yoziladi.
4. Hammasi audit'ga yoziladi.

Model: `MakeupRequest(attendance, teacher, makeup_date, comment, status [Kutilmoqda / Tasdiqlandi / Rad etildi], reviewed_by, reviewed_at, reject_reason)`.

## 10. Interfeys va menyu

Menyu tartibi va nomlari AppSheet'dagidek saqlanadi, xodimlar qayta o'rganmasin. Har bir rol faqat ruxsat berilgan bo'limlarni ko'radi.

1. **Bosh sahifa (Dashboard)**, yangi.
2. **Lidlar:** voronka (status bo'yicha), statistika, to'lov qilganlar.
3. **Shartnomalar:** Faol / Nofaol, guruhlash filial → kurs.
4. **To'lovlar:** yil → oy → sana, jami summa bilan.
5. **Qarzdorlar:** qarzi > 0, guruh bo'yicha, jami qarz bilan.
6. **Davomatlar:** davomat olish ekrani, kelmaganlar (X va 0, bog'lanish holati bilan), statistika, qoldirilgan darslar so'rovlari.
7. ~~Baholash bo'limi (ustoz → talaba)~~ — olib tashlangan (2026-10-13).
8. **Foyda (oyma-oy):** Admin, Bosh menejer.
9. **Xarajatlar bo'limi:** sana bo'yicha va oy → kategoriya bo'yicha.
10. **Shartnoma yuklash:** Excel eksport.
11. **Faol guruhlar tahlili:** to'lish holati, ustoz va kurs bo'yicha.
12. **Guruhlar.**
13. ~~50% chegirmalar~~ — olib tashlangan (2026-10-13).
14. **Tasdiqlashlar:** chegirmalar, naqdsiz to'lovlar, o'tkazmalar, qoldirilgan darslar, oydagi dars soni.
15. **Oyliklar:** KPI belgilash, hisoblangan KPI (ustozlar, yordamchilar), oylik belgilash, oylik berish, xodim balansi.
16. **Ichki pul oqimi:** g'aznalar orasida o'tkazma.
17. **Tashqi pul oqimi:** kreditorlar (Admin, Bosh menejer).
18. **Pul ayirboshlash** (Admin, Bosh menejer).
19. **G'aznalar:** joriy qoldiq bilan.
20. **Baholash:** talaba ustozni baholaydi.
21. ~~Talaba vazifalari~~ — olib tashlangan (2026-10-13).
22. **Ota-onalar bilan aloqa.**
23. **Sozlamalar:** barcha ma'lumotnomalar. Bosh menejer hammasini, Filial menejeri o'z filiali doirasida boshqaradi. Bo'limlar: kurslar, kurs narxlari, oydagi dars soni (oylik tasdiq bilan), KPI stavkalari, chegirma turlari, xarajat kategoriyalari, lid manbalari, xonalar, dars kunlari, dars vaqtlari, filiallar, g'aznalar, foydalanuvchilar (qo'shish, rol berish, filial biriktirish, ishdan chiqarish), rollar va ruxsatlar, davomat statuslari.
24. **AI yordamchi:** faqat Bosh menejer (13-bo'lim).
24a. **Qo'ng'iroqlar** (2026-10-19): qabul telefonidagi qo'ng'iroqlar, statistika, qurilmalar (0-bo'lim).
25. **Audit tarixi:** Admin va Bosh menejer.

UX talablari:
- Formalar bosqichma-bosqich: keyingi maydon oldingisi to'ldirilgach chiqadi (AppSheet `Show_If`). Bog'liq ro'yxatlar avtomatik filtrlanadi: filial → kurs → guruh → talaba. Tanlov bitta bo'lsa, u avtomatik tanlanadi va maydon yashiriladi.
- Ro'yxatlarda qidiruv, filtrlar, guruhlash, jami summalar va sahifalash (50 tadan) bor.
- Ranglar (AppSheet format qoidalari): shartnoma Faol yashil, Nofaol qizil; qarzdor talaba nomi qizil; guruh to'lish holati rangli; foyda musbat yashil, manfiy qizil; lid shartnoma holati "Tuzilmagan" 5-statusda qizil, boshqa statuslarda to'q sariq.
- Telefonda davomat ekrani bir qo'l bilan qulay: katta tugmalar.
- Yaratgan/o'zgartirgan shaxs va vaqt formalarda ko'rinmaydi, faqat batafsil sahifada.

## 11. Dashboard va statistika (yangi)

**Bosh sahifa** (rolga mos):
- bugungi to'lovlar (naqd, naqdsiz);
- g'azna qoldiqlari;
- jami qarzdorlik va qarzdorlar soni;
- faol talabalar, faol guruhlar va ularning to'lish holati;
- tasdiq kutayotganlar soni;
- shu oy uchun dars soni tasdiqlanmagan bo'lsa ogohlantirish;
- bugun davomati olinmagan guruhlar.

**Oylik statistika** (Chart.js, oyma-oy taqqoslash):
- yangi lidlar (manba va kurs bo'yicha);
- yangi va to'xtatilgan shartnomalar (to'xtatish sababi bo'yicha);
- to'lovlar, xarajatlar va foyda;
- o'rtacha davomat foizi (guruh va ustoz bo'yicha).

**Sotuv voronkasi:** har bosqichdagi lidlar soni va o'tish foizi. Filtrlar: davr, manba, kurs, mas'ul xodim. Lid → to'lov konversiyasi ham ko'rsatiladi.

**Birinchi marta to'lov qilganlar:** tanlangan oyda birinchi marta to'lov qilgan talabalar soni va ro'yxati, manba va kurs kesimida.

Hisobot so'rovlari aggregatsiya bilan bajariladi. Og'ir hisobotlar uchun kesh (15 daqiqa) yoki tunda hisoblanadigan jadval ishlatiladi.

## 12. Telegram bot (xodimlar uchun)

- Xodim `/start` yozadi va profilidagi bir martalik kod bilan akkauntini bog'laydi.
- Xabarlar:
  - yangi lid (filial administratorlariga);
  - tasdiq kutayotgan chegirma yoki naqdsiz to'lov (Bosh menejer, Filial menejeri);
  - tasdiq kutayotgan o'tkazma (qabul qiluvchi g'azna mas'uliga);
  - qoldirilgan dars so'rovi;
  - dars boshlanganidan keyin N daqiqa (standart 30) ichida davomat olinmasa (ustoz va administratorga);
  - **dars boshlanganda** guruh ustoziga «davomat olish vaqti» (bot jarayoni har daqiqada tekshiradi, alohida cron yo'q);
  - **botda davomat olish — Telegram Mini App** (`apps/notifications/webapp.py`, `POST /api/v1/auth/telegram/`): xabardagi «📋 Davomat olish» tugmasi va bot menyusidagi «Davomat» saytdagi davomat ekranini Telegram ichida parolsiz ochadi (bog'langan faol xodim);
  - **8:30** da Administrator+Hisobchi'ga bugungi ish rejasi: olinadigan to'lovlar (dars vaqti bo'yicha qarzdorlar), sinov darsiga keladiganlar, kelmaganlar bilan bog'lanish, qayta bog'lanish lidlari, kecha olinmagan davomat (`morning_plan`, cron);
  - har kuni **19:00** da Bosh menejerga hisobot (buyurtmachi so'rovi 2026-10-14): to'lovlar, faol shartnomalar (kurslar bo'yicha), lidlar (statuslar va kurslar bo'yicha), qo'ng'iroqlar (2026-10-19: jami, javobsiz qolganlar ro'yxati, qayta javob vaqti, yangi raqamlar), bugungi xarajatlar, davomat, g'azna qoldiqlari, tizim auditi. Faqat audit huquqi borlar (Admin, BM) oladi.
- Har bir xodim qaysi xabarlarni olishini sozlaydi. Token `.env` da saqlanadi.
- **Keyingi bosqich (hozir qilinmaydi):** ota-onalarga SMS yoki Telegram xabarlar (qarz eslatmasi, darsga kelmagani). Arxitektura bunga tayyor bo'lsin.

## 13. AI yordamchi (faqat Bosh menejer)

**Maqsad:** Bosh menejer o'zbek tilida savol beradi va data analitikada yordam oladi. Masalan: "Sentabrda qaysi kurs eng ko'p foyda keltirdi?"

**Arxitektura:**
1. Faqat o'qish huquqiga ega alohida DB foydalanuvchisi. U faqat `analytics_*` view'larni ko'radi; telefonlar va parollar bu view'larga kirmaydi. **Buyurtmachi qarori (2026-10-13):** view'larda talaba ismi va telefonlari bo'lishi mumkin — so'rovni faqat server bajaradi, natija faqat Bosh menejer ekranida, LLM'ga natija qatorlari yuborilmaydi (`docs/decisions.md`, M9). Parollar va xodimlar telefoni/pochtasi kirmaydi.
2. LLM'ga savol va view'lar sxemasi (ustun tavsiflari bilan) yuboriladi, LLM SQL qaytaradi.
3. Server SQL'ni tekshiradi: faqat `SELECT`, faqat ruxsat etilgan view'lar, `LIMIT` va 5 soniya timeout.
4. Natija jadval yoki Chart.js diagramma qilib ko'rsatiladi.
5. Ixtiyoriy: natijaning faqat yig'ma ko'rinishi LLM'ga qayta yuborilib, qisqa tahlil olinadi. Talabalar ismlari LLM'ga yuborilmaydi.
6. Har bir savol, SQL va natija hajmi log'ga yoziladi.

**Provayder:** `AI_PROVIDER=gemini|anthropic|openai` bilan almashtiriladi. Boshida Gemini bepul tarifi bo'lishi mumkin; bepul tariflarda ma'lumot xizmatni yaxshilash uchun ishlatilishi mumkin, shuning uchun 1, 3 va 5-bandlar majburiy. Kunlik so'rovlar limiti sozlanadi.

## 14. Tezlik, sifat va xavfsizlik

- Har qanday ro'yxat yoki forma sahifasi serverda **< 300 ms**, foydalanuvchida **< 1 s**.
- N+1 so'rovlar taqiqlanadi (`select_related` / `prefetch_related`). Testlarda `django_assert_max_num_queries` bilan tekshiriladi.
- Indekslar: filial, sana, (yil, oy), guruh, shartnoma, status, `created_by`, `legacy_id`.
- Hisoblangan qiymatlar (qarz, KPI, balans) saqlanadi yoki indeksli aggregatsiya bilan olinadi. Butun jadvalni Python'da aylanib chiqish taqiqlanadi.
- Statik fayllar siqiladi va keshlanadi (WhiteNoise yoki Nginx).
- CSRF, HTTPS, xavfsiz cookie'lar, login urinishlariga limit, parol kamida 4 belgi (buyurtmachi qarori 2026-10-13; kuchaytirish kerak bo'lsa — `config/settings/base.py` `AUTH_PASSWORD_VALIDATORS`), sirlar `.env` da, prod'da `DEBUG=False`.
- Kodga hech qanday ID, email yoki parol qattiq yozilmaydi.

## 15. Deploy

Tasdiqlangan (2026-10-12): **bitta Hetzner VPS'da ikki muhit** — test (M1 dan) va asosiy (M11 dan). PythonAnywhere ishlatilmaydi.

- Server: Hetzner Cloud **CAX11** (Arm64, 2 vCPU, 4 GB RAM, 40 GB), Helsinki, Ubuntu 24.04, `77.42.9.23`. Cost-Optimized x86 mavjud emas edi; Arm64'da hammasi ishlaydi.
- Har bir muhit: `deploy/docker-compose.yml` — `db` (PostgreSQL 16) + `web` (Gunicorn), `127.0.0.1:8001` (test) / `8002` (prod). **Nginx, certbot va cron — serverning o'zida** (apt), Docker'da emas.
- Papkalar: `/srv/codial-test`, keyin `/srv/codial-prod` (git checkout), sirlar `deploy/.env` da (git'ga kirmaydi, `chmod 600`).
- Zaxira: `deploy/backup.sh` har kuni 03:15 (cron), `/srv/backups/codial-<env>`, 30 kun. Tiklash: `deploy/restore.sh`.
- Har oy 1-kuni 06:00: `propose_lesson_frequencies` (cron).
- Qo'llanma va joriy holat: `docs/deploy_hetzner.md` (0-bo'lim — server, manzil, cron; yangilash; muammolar jadvali).
- **Eslatma:** O'zbekistonda fuqarolarning shaxsiy ma'lumotlarini mamlakat hududida saqlash talabi bor. Buyurtmachi Hetzner'ni tanladi va buni o'zi tekshiradi. Kod Docker'da — istalgan hostingga ko'chiriladi.

## 16. Migratsiya (faqat faol ma'lumotlar)

**Manba:** Google Sheets'dan yuklab olingan `.xlsx` fayllar, `import_data/` papkasida. Faqat **Emirat** filiali ko'chiriladi.

Avval `python manage.py import_appsheet --dry-run` ishga tushiriladi va xatolar hamda ogohlantirishlar hisobotini chiqaradi. Keyin haqiqiy rejimda ishlatiladi.

**Ko'chiriladiganlar:**
1. Ma'lumotnomalar: filial (Emirat), faol kurslar, xonalar, dars kunlari, dars vaqtlari, chegirma turlari, xarajat kategoriyalari, lid manbalari, g'aznalar, kreditorlar.
2. Foydalanuvchilar: AppSheet `Status` = "Qo'shilgan" bo'lsa Faol, "Qo'shilmagan" bo'lsa Ishdan ketgan. Rollar 6.1 bo'yicha moslashtiriladi, eski xato nomlar ham ("Yordmachi", "Ustoz-Yordamchi", "Filial menejer") taniladi. Parollar yangidan beriladi: birinchi kirishda parol o'rnatish havolasi yuboriladi.
3. Joriy kurs narxlari va KPI stavkalari, `effective_from` = joriy oyning 1-kuni.
4. Joriy oy uchun oydagi dars soni (Tasdiqlangan holatda).
5. Faol va rejadagi guruhlar.
6. Faol va rejadagi shartnomalar, ularning talabalari va ota-onalari, ochiq lidlar (1–4 va 8-statuslar).
7. **Boshlang'ich qoldiqlar** (o'tish sanasi holatiga):
   - har bir shartnomaning joriy qarzi → `Contract.opening_balance`;
   - har bir g'aznaning joriy qoldig'i → `Account.initial_balance`;
   - kreditorlarning joriy haqqi;
   - xodimlarning oylik qoldig'i (`ToMonthBalance`) → `carried_from_previous` uchun boshlang'ich yozuv.

**Qoidalar:**
- Har bir yozuvda `legacy_id` saqlanadi.
- Importni qayta ishga tushirish dublikat yaratmaydi (idempotent).
- Oxirida tekshiruv hisoboti chiqadi (faol shartnomalar soni, jami qarz, g'azna qoldiqlari). Bu raqamlar AppSheet ko'rsatkichlari bilan solishtiriladi.

## 17. Bosqichlar (milestone'lar)

Real ishga tushirish uchun minimal to'plam: **M1–M7 + M10 + M11** (xodimlar AppSheet'dagi hamma bo'limdan foydalanadi). M8 va M9 — keyin.

| # | Bosqich | Natija | Holat |
|---|---|---|---|
| M0 | Prototip | Bosiladigan HTML prototip | ✅ |
| M1 | Loyiha asosi | Django + DRF, Docker, User/Role/ruxsatlar, filial doirasi, audit, login va parol havolasi, Sozlamalar, Audit tarixi, front-end ulandi, test server | ✅ 2026-10-12 |
| M2 | CRM | Talabalar, ota-onalar, lidlar (voronka, forma, izohlar, statistika), "Shartnoma tuzish" tugmasi (shartnoma o'zi M3 da) | ✅ 2026-10-13 |
| M3 | O'quv jarayoni | Guruhlar, shartnomalar, qarzdorlar, davomat ekrani, qarz va KPI servislari, kelmaganlar, qoldirilgan darslar, qayta hisoblash; lidda guruh va «Shartnoma tuzish», shartnoma konversiyasi, Shartnomalar → «Talabalar» | ✅ 2026-10-13 |
| M4 | Moliya | CashMovement ledger, g'aznalar balansi, to'lovlar (tasdiqlar, chegirma limiti, PDF chek), o'tkazmalar, almashtirish, xarajatlar, kreditorlar, Tasdiqlashlar; shartnoma balansiga to'lovlar | ✅ 2026-10-13 |
| M5 | Oyliklar | KPI stavkalari (o'zgarsa qayta hisoblash), oylik belgilash va berish (g'aznaga `CashMovement` SALARY), KPI daraxti, xodim balansi | ✅ 2026-10-13 |
| M6 | Qo'shimcha modullar | Ustozni baholash, ota-onalar bilan aloqa, Excel eksport (vazifalar, baholash bo'limi, 50% chegirma — olib tashlangan) | ✅ 2026-10-13 |
| M7 | Hisobot va dashboard | Bosh sahifa, oylik statistika, voronka, birinchi to'lovchilar, foyda, guruh tahlili | ✅ 2026-10-13 |
| M8 | Telegram bot | Bog'lash, xabarlar, kunlik hisobot | ✅ 2026-10-13 |
| M9 | AI yordamchi | Faqat o'qish view'lari, SQL xavfsizligi, provayder abstraksiyasi | ✅ 2026-10-14 |
| M10 | Migratsiya | Import skripti, sinov rejimi, tekshiruv hisoboti (doira: faqat faol shartnomalar, qarzsiz) | ✅ 2026-10-14 |
| M11 | Ishga tushirish | Asosiy muhit (`erp.codialinfo.uz`), o'tish kuni, monitoring | ✅ 2026-10-18 |

Har bir bosqichda bo'ladi: algoritm va ruxsatlar uchun testlar, `seed_demo` buyrug'i (sinov ma'lumotlari), qisqa foydalanuvchi qo'llanmasi (`docs/user_guide/`).

## 18. Ochiq savollar (kod boshlanishidan oldin buyurtmachidan so'ra)

Asl topshiriqdan:
1. **Shartnoma statusi:** AppSheet formulasi buzilgan (`IFS([EndDate]=TODAY()), "Faol", …`). Taxmin: end < bugun → Nofaol, start > bugun → Rejada, aks holda Faol. Tasdiqlansin.
2. **Kreditor amali sanasi:** formula buzilgan (`[_THIS]TODAY()`). Xato matni "bir hafta avvalgi sanagacha" deydi. Taxmin: oxirgi 7 kun ichida, kelajak sana mumkin emas.
3. ~~**50% chegirma:**~~ **Yopildi (2026-10-13): bo'lim butunlay olib tashlandi.** Eski savol: aniq qoidasi qanday? Kimga, qachon beriladi va to'lovdagi chegirma bilan qanday bog'lanadi? AppSheet'da Discount50 to'lovga bog'lanmagan, faqat ro'yxat edi. Guruhda ≥ 3 o'quvchi sharti nimani anglatadi?
4. **"Nofaol (–)" davomat statusini** kim va qachon qo'yadi?
5. **"All" turidagi g'azna:** balans har bir to'lov turi bo'yicha alohida ko'rsatilsinmi?
6. **Davomat olinmagani haqidagi eslatma:** dars boshlanganidan necha daqiqa keyin? (standart 30)
7. **Xarajat kategoriyasining `allowed_roles` maydoni** majburiy tekshirilsinmi?

JSON tahlilidan yangi savollar:

8. **Manfiy chegirma:** AppSheet'da `Discount < 0` ruxsat etilgan ("Chegirmalar" slice'i `Discount>0 OR Discount<0`). U nima uchun ishlatilgan, masalan "Boshlang'ich balansga" turi bilan oldingi qarzni kiritish uchunmi? Yangi tizimda bu `opening_balance` bilan almashtirilsinmi?
9. **Pulni qaytarish:** to'lov summasi manfiy bo'lishi mumkinmi (formulalar `Summa<>0` ni tekshiradi)? Qaytarish alohida amal bo'lsinmi?
10. **Administrator to'lov qabul qiladimi?** AppSheet'da `Administrator` roli To'lovlar jadvalida faqat ko'ra olardi, 6.4-jadval esa unga "to'lov: faqat bugun" muddatini beradi. Qaysi biri to'g'ri?
11. **Shartnoma PDF fayli:** AppSheet'da `Contracts/{ContractID}.pdf` yo'li bor. Shartnoma shablondan avtomatik yaratilsinmi yoki qo'lda yuklanadimi? Shablon bormi?
12. **Oylik belgilash noyobligi:** AppSheet'da (filial, xodim, yil, oy) bo'yicha edi. Xodim bir necha filialda ishlasa, har filial uchun alohida oylik bo'ladimi?
13. **Talabaning 2-telefoni** majburiymi? AppSheet formasida tug'ilgan sana faqat 2-telefon kiritilgandan keyin chiqardi.
14. **Ota-onalar bilan aloqa va Excel eksport** bo'limlarini qaysi rollar ishlatadi? AppSheet'da ular uchun cheklov yo'q edi.

## 19. AppSheet'da topilgan va tuzatilishi kerak bo'lgan xatolar

1. Tahrirlash va o'chirish muddatlari ishlamaydi (`TODAY()+N >= sana` doim rost). 6.4 qo'llansin.
2. Jarima jami oylikdan ayirilmagan (`TotalSalary = Fixed+Bonus+KPI+TeacherKPI+SupporterKPI`). 8.4 bo'yicha tuzatilsin.
3. Chegirma limiti (`MaxAmount`) tekshirilmagan: xato matni bor, lekin `Valid_If` yo'q. Endi majburiy.
4. Yordamchi KPI'sida Grant shartnomalar chiqarib tashlanmagan.
5. Foiz-KPI'da (ustoz va yordamchi) va yordamchining O'zgarmas KPI'sida oydagi dars soni dars kunlarisiz qidirilgan (`ANY(SELECT(...))` tasodifiy qiymat olishi mumkin).
6. Oylik qoldig'i (`FromLastMonth`) faqat bir yil ichida o'tkaziladi, yillar oralig'ida yo'qoladi.
7. Rol nomlaridagi xatolar ("Ustoz-Yordamchi", "Yordmachi", "Filial menejer") tufayli ba'zi shartlar hech qachon ishlamagan. Endi rollar FK yoki enum bilan.
8. Kodga qattiq yozilgan ID'lar: `cb4963b4` (naqdsiz g'azna), `914bea1a` (50% chegirma), `10f01992` (foydadan chiqariladigan kategoriya). Endi `Branch.noncash_cashbox`, `ExpenseCategory.kind` ishlatiladi (50% chegirma bo'limi olib tashlangan).
9. `Baholash_tizimi.CreatedBy` va `B_Students.CreatedBy` boshlang'ich qiymati aniq bir email bilan qattiq yozilgan. `request.user` ishlatilsin.
10. Yordamchi KPI oylikka filial bo'yicha filtrlanmasdan yig'ilgan.
11. Sekinlik: g'azna balansi, guruh statistikasi va shartnoma qarzi har ochilishda butun jadvallar bo'yicha qayta hisoblanardi. Endi ledger va saqlanadigan maydonlar.
12. Davomat "sessiyasi" (TakeAttendance) har foydalanuvchi uchun jadval qatori sifatida saqlanardi. Endi u oddiy ekran holati.
13. `Attendance.ContactStatus` da `Required_If = [ContactStatus]="Bog'lanildi"`, ammo bunday qiymat yo'q. To'g'ri qoida: "Gaplashildi" bo'lsa izoh majburiy.
14. `Expenses.Cashier` boshlang'ich qiymati foydalanuvchining to'liq ismi, ruxsat etilgan qiymatlar esa UserID. Bu tur nomuvofiqligi. Endi FK User.
15. `Accounts.Now` ("All" turi) tasdiqlanmagan naqdsiz to'lovlarni ham qo'shgan. Endi naqdsiz to'lov tasdiqlangandan keyin hisobga olinadi.
16. `Exchange`, `CommentToCreditors`, `Parent_Comment`, `Discount50`, `Exel` jadvallarida ruxsat cheklovi bo'lmagan (6.2).
17. `Groups.Open_Place_percent` xona sig'imi 0 yoki xona bo'lmasa nolga bo'linadi. Endi "—" ko'rsatiladi.

---

## 20. Prototip (`prototype/`) — muzlatilgan dizayn namunasi

> **2026-10-12 dan prototip muzlatilgan.** Unga yangi o'zgarish kiritilmaydi — ekranlar `frontend/` da (21-bo'lim) davom etadi. Buyurtmachi yangi o'zgarish so'rasa, u `frontend/` + `backend/` da qilinadi va 20.6 jadvaliga emas, `docs/decisions.md` ga yoziladi.

### 20.1 Bu nima va nima emas

- **Bu:** kelajakdagi tizimning **ishlaydigan maketi**. Oddiy HTML + CSS + JavaScript: framework yo'q, server yo'q, build yo'q. Brauzerda ochiladi, tugmalar bosiladi, formalar saqlanadi, qarz / KPI / g'azna / oylik haqiqatan hisoblanadi.
- **Bu emas:** Django tizimi. Prototip kodi Django'ga ko'chirilmaydi — u **talablar va dizayn namunasi**. Django'da hamma narsa 4–19-bo'limlar bo'yicha qaytadan yoziladi, lekin ekranlar, formalar ketma-ketligi va matnlar prototipdagidek bo'ladi.
- Ma'lumotlar **soxta** (sinov uchun yaratilgan) va faqat foydalanuvchi brauzerida (`localStorage`) saqlanadi. Serverga hech narsa yuborilmaydi.

### 20.2 Qanday ochiladi

| Usul | Qanday |
|---|---|
| Internetda | https://ilhomjon1502.github.io/codialERP1/ |
| Kompyuterda | `python -m http.server 5510 --directory prototype` → http://localhost:5510 |
| Eng oddiy | `prototype/index.html` ni ikki marta bosish |

- Kirish sahifasida parol yo'q — demo xodimni tanlaysiz. O'ng yuqoridagi ism orqali istalgan payt boshqa rolga o'tiladi.
- Yuqoridagi **sana tugmasi**: "bugun"ni o'zgartirish (masalan, dars bor kunga) va ma'lumotlarni boshlang'ich holatga qaytarish.
- Sinov ma'lumotlari: Emirat filiali, 13 xodim (har roldan), 5 kurs, 7 guruh, ~60 shartnoma, ~70 lid, sentabr–oktabr davomatlari, to'lovlar, xarajatlar, oyliklar. AppSheet'dan import sanasi **01.09.2026** deb olingan.

### 20.3 Fayllar xaritasi — "nimani o'zgartirsam, qaysi faylni ochaman?"

| Fayl (`prototype/` ichida) | Ichida nima bor | Qachon ochiladi |
|---|---|---|
| `index.html` | Fayllarni ulaydi, `?v=N` versiya | Har o'zgarishdan keyin `?v=N` ni oshirish |
| `assets/style.css` | Butun dizayn: ranglar (`:root` dagi `--brand` = to'q sariq), tugmalar, jadvallar, telefon ko'rinishi (`@media (max-width: 900px)`) | Rang, o'lcham, joylashuv |
| `assets/js/util.js` | Sana, pul formati (`A.money`), oy nomlari | Kamdan-kam |
| `assets/js/core.js` | **Rollar va ruxsatlar matritsasi** (`MATRIX`), tahrirlash muddatlari (`A.editDays`), ma'lumot doirasi (`A.vis`), **hisob-kitob servislari**: narx, dars soni, qarz, KPI, g'azna ledger, oylik, tasdiq qoidalari | Ruxsat yoki formula o'zgarsa |
| `assets/js/seed.js` | Sinov ma'lumotlari (xodimlar, kurslar, guruhlar, narxlar, KPI stavkalari…) | Demo ma'lumotni o'zgartirish. **O'zgartirsangiz `seed.js` dagi `version` va `core.js` dagi `s.version !== N` raqamini oshiring**, aks holda eski ma'lumot qoladi |
| `assets/js/forms.js` | Modal oyna va bosqichma-bosqich forma (AppSheet `Show_If` / `Valid_If` / `Reset_If` mantig'i) | Forma xatti-harakati |
| `assets/js/app.js` | Layout, chap menyu (`A.NAV` — tartib va nomlar), pastki panel (telefon), login, marshrutlash | Menyu tartibi, nomi, ikonkasi |
| `assets/js/pages-crm.js` | Bosh sahifa, Lidlar (voronka, forma, kartochka), Talabalar, Shartnomalar, Qarzdorlar | Shu sahifalar |
| `assets/js/pages-edu.js` | Guruhlar, Guruhlar tahlili, **Davomat olish**, Kelmaganlar, Qoldirilgan darslar, Vazifalar, Baholash (ikkala yo'nalish), Ota-onalar, 50% chegirma, Excel eksport | Shu sahifalar |
| `assets/js/pages-fin.js` | To'lovlar va chek, Tasdiqlashlar, G'aznalar, O'tkazmalar, Ayirboshlash, Xarajatlar, Kreditorlar, Foyda, Oyliklar | Shu sahifalar |
| `assets/js/pages-admin.js` | Sozlamalar (barcha ma'lumotnomalar, rollar matritsasi, oydagi dars soni), Audit tarixi, AI yordamchi | Shu sahifalar |

Har bir sahifa bir xil shaklda yozilgan: `A.page('marshrut', { title, section, render() {...} })`. `section` — ruxsat kaliti (`core.js` dagi `MATRIX`). Tugmalar `data-act="nom"` orqali `A.act.nom` funksiyasini chaqiradi. Formalar `A.form({ fields: [...] })` bilan yoziladi: har bir maydonda `show` (qachon ko'rinadi), `options`, `validate`, `resets` (qaysi maydonlarni tozalaydi) bor.

### 20.4 Prototipda ishlaydigan narsalar (buyurtmachi ma'qullagan)

- **Rollar:** 10 rol, har biri uchun menyu, tugmalar va ko'rinadigan ma'lumot farq qiladi (6-bo'lim). Ruxsatlar matritsasini Sozlamalar → Rollar va ruxsatlar'da o'zgartirsa bo'ladi.
- **Tahrirlash muddatlari:** muddati o'tgan yozuvda tugma o'chiq va sababi ko'rsatiladi. Tasdiqlangan yozuvni faqat Admin / Bosh menejer o'zgartiradi.
- **Lidlar:** 8 bosqichli voronka (kanban), bosqichma-bosqich forma, dublikat talaba tekshiruvi, izohlar, statistika (manba, konversiya), 5-statusda "talaba ma'lumotlarini to'ldirish" → "Shartnoma tuzish".
- **Shartnomalar:** Faol / Rejada / Nofaol, qarzdor nomi qizil, "Qarz qanday hisoblandi" bloki, to'lovlar va davomat tarixi.
- **Davomat:** faqat ustoz oladi; ustoz uchun faqat bugun, menejerlar o'tgan sanani tuzatadi; dars kuni tekshiruvi; o'rindosh ustoz; telefonda katta Keldi / Sababli / Besabab tugmalari; "Hammasi keldi"; belgilashda qatorlar sakramaydi.
- **Kelmaganlar:** bog'lanish holati, "Gaplashildi" bo'lsa izoh majburiy; ustoz "Darsni yetkazdim" so'rovini yuboradi → menejer tasdiqlaydi → X → 0 va KPI yoziladi.
- **Oydagi dars soni:** kalendar bo'yicha "Taklif" → tasdiqlash → qarz va KPI qayta hisoblanadi. Tasdiqlanmagan oy uchun Bosh sahifada ogohlantirish chiqadi.
- **To'lov:** shartnoma → summa → turi → g'azna (avtomatik) → chegirma (limit tekshiruvi) → chek. Naqdsiz to'lov va chegirma tasdiqlashga ketadi; naqdsiz to'lov tasdiqlanmaguncha g'azna balansiga qo'shilmaydi.
- **G'azna:** yagona pul harakatlari jurnali (ledger), balans to'lov turlari bo'yicha, tasdiqlanmagan summalar alohida.
- **O'tkazma, ayirboshlash, xarajat** (g'aznadagi puldan ko'p bo'lmaydi), **kreditorlar** ("−" qarz olish / "+" qaytarish).
- **Oyliklar:** belgilash, KPI (davomatdan avtomatik), jarima ayiriladi, oldingi oylardan qoldiq yillar oralig'ida ham; KPI stavkalari "amal qilish oyi" bilan; oylik berish; xodim balansi.
- **Foyda:** oylar tanlanadi, faqat "Xarajat" turi ayiriladi; qayta investitsiya / dividend / tashqi qarz alohida.
- **Guruhlar:** to'lish rangi (qizil / to'q sariq / ko'k / yashil), oylik davomat jurnali, tahlil.
- **Boshqalar:** vazifalar, ikki yo'nalishli baholash, ota-onalar bilan aloqa (tel / SMS havolalar), 50% chegirma (≥3 talaba), Excel (CSV) eksport, audit tarixi, AI yordamchi (namunaviy).
- **Telefon:** chap menyu yashirin (☰), pastda 5 tugmali panel, jadvallar kartochkaga aylanadi, formalar pastdan ochiladi.

### 20.5 Prototipdagi soddalashtirishlar (Django'da boshqacha bo'ladi)

| Prototipda | Django'da |
|---|---|
| Parolsiz kirish, demo xodim tanlanadi | Email + parol, login urinishlariga limit |
| `localStorage` | PostgreSQL |
| Excel o'rniga CSV | openpyxl bilan `.xlsx` |
| PDF chek = brauzerda chop etish | WeasyPrint bilan PDF fayl |
| AI javoblari — oldindan yozilgan 6 ta savol | LLM → SQL → tekshiruv (13-bo'lim) |
| Telegram xabarlari yo'q (faqat matnda aytilgan) | Telegram bot (12-bo'lim) |
| "Kalendar bo'yicha taklif" tugma bilan | Har oy 1-kuni cron |
| Bitta filial | Ko'p filialga tayyor model |
| Manfiy to'lov taqiqlangan | 18-bo'limdagi savolga javobga qarab |

### 20.6 Buyurtmachi so'ragan o'zgarishlar

Buyurtmachi so'ragan va bajarilgan o'zgarishlar (hammasi `frontend/` ga ham ko'chgan; Sozlamalardagilari M1 da server bilan ishlaydi, qolganlari o'z bosqichida):

| # | Nima o'zgaradi | Sahifa / fayl | Holat |
|---|---|---|---|
| 1 | Yangi lid formasida talabaning **ikkala telefoni** majburiy (1- va 2-telefon yonma-yon; bir xil bo'lmasin). 18-bo'lim 13-savolga javob: lid orqali yangi talabada 2-telefon majburiy | Lidlar → Yangi lid / `pages-crm.js` (`A.leadForm`) | ✅ |
| 2 | Yangi lidning standart statusi **"2. Yangi guruhga kutyapti"** (avval 1 edi) | Lidlar → Yangi lid / `pages-crm.js` (`A.leadForm`) | ✅ |
| 3 | Lid formasida "Sharif" o'rniga **"Izoh"** (ixtiyoriy, lidning birinchi izohi bo'lib saqlanadi). Dublikat tekshiruvi endi: shu filialda ism + familiya bir xil **va** telefonlardan biri mos. Sharif keyin "Talaba ma'lumotlarini to'ldirish" formasida kiritiladi | Lidlar → Yangi lid / `pages-crm.js` (`A.leadForm`) | ✅ |
| 4 | Lid manbalariga **Faol / Nofaol** holati. Nofaol manba (masalan "Qayta murojaat") yangi lid formasida chiqmaydi; eski lidlarda va statistikada qoladi | Sozlamalar → Lid manbalari, Lidlar → Yangi lid / `pages-admin.js` (`CRUD.sources`), `pages-crm.js` | ✅ |
| 5 | Dars kunlariga **Faol / Nofaol** va **o'chirish** (🗑). Ishlatilgan (guruh, lid, dars soni, davomat) yozuvni o'chirib bo'lmaydi — faqat nofaol. O'chirish tugmasi umumiy: boshqa ma'lumotnomaga `usage` qo'shilsa unda ham chiqadi | Sozlamalar → Dars kunlari / `pages-admin.js` (`CRUD.patterns`, `crud-del`), `pages-crm.js`, `pages-edu.js` | ✅ |
| 6 | Dars vaqtlariga ham **Faol / Nofaol** va **o'chirish** (dars kunlari kabi). Guruh yoki lidda ishlatilgan vaqtni o'chirib bo'lmaydi — faqat nofaol | Sozlamalar → Dars vaqtlari / `pages-admin.js` (`CRUD.times`), `pages-crm.js`, `pages-edu.js` | ✅ |
| 7 | Ota-onalar bilan aloqa: chapda **kurs → guruh daraxti** ("Barchasi" bilan, sonlari bilan), bosilganda jadval filtrlanadi. Aloqa ustunida 2-telefon ham chiqadi. Daraxt umumiy komponent (`A.treeNav` / `A.treeFilter`), boshqa ro'yxatlarga ham qo'shsa bo'ladi. Seed v5: har guruhdan qo'ng'iroqlar | Ota-onalar bilan aloqa / `pages-edu.js`, `app.js`, `style.css`, `seed.js` | ✅ |
| 8 | Ota-onalar bilan aloqa: izohni **tahrirlash** (✎) va **o'chirish** (🗑). Tahrirlagan kishi va vaqti izoh ostida kichik yozuv bilan; tahrirlash formasida "Qo'shgan / Oxirgi tahrir" ko'rsatiladi. Hammasi audit'ga yoziladi | Ota-onalar bilan aloqa / `pages-edu.js` | ✅ |
| 9 | Rollar va ruxsatlar jadvali: **rol nomlari (sarlavha) va bo'limlar (1-ustun) qotib turadi**, faqat kataklar o'zi aylanadi (ekran balandligiga sig'adi). Katak bosilganda jadval joyidan siljimaydi; katak ustida "rol · bo'lim · amal" yozuvi chiqadi | Sozlamalar → Rollar va ruxsatlar / `pages-admin.js` (`rolesView`, `A.act.perm`), `style.css` (`.perm-wrap`) | ✅ |
| 10 | Oyliklar → Hisoblangan KPI: chapda AppSheet'dagidek **daraxt: Barchasi → yil → oy → xodim → guruh**, har tugunda **KPI summasi**. Standart holatda oxirgi oy ochiq. Bosilgan tugun bo'yicha jadval filtrlanadi (bir necha oy bo'lsa "Oy" ustuni chiqadi); guruh tanlansa har bir davomat qatori (sana, shartnoma, status, KPI) ham chiqadi. Oy tanlash ro'yxati bu tabda olib tashlandi. Daraxt komponenti endi darajalari sozlanadigan (`A.treeNav(key, rows, { levels, value, def })`) | Oyliklar → Hisoblangan KPI / `pages-fin.js` (`kpiView`, `KPI_LEVELS`), `app.js`, `style.css` | ✅ |
| 11 | Oyliklar → Xodim balansi: qatorni bosganda **batafsil oyna**: oy tanlash tugmalari; 4 ta karta (avvalgi oylardan qoldiq — haqdor/qarzdor, shu oy hisoblangan, shu oy berilgan, yakuniy balans); hisoblangan oylik tarkibi (belgilangan, bonus, qo'lda KPI, ustoz KPI, yordamchi KPI, − jarima); shu oy berilgan pullar ro'yxati (sana, turi, summa, g'azna, kim berdi, izoh); yakuniy balans hisobi; oylar bo'yicha tarix. Musbat balans = xodim haqdor, manfiy = xodim qarzdor | Oyliklar → Xodim balansi / `pages-fin.js` (`balanceView`, `bal-open`), `style.css` | ✅ |

### 20.7 GitHub

- Repo: https://github.com/Ilhomjon1502/codialERP1 (ochiq — GitHub Pages bepul ishlashi uchun). Ichida haqiqiy talaba ma'lumoti yo'q, faqat soxta demo.
- Sayt `main` branch ildizidan chiqadi: ildizdagi `index.html` → `prototype/` ga yo'naltiradi.
- `AppSheetsDoc.pdf` va `.claude/` yuklanmaydi (`.gitignore`).
- Push qilingandan keyin sayt 1–2 daqiqada yangilanadi.

---

## 21. Haqiqiy tizim (`backend/` + `frontend/`) — dasturchi uchun qo'llanma

### 21.1 Umumiy sxema

```
Brauzer ──HTTPS──► Nginx (serverda) ──┬── /            → frontend/ fayllari (statik)
                                      └── /api /admin /static → Docker: Gunicorn (Django) → PostgreSQL
```

- Front-end va API **bitta domenda**: sessiya cookie + CSRF, CORS yo'q. Lokalda Django `DEBUG` rejimida `frontend/` ni o'zi beradi (`config/urls.py`).
- **Hisob-kitob va tekshiruv faqat serverda.** Front-end faqat ko'rsatadi va tugmalarni yashiradi; ruxsat, filial doirasi va muddatlarni server baribir tekshiradi.
- Kirgandan keyin front-end bir marta `GET /api/v1/bootstrap/` oladi: joriy xodim, rollar (ruxsatlar), tahrirlash muddatlari va barcha **kichik** ma'lumotnomalar. Katta jadvallar (lid, shartnoma, davomat, to'lov…) bootstrap'ga **kirmaydi** — ular sahifa ochilganda filtr va sahifalash bilan yuklanadi (AppSheet sekinligining sababi aynan hammasini bir yo'la yuklash edi).

### 21.2 Backend kelishuvlari

| Mavzu | Qoida |
|---|---|
| ID | Barcha modellar **UUID** (`BaseModel.id`), JSON'da satr |
| Maydon nomlari | Model — CLAUDE.md 7-bo'limdagi nomlar (`max_amount`, `start_time`…). **Serializer — prototipdagi nomlar** (`max`, `start`, `pattern`…, `source=` orqali), shunda front-end kodi deyarli o'zgarmaydi |
| Pul | `DecimalField(14, 0)`; JSON'da son (`COERCE_DECIMAL_TO_STRING=False`) |
| Oy | Model — oyning 1-kuni (`DateField`); API — `"YYYY-MM"` (`YearMonthField`) |
| Vaqt | API — `"HH:MM"` |
| Rol | API'da kod satri (`"USTOZ"`); `apps/core/roles.py` — rollar, bo'limlar (`SECTIONS`), boshlang'ich matritsa, `edit_days()` |
| Ruxsat | Har bir ViewSet `section = "..."` e'lon qiladi; `SectionPermission`: GET→v, POST→a, PATCH→e, DELETE→d; maxsus amallar `action_ops = {"approve": "p"}` |
| Filial doirasi | `branch_field = "branch"` → `scope_branch()`; serializer'da `BranchScopedSerializerMixin` (filial doirada bo'lsin, yaratilgandan keyin o'zgarmasin) |
| Muddat | `check_edit_window(user, section, record.date)` — 6.4 jadvali, sababi bilan 403 |
| Audit | `AuditedModelViewSet` yaratish/o'zgartirish/o'chirishni o'zi yozadi (`apps/core/audit.py`). Servisda qo'lda o'zgartirsangiz — `audit.snapshot()` + `audit.log_update()` |
| O'chirish | Faqat soft delete: `services.soft_delete()` — ishlatilgan yozuv (reverse relation'larda o'chirilmagan yozuv bor) 409 bilan rad etiladi va «ishlatilgan (N ta …)» deydi |
| Xatolar | O'zbekcha: `{"detail": "..."}` yoki `{"maydon": ["..."]}`; 401 — `{"code": "not_authenticated"}`, 409 — `Conflict` |
| Ro'yxat | Ma'lumotnomalar sahifalashsiz (`AuditedModelViewSet.pagination_class = None`); katta ro'yxatlarda `pagination_class = Pagination` (50 tadan, `{count, page, pages, results}`) |
| Biznes mantiq | `apps/<app>/services.py`, `transaction.atomic`; view faqat chaqiradi |
| Seed | `python manage.py seed_demo --password ...` — idempotent (`legacy_id="demo:..."`, nomi bo'yicha ham topadi). Rollar va davomat statuslari — data migratsiyalar (`accounts/0003`, `references/0002`) |

### 21.3 Front-end kelishuvlari (`frontend/assets/js/`)

| Fayl | Vazifa |
|---|---|
| `api.js` | `A.http.get/post/patch/del` (CSRF, xatolar `A.ApiError`), `A.ENDPOINT` (to'plam → API manzili), `A.create/update/remove` (serverga yozib, keshni yangilaydi), `A.boot()` |
| `core.js` | Kesh `A.S` (prototipdagi to'plam nomlari), `A.can()` — server ruxsatlari, `A.editDays()` — server jadvali |
| `app.js` | Marshrut, layout, kirish va parol o'rnatish sahifalari, **`A.CONNECTED`** — serverga ulangan bo'limlar, `A.MILESTONE` |
| `forms.js` | `onSubmit` async; server xatosi tegishli maydon ostida chiqadi |
| `pages-admin.js` | Sozlamalar, Audit tarixi, Bosh sahifa (M1) — **namuna sifatida o'qing** |
| `pages-crm.js` | Lidlar (M2), Shartnomalar, Qarzdorlar (M3) — API'ga ulangan. Ichidagi eski `A.page('dashboard')` ishlatilmaydi (`pages-admin.js` dagisi uni almashtiradi) |
| `pages-edu.js` | Guruhlar, Guruhlar tahlili, Davomat (M3), Baholash (ustozni), Ota-onalar bilan aloqa, Shartnoma yuklash (M6) — hammasi API'ga ulangan |
| `pages-fin.js` | To'lovlar, Tasdiqlashlar, G'aznalar, O'tkazmalar, Ayirboshlash, Xarajatlar, Kreditorlar (M4), Oyliklar (M5), Foyda va Statistika (M7) — hammasi API'ga ulangan |

Sahifa serverdan ma'lumot olishi kerak bo'lsa: `A.page('route', { section, async load(p, q) {...}, render(p, q) {...} })` — `load` har chizishdan oldin (filtr o'zgarganda ham) chaqiriladi. Namuna: `A.page('audit')`.

### 21.4 Yangi bo'limni ulash tartibi (M2 dan boshlab har safar)

1. **Model** `apps/<app>/models.py`, `BaseModel` dan; `verbose_name` o'zbekcha (o'chirish xabarida ishlatiladi); kerakli indekslar; `makemigrations`.
2. **Servis** `services.py`: hisob-kitob, tekshiruv, `transaction.atomic`, audit.
3. **Serializer**: maydon nomlari prototipdagidek; xato matnlari CLAUDE.md 7-bo'limdagidek.
4. **ViewSet**: `AuditedModelViewSet`, `section`, `branch_field`, kerak bo'lsa `pagination_class = Pagination`, `action_ops`; `config/api.py` ga `router.register`.
5. **Testlar** `backend/tests/`: servis qoidalari, ruxsatlar (rollar bo'yicha), filial doirasi, muddatlar, `django_assert_max_num_queries`.
6. **Front-end**: `A.ENDPOINT` ga qo'shing; sahifaga `load()` yozing va `A.insert/patch/softDelete` (prototip) o'rniga `A.create/update/remove` yoki `A.http`; hisob-kitobni JS'dan olib tashlab, server qiymatini ko'rsating; bo'limni `A.CONNECTED` ga qo'shing.
7. `frontend/index.html` dagi `?v=` ni almashtiring; `seed_demo` ga sinov ma'lumoti; `docs/user_guide/` ga qisqa qo'llanma; README va shu CLAUDE.md (0, 17-bo'limlar) holatini yangilang.
8. Test serverga joylash (21.5) va buyurtmachiga qisqa hisobot.

### 21.5 Serverga yangilash

```bash
ssh -i ~/.ssh/codial_hetzner root@77.42.9.23
cd /srv/codial-test && git pull
cd deploy && docker compose --env-file .env up -d --build      # migratsiyalar o'zi qo'llanadi
docker compose --env-file .env logs web --tail 50              # xatolarni tekshirish
```

Front-end fayllari `git pull` bilan darhol yangilanadi (Nginx papkadan beradi).

### 21.6 Tuzoqlar (bilib qo'ying)

- `frontend/index.html` dagi `?v=` almashtirilmasa, brauzer eski JS'ni ko'rsatadi.
- Bitta JS faylda sintaksis xatosi bo'lsa, o'sha fayldagi **barcha** sahifalar «Sahifa topilmadi» bo'ladi. Push'dan oldin `pytest` (ichida `test_frontend_syntax.py`) yashil bo'lsin.
- Python skript bilan JS'ga matn qo'shganda qo'shtirnoqqa ehtiyot bo'ling: `'...g'azna...'` — xato; o'zbekcha apostrofli matn uchun `"..."` yoki `` `...` `` ishlating.
- Git Bash'da katta heredoc (`<<'EOF'`) ba'zan buziladi — uzun tahrir skriptlarini faylga yozib ishga tushiring.
- Login so'rovi ham CSRF talab qiladi: front-end avval `GET /api/v1/auth/csrf/` oladi.
- **Admin rolining ruxsatlari o'zgarmaydi** (qulflanib qolmaslik uchun); matritsani faqat Admin va Bosh menejer o'zgartiradi.
- Prod sozlamada HTTPS majburiy (xavfsiz cookie) — SSL'siz HTTP orqali kirib bo'lmaydi. Domen bo'lmasa `*.sslip.io` ishlatiladi.
- Ubuntu 24.04: SSH socket orqali ishlaydi, `systemctl reload ssh` xato beradi — `sshd_config.d` o'zgarishi keyingi ulanishda kuchga kiradi.
- Server **Arm64**: Docker obrazlar `linux/arm64` bo'lishi kerak (python, postgres rasmiy obrazlari mos).
- Nginx'da ichki `location` da `add_header` bo'lsa, server darajasidagi xavfsizlik sarlavhalari bekor bo'ladi — ularni o'sha `location` ichida takrorlang.
- Lokal kompyuterda Docker va PostgreSQL yo'q: lokal SQLite, serverda PostgreSQL. Faqat ORM ishlating; partial unique constraint'lar ikkalasida ishlaydi.
- Repo **ochiq**: sirlar, parollar, haqiqiy talaba ma'lumotlari git'ga tushmasin (`deploy/.env`, `deploy/*.local.md`, `import_data/` — `.gitignore` da).
- Telegram bot tokeni ham shunday: faqat `bash /srv/codial-test/deploy/set-telegram.sh` orqali, buyurtmachining o'zi kiritadi. Gemini kaliti — `bash /srv/codial-test/deploy/set-ai.sh`.
- Gmail App password va boshqa sirlarni **hech qachon chatga yozdirmang va o'zingiz kiritmang**: buyurtmachi serverda `bash /srv/codial-test/deploy/set-smtp.sh` ni o'zi ishga tushirib kiritadi (terminalda parol ekrandan o'chiriladi). Sir chatga yoki terminal tarixiga tushib qolsa — darhol bekor qildiring va yangisini yaratdiring.
- Serverdagi checkout'ga fayllarni `scp` bilan qo'lda qo'ymang — keyingi `git pull` to'xtaydi. O'zgarish faqat git orqali.

