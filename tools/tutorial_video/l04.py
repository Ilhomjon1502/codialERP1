from common import SAVE, f, lesson, outro

STATUSES = [
    ("1", "«1. Qayta bog'lanishga» — keyinroq qo'ng'iroq qilishimiz kerak bo'lganlar."),
    ("2", "«2. Yangi guruhga kutyapti» — o'qimoqchi, lekin mos guruh ochilishini kutyapti."),
    ("3", "«3. Sinov darsga yozildi» — sinov darsiga kelish kuni belgilangan."),
    ("4", "«4. Sinov darsga qatnashdi» — sinov darsida bo'ldi, qaror kutilyapti."),
    ("5", "«5. O'qishni boshladi» — endi u bilan shartnoma tuziladi."),
    ("6", "«6» va «7» — ma'qul kelmadi. Yettinchisi — sifatsiz murojaat, masalan noto'g'ri raqam."),
    ("8", "«8. Keyinroq o'qiydi» — hozir emas, keyinroq qaytadan bog'lanamiz."),
]


@lesson("04", "lidlar_1", "Lidlar: voronka va yangi lid")
async def l04(L):
    await L.card("4-dars", "Lidlar: voronka va yangi lid", "Murojaat qilganlar bilan ishlashning birinchi qismi",
                 ["Lid nima va voronka", "8 ta bosqich (status)", "Qidirish va filtrlar", "Yangi lid qoʻshish",
                  "Roʻyxat va statistika", "Toʻlov qilganlar"],
                 text="To'rtinchi darsda lidlar bilan tanishamiz. Lid — markazimizga qiziqib murojaat qilgan, lekin hali o'qishni boshlamagan odam.")
    await L.uncard()
    await L.say("Masalan, kimdir qo'ng'iroq qilib Backend kursini so'radi — biz uni darhol lid sifatida yozib qo'yamiz.")
    await L.nav("leads", "Lidlar")
    await L.say("Lidlar sahifasi ochildi. Bu yerda to'rtta tab bor: Voronka, Ro'yxat, Statistika va To'lov qilganlar.",
                L.show("#view .tabs", "Toʻrtta tab", side="below"))
    await L.say("Voronka — eng ko'p ishlatiladigan ko'rinish. Har bir ustun — lidning bosqichi, ichida — shu bosqichdagi odamlar.",
                L.show(".kanban", "Voronka", side="above", pad=4))
    for k, text in STATUSES:
        sel = f'.kanban .kcol:nth-child({k}) .kcol-h'
        await L.say(text, L.show(sel, f"{k}-bosqich", side="below"), pause=0.2)
    await L.clear()
    await L.say("Ustun sarlavhasidagi son — shu bosqichdagi lidlar soni.")
    await L.say("Kartochkada: talabaning ismi, kursi va qayerdan kelgani. Sinov dars sanasi va qayta bog'lanish vaqti ham shu yerda.",
                L.show(".kanban .kcard", "Lid kartochkasi", side="right"))
    await L.say("Soat belgisi qizil bo'lsa — qayta bog'lanish vaqti o'tib ketgan, darhol qo'ng'iroq qilish kerak.")
    await L.say("Yuqoridagi foizlar — voronka natijasi: lidlarning qanchasi sinov darsiga yozildi, qatnashdi, o'qishni boshladi va shartnoma tuzdi.",
                L.show("#view .conv", "Natija foizlari", side="below"))
    await L.clear()
    await L.say("Lidni topish uchun qidiruvga ismi yoki telefonini yozasiz.",
                L.type('[data-filter="leads:search"]', "Sulaymon", "Qidiruv", delay=110))
    await L.wait(1.0)
    await L.say("Faqat mos lidlar qoldi. Qidiruvni tozalaymiz.", L.type('[data-filter="leads:search"]', "", "Tozalash"))
    await L.wait(0.8)
    await L.say("Kurs yoki manba bo'yicha ham filtrlash mumkin. Masalan, faqat Backend kursi lidlari.",
                L.choose('select[data-filter="leads:course"]', text="Backend", label="Kurs filtri"))
    await L.wait(0.8)
    await L.say("Filtrni olib tashlash uchun «Barcha kurslar»ni tanlaymiz.",
                L.choose('select[data-filter="leads:course"]', "", label="Barcha kurslar"))
    await L.clear()
    await L.say("Endi yangi lid qo'shamiz. Tepadagi «Yangi lid» tugmasini bosamiz.",
                L.click('[data-act="lead-new"]', "Yangi lid", side="below"))
    await L.wait_for(f("first_name"))
    await L.say("«Murojaatchi» qatorida ikki variant: «Yangi talaba» — bazada yo'q odam, «Bazadagi talaba» — oldin bizda bo'lgan odam.",
                L.show('[data-f="mode"]', "Kim murojaat qildi", side="below"))
    await L.say("Avval bazada bor-yo'qligini tekshirish uchun qidiruvdan foydalaning. Bu yangi odam — ismini yozamiz.",
                L.type(f("first_name"), "Jasur", "Ism"))
    await L.say("Familiyasi.", L.type(f("last_name"), "Karimov", "Familiya"))
    await L.say("Ikkita telefon raqami majburiy. To'qqiz raqam yoziladi, plyus to'qqiz yuz to'qson sakkiz yozilmaydi.",
                L.type(f("phone1"), "907776655", "1-telefon"), L.type(f("phone2"), "937776655", "2-telefon"))
    await L.say("Agar shu ism va telefon bilan talaba bazada bo'lsa, tizim saqlashda ogohlantiradi — bitta odam ikki marta yozilmaydi.")
    await L.say("Izohga suhbatdagi muhim gapni yozamiz. U lidning birinchi izohi bo'lib saqlanadi.",
                L.type(f("comment", "textarea"), "Narxni so'radi, onasi bilan maslahatlashadi", "Izoh", delay=40, side="below"))
    await L.say("Jinsi.", L.seg("gender", "Erkak", "Jins"))
    await L.say("Yosh guruhi va ijtimoiy holati — bu statistika uchun kerak.",
                L.choose(f("age_group", "select"), "19-21", label="Yosh guruhi"),
                L.choose(f("social", "select"), "Oliygoh talabasi", label="Ijtimoiy holat"))
    await L.say("Noutbuki bormi? Dasturlash kurslarida bu muhim.", L.seg("laptop", "Sotib oladi", "Noutbuk"))
    await L.say("Teglar ixtiyoriy: masalan, chegirma so'ragan bo'lsa yoki kechki vaqtni xohlasa.",
                L.click("""[data-f="tags"] button[data-val="Chegirma so'radi"]""", "Teg", side="above"))
    await L.say("Manba — lid bizni qayerdan topgani. Bu reklama samarasini o'lchash uchun juda muhim, har doim to'g'ri tanlang.",
                L.choose(f("source", "select"), text="Instagramdan", label="Manba"))
    await L.say("Qaysi kursga qiziqyapti.", L.choose(f("course", "select"), text="Backend", label="Kurs"))
    await L.say("Hafta kunlari va ma'qul vaqt — qaysi kunlari va soat nechada o'qiy olishi. Bu guruh ochishda yordam beradi.",
                L.click(f("pattern", "button:nth-child(1)"), "Hafta kunlari", side="above"),
                L.choose(f("new_start", "select"), "15:00", label="Boshlanish"))
    await L.say("Tugash vaqti avtomatik ikki soat keyin qo'yiladi.", L.show('[data-f="new_end"]', "Tugash", side="above"))
    await L.say("Status — «Yangi guruhga kutyapti». Agar «1» yoki «8» tanlasangiz, qayta bog'lanish sana va vaqtini kiritish majburiy bo'ladi.",
                L.show('[data-f="status"]', "Status", side="above"))
    await L.say("«Saqlash» tugmasini bosamiz.", L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.0)
    await L.say("Lid qo'shildi va voronkaning ikkinchi ustunida turibdi. Filial administratorlariga Telegram orqali «yangi lid» xabari boradi.",
                L.show('.kcard:has-text("Jasur")', "Yangi lid", side="right"))
    await L.clear()
    await L.say("Endi «Ro'yxat» tabini ochamiz.", L.click('#view .tabs a[href*="tab=list"]', "Roʻyxat", side="below", wait=1.2))
    await L.say("Bu yerda barcha lidlar jadval ko'rinishida: telefon, kurs, manba, status, qayta bog'lanish vaqti, shartnoma va qo'shilgan sana.",
                L.show("#view .tbl thead", "Jadval", side="below"))
    await L.say("Ism ustiga bossangiz, lid kartochkasi ochiladi. Ro'yxat ellik tadan sahifalanadi.")
    await L.say("«Statistika» tabi — manba bo'yicha konversiya, statuslar, oylar va yosh guruhlari.",
                L.click('#view .tabs a[href*="tab=stats"]', "Statistika", side="below", wait=1.5))
    await L.say("Masalan, bu jadvalda qaysi manbadan nechta lid kelgani va ulardan nechtasi shartnoma tuzgani ko'rinadi.",
                L.show("#view .card:has-text(\"Manba bo'yicha konversiya\")", "Manba konversiyasi", side="right"))
    await L.say("«To'lov qilganlar» tabida — talabasi to'lov qilgan lidlar: birinchi to'lov sanasi va jami to'lovlar.",
                L.click('#view .tabs a[href*="tab=paid"]', "Toʻlov qilganlar", side="below", wait=1.5))
    await L.clear()
    await L.say("Keyingi darsda lid kartochkasi bilan ishlashni o'rganamiz: izoh, status, sinov darsi va shartnoma tuzish.")
    await outro(L, "Lid bilan ishlash: boshidan shartnomagacha")
