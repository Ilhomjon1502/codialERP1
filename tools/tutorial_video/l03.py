from common import SAVE, f, lesson, outro


@lesson("03", "topshiriqlar", "Topshiriqlar")
async def l03(L):
    await L.card("3-dars", "Topshiriqlar", "Xodimlar bir-biriga ish topshiradi, bot eslatib turadi",
                 ["Menga berilgan va men bergan", "Yangi topshiriq berish", "Muddat va eslatmalar",
                  "Muddatni uzaytirish", "«Bajarildi» deb belgilash", "Bajarilganlar roʻyxati"],
                 text="Uchinchi darsda topshiriqlar bo'limini o'rganamiz. Bu yerda xodimlar bir-biriga ish topshiradi, Telegram bot esa muddatni eslatib turadi.")
    await L.uncard()
    await L.nav("staffTasks", "Topshiriqlar")
    await L.say("Ikkita tab bor: «Menga berilgan» — sizga topshirilgan ishlar, «Men bergan» — siz boshqalarga bergan ishlar.",
                L.show("#view .tabs", "Ikki tab", side="below"))
    await L.say("Yonidagi tugmalar holat bo'yicha saralaydi: ochiq, bajarilgan va bekor qilingan.",
                L.show("#view .filters .seg", "Holat", side="below"))
    await L.say("Yangi topshiriq beramiz. «Yangi topshiriq» tugmasini bosamiz.",
                L.click('[data-act="task-new"]', "Yangi topshiriq", side="below"))
    await L.wait_for(f("title"))
    await L.say("Mavzu — qisqa qilib nima qilish kerakligi.",
                L.type(f("title"), "Qarzdorlarning ota-onalariga qo'ng'iroq", "Mavzu", delay=45))
    await L.say("Izohda batafsil yozamiz: qanday natija kutilyapti.",
                L.type(f("description", "textarea"), "Ro'yxat Qarzdorlar bo'limida. Har biriga izoh qoldiring.", "Izoh", delay=35))
    await L.say("Bajaruvchini tanlaymiz. Bir nechta xodimni tanlasa ham bo'ladi — har biriga alohida topshiriq ochiladi. Hozir o'zimizni tanlaymiz.",
                L.show('[data-f="assignees"]', "Bajaruvchilar", side="above", hold=0.8),
                L.click("""[data-f="assignees"] button:has-text("(o'zim)")""", "Oʻzim", side="above"))
    await L.say("Qilinish muddati — sana va soat. Odatda ertangi kun soat o'n sakkiz qo'yiladi, kerak bo'lsa o'zgartirasiz.",
                L.show('[data-f="due"]', "Muddat", side="above"))
    await L.say("Telegram orqali kimga eslatilsin: bajaruvchiga, o'zingizga yoki ikkalasiga.",
                L.show('[data-f="who"]', "Kimga eslatilsin", side="above"))
    await L.say("Eslatish qachon boshlansin — masalan, muddatdan bir soat oldin.",
                L.seg("remind_before", "60", "1 soat oldin", side="above"))
    await L.say("Qanchalik tez-tez takrorlansin. Har uch soatni tanlaymiz: ish bajarilmaguncha bot eslatib turadi.",
                L.seg("remind_every", "180", "Har 3 soat", side="above"))
    await L.say("«Saqlash» tugmasini bosamiz.", L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.0)
    await L.say("Topshiriq berildi va ro'yxatda paydo bo'ldi. Bajaruvchiga Telegram orqali xabar ketadi.",
                L.show(".task-card", "Yangi topshiriq", side="below"))
    await L.say("Kartochkada: mavzu, izoh, muddat va qancha vaqt qolgani, kim kimga bergani va eslatma tartibi.",
                L.show(".task-card .task-meta", "Tafsilotlar", side="below"))
    await L.say("Rangi muddatni bildiradi: ko'k — vaqt bor, to'q sariq — bir kundan kam qoldi, qizil — muddat o'tgan.")
    await L.say("Ulgurmasangiz, «Muddatni uzaytirish» tugmasini bosasiz.",
                L.click('.task-card [data-act="task-extend"]', "Muddatni uzaytirish", side="below"))
    await L.wait_for('[data-f="quick"]')
    await L.say("Tayyor variantlardan tanlaysiz: uch soat, bir kun, uch kun yoki bir hafta. Bir kunga uzaytiramiz.",
                L.seg("quick", "24", "+1 kun", side="below"))
    await L.say("Yangi muddat pastda ko'rinadi. «Saqlash»ni bosamiz.",
                L.show('[data-f="new"]', "Yangi muddat", side="below", hold=0.6),
                L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.0)
    await L.say("Kerak bo'lsa «Tahrirlash» bilan matn va bajaruvchini o'zgartirasiz, «Bekor qilish» bilan topshiriqni bekor qilasiz.",
                L.show('.task-card [data-act="task-edit"]', "Tahrirlash", side="below", hold=0.6),
                L.show('.task-card [data-act="task-cancel"]', "Bekor qilish", side="below"))
    await L.say("Ish bajarilgach, «Bajarildi» tugmasini bosamiz.",
                L.click('.task-card [data-act="task-done"]', "Bajarildi", side="below"))
    await L.wait_for(f("comment", "textarea"))
    await L.say("Natija haqida qisqa izoh yozamiz — ixtiyoriy, lekin rahbar uchun foydali.",
                L.type(f("comment", "textarea"), "12 ta ota-onaga qo'ng'iroq qilindi", "Natija", delay=40))
    await L.say("«Bajarildi» tugmasini bosamiz. Eslatmalar to'xtaydi, topshiriq bergan odamga xabar boradi.",
                L.click(SAVE, "Bajarildi", side="above"))
    await L.wait(1.0)
    await L.say("Bajarilgan topshiriqlarni ko'rish uchun «Bajarildi» filtrini bosamiz.",
                L.click('#view .filters .seg a:has-text("Bajarildi")', "Bajarildi", side="below", wait=1.2))
    await L.say("Mana, topshiriq va natija izohi shu yerda saqlanadi.", L.show(".task-card", "Bajarilgan", side="below"))
    await L.say("Telegram'da ham topshiriq xabari ostida «Bajarildi» tugmasi bo'ladi — saytga kirmasdan belgilash mumkin.")
    await L.clear()
    await outro(L, "Lidlar bilan ishlash")
