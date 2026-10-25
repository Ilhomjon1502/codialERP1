from common import lesson, outro


@lesson("01", "kirish", "Tizimga kirish va tanishuv", login=False, start=lambda L: L.credentials()["set_password"])
async def l01(L):
    cred = L.credentials()
    await L.card("1-dars", "Tizimga kirish va tanishuv", "Codial ERP · Administrator+Hisobchi uchun yoʻriqnoma",
                 ["Parol oʻrnatish", "Tizimga kirish", "Menyu va ekran tuzilishi", "Profil va chiqish",
                  "Telegram botni ulash", "Bot qanday xabarlar yuboradi"],
                 text="Assalomu alaykum! Codial ERP tizimi bo'yicha yo'riqnomaga xush kelibsiz. Bu birinchi darsda tizimga kirishni va ekran tuzilishini o'rganamiz.")
    await L.uncard()
    await L.keynote("erp.codialinfo.uz", "Kompyuterda ham, telefonda ham brauzer orqali ochiladi",
                    text="Tizim brauzerda ishlaydi. Manzili: e-er-pe nuqta codialinfo nuqta uz. Uni kompyuterda ham, telefonda ham ochish mumkin.")
    await L.say("Sizni tizimga Bosh menejer qo'shadi. Shundan so'ng pochtangizga «parol o'rnatish» xati keladi.")
    await L.say("Xatdagi havolani bossangiz, mana shu sahifa ochiladi. Bu yerda o'zingiz uchun parol o'ylab topasiz.",
                L.show(".login-card", "Parol oʻrnatish sahifasi", side="right"))
    await L.say("Yangi parolni yozamiz. Kamida to'rtta belgi bo'lishi kerak.",
                L.type("#sp-p1", cred["password"], "Yangi parol", delay=55))
    await L.say("Xato bo'lmasligi uchun parolni yana bir marta takrorlaymiz.",
                L.type("#sp-p2", cred["password"], "Takrorlash", delay=55))
    await L.say("«Parolni saqlash» tugmasini bosamiz.", L.click("#sp-btn", "Parolni saqlash", side="right"))
    await L.wait_for("#lg-email")
    await L.say("Parol saqlandi va kirish sahifasi ochildi. Endi tizimga kiramiz.")
    await L.say("Birinchi qatorga pochtangizni yozasiz — xat kelgan pochta.",
                L.type("#lg-email", cred["email"], "Pochta", delay=45))
    await L.say("Ikkinchi qatorga hozirgina o'rnatgan parolingizni yozasiz.",
                L.type("#lg-pass", cred["password"], "Parol", delay=55))
    await L.say("Agar parolni unutsangiz, mana shu «Parolni unutdingizmi?» havolasini bosasiz — pochtangizga yangi havola keladi.",
                L.show("#lg-forgot", "Parolni unutsangiz", side="right"))
    await L.say("«Kirish» tugmasini bosamiz.", L.click("#lg-btn", "Kirish", side="right"))
    await L.wait_for("#view .page-head")
    await L.say("Tizimga kirdik! Endi ekran qanday tuzilganini ko'rib chiqamiz.")
    await L.say("Chap tomonda — asosiy menyu. Unda sizga ruxsat berilgan barcha bo'limlar bor.",
                L.show("#nav", "Asosiy menyu", side="right", hold=1))
    await L.say("Menyu tepasida filial nomi: biz Emirat filialida ishlaymiz.",
                L.show(".branch-pill", "Filial", side="right"))
    await L.say("Yuqori qatorda: ochiq bo'lim nomi, bugungi sana va hafta kuni.",
                L.show("#top-title", "Boʻlim nomi", side="below"),
                L.show(".date-pill", "Bugungi sana", side="below"))
    await L.say("Qo'ng'iroqcha belgisi — tasdiq kutayotgan ishlar. Ustida son chiqsa, kimdir tasdiqlashi kerak bo'lgan to'lov yoki o'tkazma bor.",
                L.show("#top-bell", "Tasdiqlashlar", side="below"))
    await L.say("O'ng burchakda — sizning ismingiz va lavozimingiz.",
                L.show("#user-chip", "Siz", side="below"))
    await L.say("Uch chiziqli tugma menyuni yig'adi: faqat belgilar qoladi va ish joyi kengayadi.",
                L.click('.topbar [data-act="drawer"]', "Menyuni yigʻish", side="right", wait=1.2))
    await L.say("Yana bossangiz, menyu qaytib ochiladi.",
                L.click('.topbar [data-act="drawer"]', "Menyuni ochish", side="right", wait=1.0))
    await L.clear()
    await L.say("Endi menyu bo'limlari bilan tanishamiz. Har biri alohida darsda batafsil o'rgatiladi.")
    pairs = [
        ("«Bosh sahifa» — kunning qisqa manzarasi va dars jadvali. «Topshiriqlar» — xodimlar bir-biriga beradigan ishlar.",
         ("dashboard", "Bosh sahifa"), ("staffTasks", "Topshiriqlar")),
        ("«Lidlar» — murojaat qilganlar. «Shartnomalar» — o'qiyotgan talabalar.",
         ("leads", "Lidlar"), ("contracts", "Shartnomalar")),
        ("«To'lovlar» — pul qabul qilish. «Qarzdorlar» — kim qancha to'lashi kerak.",
         ("payments", "Toʻlovlar"), ("debtors", "Qarzdorlar")),
        ("«Davomatlar» — darsga kim kelgani. «Xarajatlar» — markaz sarflagan pullar.",
         ("attendance", "Davomatlar"), ("expenses", "Xarajatlar")),
        ("«Shartnoma yuklash» — Excel faylga chiqarish. «Guruhlar» — barcha guruhlar va ularning jurnali.",
         ("export", "Shartnoma yuklash"), ("groups", "Guruhlar")),
        ("«Tasdiqlashlar» — tasdiq kutayotgan ishlar. «Oyliklar» bo'limini rahbariyat yuritadi, siz u bilan ishlamaysiz.",
         ("approvals", "Tasdiqlashlar"), ("salaries", "Oyliklar")),
        ("«Ichki pul oqimi» — g'aznalar orasida pul o'tkazish. «G'aznalar» — kassadagi qoldiq.",
         ("transfers", "Ichki pul oqimi"), ("accounts", "Gʻaznalar")),
        ("«Qo'ng'iroqlar va SMS» — qabul telefonidagi qo'ng'iroqlar. «Ota-onalar bilan aloqa» — ota-onalar bilan suhbatlar izohi.",
         ("calls", "Qoʻngʻiroqlar va SMS"), ("parentCalls", "Ota-onalar bilan aloqa")),
    ]
    for text, (s1, l1), (s2, l2) in pairs:
        await L.say(text, L.show(f'#nav a[data-nav="{s1}"]', l1, side="right", hold=0.9),
                    L.show(f'#nav a[data-nav="{s2}"]', l2, side="right"), pause=0.25)
    await L.say("Eng pastda — «Sozlamalar»: kurslar, narxlar, xonalar va boshqa ma'lumotnomalar.",
                L.show('#nav a[data-nav="settings"]', "Sozlamalar", side="right"))
    await L.clear()
    await L.say("Endi profilingizni ko'ramiz. O'ng yuqoridagi ismingizni bosamiz.",
                L.click("#user-chip", "Profil", side="below"))
    await L.wait_for(".overlay .modal")
    await L.say("Bu yerda lavozimingiz, pochtangiz va filialingiz yozilgan.",
                L.show(".overlay .modal .kv", "Maʼlumotlaringiz", side="right"))
    await L.say("Pastda ikkita tugma bor: «Chiqish» — tizimdan chiqish, «Telegram» — botni ulash.",
                L.show(".overlay [data-logout]", "Chiqish", side="above", hold=0.8),
                L.show(".overlay [data-telegram]", "Telegram", side="above"))
    await L.say("Telegram botni ulash juda muhim: tizim eslatmalarni aynan bot orqali yuboradi. «Telegram» tugmasini bosamiz.",
                L.click(".overlay [data-telegram]", "Telegram", side="above"))
    await L.wait_for(".overlay .tg-prefs")
    await L.say("Ulash ikki qadam. Birinchi: mana shu havolani bosing — Telegram'da bizning bot ochiladi, «Start»ni bosasiz.",
                L.show('.overlay .modal-body a[href*="t.me"]', "Botga havola", side="below"))
    await L.say("Havola ochilmasa, botga mana shu sakkiz belgili kodni yuborasiz. Kod bir martalik.",
                L.show(".overlay .modal-body b[style]", "Bogʻlash kodi", side="right"))
    await L.say("Pastda — qaysi xabarlarni olishingiz. Belgilanganlari keladi; ish uchun keraklilari oldindan belgilangan. Xohlasangiz, qo'shimcha xabarlarni ham yoqasiz.",
                L.show(".overlay .tg-prefs", "Qaysi xabarlar keladi", side="right"))
    await L.say("Tanlovni o'zgartirsangiz, «Saqlash» tugmasini bosasiz.",
                L.click(".overlay [data-save]", "Saqlash", side="above"))
    await L.card("Telegram bot", "Bot sizga nimalarni yuboradi", "Administrator+Hisobchi uchun eng muhimlari",
                 ["08:30 — bugungi ish rejasi", "Lid bilan qayta bogʻlanish vaqti",
                  "Darsdan oldin — shu guruhdagi qarzdorlar", "Yangi lid va lid holati oʻzgarishi",
                  "Sizga berilgan topshiriqlar", "Davomat olinmagan darslar"],
                 text="Bot ertalab soat sakkiz yarimda bugungi ish rejasini yuboradi: kimdan to'lov olish, kim sinov darsiga keladi, kimga qo'ng'iroq qilish kerak. Lid bilan qayta bog'lanish vaqti kelganda va dars oldidan qarzdorlar haqida ham eslatadi.")
    await L.say("Botdagi xabarda tugmalar bo'ladi: masalan «Qo'ng'iroq qilindi» yoki «Bajarildi». Ularni bossangiz, tizimda ham belgilanadi.")
    await L.uncard()
    await L.say("Tizimdan chiqish uchun ismingizni bosib, «Chiqish» tugmasini bosasiz. Begona kompyuterda ishlagan bo'lsangiz, albatta chiqing.",
                L.click("#user-chip", "Profil", side="below"),
                L.point(".overlay [data-logout]", "Chiqish", side="above"))
    await L.close_modal()
    await outro(L, "Bosh sahifa va dars jadvali")
