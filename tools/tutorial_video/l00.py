from common import SAVE, f, lesson


@lesson("00", "namuna", "Namuna: yangi lid qo'shish")
async def sample(L):
    await L.card("Codial ERP · namuna", "Yangi lid qoʻshish", "Administrator+Hisobchi uchun yoʻriqnoma",
                 text="Assalomu alaykum! Bu qisqa namunada tizimga yangi lid qanday qo'shilishini ko'rib chiqamiz.")
    await L.uncard()
    await L.say("Lid — markazimizga qiziqib murojaat qilgan, lekin hali o'qishni boshlamagan odam.")
    await L.say("Yangi lid qo'shish uchun chap menyudan «Lidlar» bo'limini tanlaymiz.",
                L.nav("leads", "Lidlar menyusi"))
    await L.say("Bu yerda lidlar voronkasi: har bir ustun — lidning bosqichi, ichida shu bosqichdagi odamlar.",
                L.show(".kanban", "Voronka", side="above", pad=4, hold=1.5))
    await L.clear()
    await L.say("Yuqori o'ng burchakdagi «Yangi lid» tugmasini bosamiz.",
                L.click('[data-act="lead-new"]', "Yangi lid", side="below"))
    await L.wait_for(f("first_name"))
    await L.say("Forma ochildi. «Yangi talaba» tanlangan — demak, bu odam bazada hali yo'q.",
                L.show('[data-f="mode"]', "Yangi talaba", side="below"))
    await L.say("Avval talabaning ismini yozamiz.", L.type(f("first_name"), "Sardor", "Ism"))
    await L.say("Keyin familiyasini.", L.type(f("last_name"), "Aliyev", "Familiya"))
    await L.say("Endi ikkita telefon raqami: to'qqiz raqam, oldidagi plyus to'qqiz yuz to'qson sakkizsiz yoziladi.",
                L.type(f("phone1"), "901112233", "1-telefon"),
                L.type(f("phone2"), "911112233", "2-telefon"))
    await L.say("Ikkala raqam ham majburiy va ular bir xil bo'lmasligi kerak.")
    await L.say("Izoh maydoniga suhbatdan muhim gapni yozib qo'yamiz.",
                L.type(f("comment", "textarea"), "Kechki guruhni so'radi", "Izoh", side="below"))
    await L.say("Jinsini tanlaymiz.", L.seg("gender", "Erkak", "Jins"))
    await L.say("Yosh guruhi va ijtimoiy holatini belgilaymiz.",
                L.choose(f("age_group", "select"), "16-18", label="Yosh guruhi"),
                L.choose(f("social", "select"), "Maktab o'quvchisi", label="Ijtimoiy holat"))
    await L.say("Noutbuki bor-yo'qligini so'raymiz.", L.seg("laptop", "Bor", "Noutbuk"))
    await L.say("Endi eng muhimi: lid qayerdan kelgani — manbasi, va qaysi kursga qiziqyapti.",
                L.choose(f("source", "select"), text="Instagramdan", label="Manba"),
                L.choose(f("course", "select"), text="Backend", label="Kurs"))
    await L.say("Status — «2. Yangi guruhga kutyapti». U avtomatik tanlangan, o'zgartirmaymiz.",
                L.show('[data-f="status"]', "Status", side="above"))
    await L.say("Hammasi to'g'ri bo'lsa, «Saqlash» tugmasini bosamiz.", L.click(SAVE, "Saqlash", side="above"))
    await L.wait(0.8)
    await L.say("Tayyor! Yangi lid voronkaning ikkinchi ustunida paydo bo'ldi.",
                L.show('.kcard:has-text("Sardor")', "Yangi lid", side="right"))
    await L.clear()
    await L.card("Codial ERP", "Namuna tugadi", "Ovoz, belgilash va yozuvlar shu uslubda bo'ladi",
                 text="Namuna shu yerda tugadi. Rahmat!", hold=0.6)
