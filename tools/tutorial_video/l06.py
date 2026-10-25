from common import MODAL, SAVE, f, lesson, outro


@lesson("06", "shartnomalar", "Shartnomalar")
async def l06(L):
    await L.card("6-dars", "Shartnomalar", "Oʻqiyotgan talabalar va ularning hisob-kitobi",
                 ["Faol, rejadagi va nofaol", "Qidirish va filtrlar", "Shartnoma sahifasi",
                  "Qarz qanday hisoblanadi", "Davomat va toʻlovlar tarixi", "Shartnomani toʻxtatish"],
                 text="Oltinchi darsda shartnomalarni o'rganamiz. Shartnoma — talaba o'qishni boshlaganini bildiradi, uning qarzi va to'lovlari shu yerda yuritiladi.")
    await L.uncard()
    await L.nav("contracts", "Shartnomalar")
    await L.say("Tablar: «Faol» — hozir o'qiyotganlar, «Rejada» — hali boshlamaganlar, «Nofaol» — o'qishni tugatgan yoki to'xtatganlar.",
                L.show("#view .tabs", "Holat boʻyicha", side="below"))
    await L.say("Shartnomalar guruhlar bo'yicha ajratilgan. Har bir guruh sarlavhasida o'quvchilar soni va guruhning jami qarzi.",
                L.show("#view .group-block h3", "Guruh", side="below"))
    await L.say("Jadvalda: shartnoma nomi, turi, boshlanish sanasi, holati va balans. Qizil ism — qarzdor talaba.",
                L.show("#view .group-block .tbl thead", "Shartnomalar", side="below"))
    await L.say("Balans musbat bo'lsa — talaba qarzdor, manfiy bo'lsa — oldindan to'lagan.")
    await L.say("Qidiruvga ism, telefon yoki shartnoma raqamini yozish mumkin. Yonida — kurs va tur bo'yicha filtrlar.",
                L.show("#view .filters", "Qidiruv va filtrlar", side="below"))
    await L.say("«Excel» tugmasi joriy ro'yxatni Excel faylga yuklaydi.",
                L.show('[data-act="contracts-csv"]', "Excel", side="below"))
    await L.say("Qarzdor talabaning shartnomasini ochamiz.", L.click("#view .group-block a.t-red", "Shartnomani ochamiz", side="right"))
    await L.wait_for("#view .back")
    await L.say("Shartnoma sahifasi. Tepada: talaba nomi, holati va guruhi. O'ngda — «To'lov qilish» va «Tahrirlash» tugmalari.",
                L.show("#view .page-head", "Shartnoma", side="below"))
    await L.say("To'rtta kartochka: balans, darslar uchun hisoblangan summa, to'langan summa va chegirmalar.",
                L.show("#view .stats", "Hisob", side="below"))
    await L.say("Chapda — ma'lumotlar: telefon, vasiy, kurs va guruh, sanalar va izoh.",
                L.show("#view .grid-2 .card:first-child", "Maʼlumotlar", side="right"))
    await L.say("O'ngda — qarz qanday hisoblangani. Bu talaba yoki ota-onasi «nega qarzim bor?» deb so'rasa, tushuntirish uchun juda qulay.",
                L.show("#view .grid-2 .card:nth-child(2)", "Qarz hisobi", side="left"))
    await L.say("Qoida: bir dars narxi — kurs narxi oydagi darslar soniga bo'linadi. Talaba kelmasa ham, dars bo'lgan bo'lsa, qarz yoziladi.")
    await L.clear()
    if await L.exists("#stu-calls h4"):
        await L.say("Pastda — talaba raqamlari bilan bo'lgan qo'ng'iroqlar va SMS tarixi.",
                    L.show("#stu-calls", "Qoʻngʻiroqlar va SMS", side="above"))
    await L.say("Undan keyin ikki tab. «Davomat» — har bir dars: sana, holat, ustoz va dars narxi.",
                L.scroll("#view .tabs", wait=1.0), L.show("#view .tabs", "Davomat va toʻlovlar", side="below"))
    await L.say("Statusni shu jadvalning o'zida tanlab tuzatish mumkin — qarz darhol qayta hisoblanadi.",
                L.show("#view .att-sel", "Statusni tuzatish", side="right"))
    await L.say("«To'lovlar» tabida — talabaning barcha to'lovlari va cheklari.",
                L.click('#view .tabs a[href*="tab=pay"]', "Toʻlovlar", side="below", wait=1.2))
    await L.clear()
    await L.say("Agar talaba o'qishni to'xtatsa, shartnomani to'xtatamiz. Tepadagi «To'xtatish» tugmasini bosamiz. Yangi shartnomada bu tugma «Tahrirlash» deb yoziladi.",
                L.scroll(dy=-3000, wait=0.8), L.click('[data-act="contract-edit"], [data-act="contract-stop"]', "Tahrirlash", side="below"))
    await L.wait_for(f("end"))
    await L.say("Shartnoma boshlanganiga yetti kundan oshgani uchun kurs va guruh qulflangan — faqat to'xtatish mumkin. Yangi shartnomada ularni o'zgartirsa bo'ladi.",
                L.show('[data-f="group"]', "Guruh", side="below"))
    await L.say("To'xtatish uchun «Tugash sana»ni kiritamiz — talaba oxirgi marta kelgan kun.",
                L.fill(f("end"), L.today(), "Tugash sana", side="above"))
    await L.say("Endi to'xtatish sababi majburiy. Ro'yxatdan tanlaymiz.",
                L.choose(f("stop_reason", "select"), text="Moliyaviy", label="Sabab"))
    await L.say("Izohga batafsil yozib qo'yish foydali.",
                L.type(f("comment", "textarea"), "Oilaviy sabab, keyingi oy qaytishi mumkin", "Izoh", delay=35, side="above"))
    await L.say("«Saqlash»ni bosamiz. Tugash sanasidan keyin shartnoma «Nofaol» bo'ladi va qarz yozilmaydi.",
                L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.2)
    await L.say("Eslatma: tugash sanasini oxirgi o'ttiz kun ichidagi sana bilan qo'yish mumkin.")
    await L.clear()
    await L.say("Yangi shartnoma odatda liddan tuziladi. Lekin «Yangi shartnoma» tugmasi bilan to'g'ridan-to'g'ri ham tuzish mumkin.",
                L.click('#view .back', "Shartnomalarga qaytish", side="right", wait=1.2),
                L.click('[data-act="contract-new"]', "Yangi shartnoma", side="below"))
    await L.wait_for(f("student", "select"))
    await L.say("Formada: talaba, kurs, guruh, boshlanish sanasi va izoh. Hozir bekor qilamiz.",
                L.show(MODAL + " .form", "Forma", side="right", hold=1.0))
    await L.click(MODAL + " .modal-foot [data-close]", "Bekor qilish", side="above")
    await L.say("Oxirgi tab — «Talabalar»: barcha talabalar ro'yxati, telefonlari va shartnomalari.",
                L.click('#view .tabs a[href*="tab=students"]', "Talabalar", side="below", wait=1.2))
    await L.say("Talaba ismini bossangiz, uning ma'lumotlarini tahrirlash oynasi ochiladi: telefon, tug'ilgan sana, vasiy.",
                L.show('#view .tbl [data-act="student-edit"]', "Tahrirlash", side="right"))
    await L.clear()
    await outro(L, "To'lov qabul qilish")
